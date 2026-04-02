#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# jarvis_update.sh — OpenJarvis Intelligent Update Script v2.0
# ═══════════════════════════════════════════════════════════════════════════════
# USAGE:
#   ./jarvis_update.sh              — scan and deploy all files in /var/home/kmonette/OpenJarvis/Updates/OpenJarvisUpdater
#   ./jarvis_update.sh --dry-run    — show what WOULD be copied without doing it
#   ./jarvis_update.sh --list       — list all known file mappings
#   ./jarvis_update.sh --help       — show this message
#
# HOW IT WORKS:
#   1. Scans every file in /var/home/kmonette/OpenJarvis/Updates/OpenJarvisUpdater/
#   2. Looks up each filename in the DESTINATION MAP below
#   3. Copies to ALL matching destinations (most important location first)
#   4. Handles .modelfile specially — runs: ollama rm + ollama create
#   5. Handles .sh files — sets chmod +x automatically
#   6. Creates a timestamped backup of each file it overwrites
#   7. Prints a full report of what was updated, skipped, or unknown
#
# ADD NEW FILES:
#   Edit the # ── DESTINATION MAP section below.
#   Format: ["filename"]="dest1|dest2|dest3"
#   Use TYPE: prefix to trigger special behavior:
#     MODELFILE:name   — runs ollama rm + ollama create -f
#     COMPONENT:       — also copies to all workspace component dirs
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# ─── Paths ────────────────────────────────────────────────────────────────────

UPDATER_DIR="/var/home/kmonette/OpenJarvis/Updates/OpenJarvisUpdater"
KEVIN_RECS_DIR="/var/home/kmonette/OpenJarvis/Updates/KevinsUpdateRecommendations"
SEND_QUEUE_DIR="/var/home/kmonette/OpenJarvis/workspaces/ws_1/SendToOpenJarvisUpdaterFiles"
JARVIS_ROOT="/var/home/kmonette/OpenJarvis"
WS_ROOT="$JARVIS_ROOT/workspaces"
BACKUP_DIR="$JARVIS_ROOT/update_backups/$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$JARVIS_ROOT/logs/update_log.txt"
DEPLOYED_DIR="$JARVIS_ROOT/Updates/deployed/$(date +%Y%m%d_%H%M%S)"

# ─── Flags ────────────────────────────────────────────────────────────────────

DRY_RUN=false
LIST_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --dry-run)  DRY_RUN=true  ;;
        --list)     LIST_ONLY=true ;;
        --help|-h)
            head -30 "$0" | grep "^#" | sed 's/^# \?//'
            exit 0
            ;;
    esac
done

# ─── Colors ───────────────────────────────────────────────────────────────────

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

log()     { echo -e "${GREEN}✅${NC} $*"; }
warn()    { echo -e "${YELLOW}⚠️ ${NC} $*"; }
err()     { echo -e "${RED}❌${NC} $*"; }
info()    { echo -e "${BLUE}ℹ️ ${NC} $*"; }
section() { echo -e "\n${BOLD}${CYAN}$*${NC}"; }

# ═══════════════════════════════════════════════════════════════════════════════
# ── DESTINATION MAP ───────────────────────────────────────────────────────────
# Format: ["filename"]="dest1|dest2|..."
# Special prefixes in destinations:
#   MODELFILE:<ollama_name>  — rebuild Ollama model with this name
#   EXEC:                    — chmod +x after copy
#   WS_COMPONENT:            — copy to all workspace components_master + promoted
# ═══════════════════════════════════════════════════════════════════════════════

declare -A DEST_MAP

# ── Bridge & pipeline files ───────────────────────────────────────────────────
DEST_MAP["slack_bridge.py"]="$JARVIS_ROOT/slack_bridge.py|$WS_ROOT/ws_2/slack_bridge.py"
DEST_MAP["assembler.py"]="$JARVIS_ROOT/assembler.py"
DEST_MAP["component_manager.py"]="$JARVIS_ROOT/component_manager.py"
DEST_MAP["tester.py"]="$JARVIS_ROOT/tester.py"
DEST_MAP["reviewer.py"]="$JARVIS_ROOT/reviewer.py"
DEST_MAP["qcai_trainer.py"]="$JARVIS_ROOT/qcai_trainer.py"
DEST_MAP["qcai_visualization.py"]="$JARVIS_ROOT/qcai_visualization.py"
DEST_MAP["reset_workspace.sh"]="EXEC:$JARVIS_ROOT/reset_workspace.sh|EXEC:$HOME/reset_workspace.sh"
DEST_MAP["install_host_commands.sh"]="EXEC:$JARVIS_ROOT/install_host_commands.sh"

# ── Shell scripts ─────────────────────────────────────────────────────────────
DEST_MAP["start_qcai.sh"]="EXEC:$JARVIS_ROOT/start_qcai.sh"
DEST_MAP["load_and_run.sh"]="EXEC:$JARVIS_ROOT/load_and_run.sh"
DEST_MAP["jarvis_update.sh"]="EXEC:$JARVIS_ROOT/jarvis_update.sh"
DEST_MAP["stop_qcai.sh"]="EXEC:$JARVIS_ROOT/stop_qcai.sh|EXEC:$HOME/stop_qcai.sh"
DEST_MAP["launch_qcai.sh"]="EXEC:$JARVIS_ROOT/launch_qcai.sh|EXEC:$HOME/launch_qcai.sh"

# ── Modelfiles — saved to ModelFiles/ folder, trigger ollama rebuild ──────────
MODELFILES_DIR="/var/home/kmonette/OpenJarvis/ModelFiles"
DEST_MAP["qwen3.5-9b-qcai.modelfile"]="$MODELFILES_DIR/qwen3.5-9b-qcai.modelfile|MODELFILE:qwen3.5:9b-qcai"
DEST_MAP["qwen3-8b-jarvis.modelfile"]="$MODELFILES_DIR/qwen3-8b-jarvis.modelfile|MODELFILE:qwen3-8b-jarvis"

# ── QCAI visualizer — main output files ──────────────────────────────────────
DEST_MAP["qcai_3d.py"]="$WS_ROOT/ws_1/qcai_3d.py|$WS_ROOT/ws_1/protected/qcai_3d_master.py"

# ── QCAI component files (c01–c13) ───────────────────────────────────────────
DEST_MAP["c01_header.py"]="WS_COMPONENT:c01_header"
DEST_MAP["c02_physics.py"]="WS_COMPONENT:c02_physics"
DEST_MAP["c03_nodes.py"]="WS_COMPONENT:c03_nodes"
DEST_MAP["c04_topology.py"]="WS_COMPONENT:c04_topology"
DEST_MAP["c05_curriculum.py"]="WS_COMPONENT:c05_curriculum"
DEST_MAP["c06_system.py"]="WS_COMPONENT:c06_system"
DEST_MAP["c07_dataserver.py"]="WS_COMPONENT:c07_dataserver"
DEST_MAP["c08_globe3d.py"]="WS_COMPONENT:c08_globe3d"
DEST_MAP["c09_metrics.py"]="WS_COMPONENT:c09_metrics"
DEST_MAP["c10_nodeoutput.py"]="WS_COMPONENT:c10_nodeoutput"
DEST_MAP["c11_controls.py"]="WS_COMPONENT:c11_controls"
DEST_MAP["c12_visualizer.py"]="WS_COMPONENT:c12_visualizer"
DEST_MAP["c13_main.py"]="WS_COMPONENT:c13_main"

# ── Project docs ──────────────────────────────────────────────────────────────
DEST_MAP["GROUND_TRUTH.md"]="$WS_ROOT/ws_1/GROUND_TRUTH.md"
DEST_MAP["INSTRUCTIONS.md"]="SKIP:managed_by_loop"   # never overwrite — loop owns this
DEST_MAP["README.md"]="$JARVIS_ROOT/README.md"
DEST_MAP["COMMAND_REFERENCE.html"]="$JARVIS_ROOT/docs/COMMAND_REFERENCE.html"
DEST_MAP["GITHUB_SETUP.md"]="$JARVIS_ROOT/docs/GITHUB_SETUP.md"
DEST_MAP["REVIEW.md"]="$JARVIS_ROOT/REVIEW.md"

# ═══════════════════════════════════════════════════════════════════════════════
# ── LIST MODE ─────────────────────────────────────────────────────────────────

if [ "$LIST_ONLY" = true ]; then
    section "Known File Mappings (${#DEST_MAP[@]} entries)"
    for fname in $(echo "${!DEST_MAP[@]}" | tr ' ' '\n' | sort); do
        echo -e "  ${BOLD}$fname${NC}"
        IFS='|' read -ra dests <<< "${DEST_MAP[$fname]}"
        for dest in "${dests[@]}"; do
            echo "    → $dest"
        done
    done
    exit 0
fi

# ═══════════════════════════════════════════════════════════════════════════════
# ── PREFLIGHT ─────────────────────────────────────────────────────────────────

section "OpenJarvis Updater — $(date '+%Y-%m-%d %H:%M:%S')"
[ "$DRY_RUN" = true ] && warn "DRY RUN MODE — no files will be changed"
echo ""

# Check updater folder exists
if [ ! -d "$UPDATER_DIR" ]; then
    err "Updater folder not found: $UPDATER_DIR"
    echo "   Create it with: mkdir -p $UPDATER_DIR"
    echo "   Then drop your update files in and re-run."
    exit 1
fi

# Count files in updater
shopt -s nullglob
update_files=("$UPDATER_DIR"/*) 
shopt -u nullglob

if [ ${#update_files[@]} -eq 0 ]; then
    warn "No files found in $UPDATER_DIR — nothing to do."
    exit 0
fi

info "Found ${#update_files[@]} file(s) in $UPDATER_DIR"
echo ""

# Create backup dir
if [ "$DRY_RUN" = false ]; then
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$(dirname "$LOG_FILE")"
    mkdir -p "$DEPLOYED_DIR"
    # Create dirs that may not exist yet
    mkdir -p "$JARVIS_ROOT/docs"
    mkdir -p "/var/home/kmonette/OpenJarvis/ModelFiles"
    mkdir -p "$WS_ROOT/ws_1/components_master"
    mkdir -p "$WS_ROOT/ws_1/components_promoted"
    mkdir -p "$WS_ROOT/ws_2"
fi

# ─── Counters ─────────────────────────────────────────────────────────────────
UPDATED=0
SKIPPED=0
UNKNOWN=0
ERRORS=0

# ─── Log function ─────────────────────────────────────────────────────────────
write_log() {
    if [ "$DRY_RUN" = false ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG_FILE"
    fi
}

# ─── Backup function ──────────────────────────────────────────────────────────
backup_file() {
    local target="$1"
    if [ -f "$target" ] && [ "$DRY_RUN" = false ]; then
        local bname
        bname="$(basename "$target").$(date +%s).bak"
        cp "$target" "$BACKUP_DIR/$bname" 2>/dev/null || true
    fi
}

# ─── Copy function ────────────────────────────────────────────────────────────
do_copy() {
    local src="$1"
    local dest="$2"
    local make_exec="${3:-false}"

    if [ "$DRY_RUN" = true ]; then
        echo "      [DRY-RUN] cp $src → $dest"
        return 0
    fi

    local dest_dir
    dest_dir="$(dirname "$dest")"

    if [ ! -d "$dest_dir" ]; then
        mkdir -p "$dest_dir"
    fi

    backup_file "$dest"
    cp "$src" "$dest"

    if [ "$make_exec" = true ]; then
        chmod +x "$dest"
    fi

    write_log "COPIED $(basename "$src") → $dest"
    return 0
}

# ─── WS_COMPONENT handler ─────────────────────────────────────────────────────
deploy_component() {
    local src="$1"
    local comp_name="$2"  # e.g. c02_physics
    local fname
    fname="$(basename "$src")"
    local deployed=0

    # Find all workspaces
    for ws_dir in "$WS_ROOT"/ws_*/; do
        [ -d "$ws_dir" ] || continue
        ws_id="$(basename "$ws_dir")"

        for tier in components_master components_promoted; do
            local dest_dir="$ws_dir$tier"
            local dest_file="$dest_dir/$fname"

            # Only deploy to master/promoted — never directly to sandbox
            if [ -d "$dest_dir" ] || [ "$DRY_RUN" = true ]; then
                if [ "$DRY_RUN" = true ]; then
                    echo "      [DRY-RUN] cp $src → $dest_file"
                else
                    mkdir -p "$dest_dir"
                    backup_file "$dest_file"
                    cp "$src" "$dest_file"
                    write_log "COMPONENT $fname → $ws_id/$tier"
                fi
                deployed=$((deployed + 1)) || true
            fi
        done
    done

    # Also update the main OpenJarvis components dir (legacy path, if exists)
    local legacy="$JARVIS_ROOT/workspaces/ws_1/components_master/$fname"
    if [ -f "$legacy" ] || [ -d "$(dirname "$legacy")" ]; then
        if [ "$DRY_RUN" = true ]; then
            echo "      [DRY-RUN] cp $src → $legacy"
        else
            backup_file "$legacy"
            cp "$src" "$legacy" 2>/dev/null || true
            write_log "COMPONENT $fname → legacy workspace"
        fi
        deployed=$((deployed + 1)) || true
    fi

    echo "      deployed to $deployed location(s) across workspaces"
}

# ─── Modelfile handler ────────────────────────────────────────────────────────
deploy_modelfile() {
    local src="$1"
    local modelfile_dest="$2"   # where to save the .modelfile
    local ollama_name="$3"      # e.g. qwen3.5:9b-qcai

    # Save the modelfile first
    if [ "$DRY_RUN" = false ]; then
        backup_file "$modelfile_dest"
        cp "$src" "$modelfile_dest"
        write_log "MODELFILE $(basename "$src") → $modelfile_dest"
    else
        echo "      [DRY-RUN] cp $src → $modelfile_dest"
    fi

    # Now handle Ollama rebuild
    # NOTE: Ollama runs on the HOST, not inside distrobox.
    # We detect this and print the exact commands to run on the HOST instead.
    echo ""
    if command -v ollama &>/dev/null; then
        echo "      🦙 Rebuilding Ollama model: $ollama_name"
        if [ "$DRY_RUN" = true ]; then
            echo "      [DRY-RUN] ollama rm $ollama_name"
            echo "      [DRY-RUN] ollama create $ollama_name -f $modelfile_dest"
        else
            echo "      Removing old: $ollama_name"
            ollama rm "$ollama_name" 2>/dev/null || true
            echo "      Creating: $ollama_name"
            if ollama create "$ollama_name" -f "$modelfile_dest"; then
                log "Ollama model rebuilt: $ollama_name"
                write_log "OLLAMA_REBUILT $ollama_name from $modelfile_dest"
            else
                err "ollama create failed for $ollama_name"
                write_log "OLLAMA_FAIL $ollama_name"
                return 1
            fi
        fi
    else
        # ollama not in PATH — running inside distrobox or container
        # Print the exact HOST commands to run manually
        echo "      ⚠️  ollama not in PATH (you are likely inside distrobox)"
        echo "      ✅ Modelfile saved to: $modelfile_dest"
        echo ""
        echo "      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "      Run these on the HOST (outside distrobox):"
        echo "      ollama rm $ollama_name"
        echo "      ollama create $ollama_name -f $modelfile_dest"
        echo "      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        write_log "OLLAMA_MANUAL_REQUIRED $ollama_name — run on HOST"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# ── MAIN LOOP — process each file in the updater folder ──────────────────────
# ═══════════════════════════════════════════════════════════════════════════════

section "Processing Files"

for src_file in "${update_files[@]}"; do
    [ -f "$src_file" ] || continue
    fname="$(basename "$src_file")"
    echo ""
    echo -e "${BOLD}📄 $fname${NC}"

    # ── Look up in DEST_MAP — with intelligent auto-detection fallback ─────────
    if [ -z "${DEST_MAP[$fname]+_}" ]; then

        # ── Auto-detection rules (no manual DEST_MAP entry needed) ────────────

        # Rule 1: QCAI component files c01-c13
        if [[ "$fname" =~ ^c[0-9][0-9]_.*\.py$ ]]; then
            comp_name="${fname%.py}"
            info "Auto-detected: QCAI component → all workspace component dirs"
            deploy_component "$src_file" "$comp_name"
            UPDATED=$((UPDATED + 1)) || true
            if [ "$DRY_RUN" = false ]; then mv "$src_file" "$DEPLOYED_DIR/$fname"; fi
            continue
        fi

        # Rule 2: Modelfiles
        if [[ "$fname" == *.modelfile ]]; then
            dest="$JARVIS_ROOT/ModelFiles/$fname"
            mkdir -p "$JARVIS_ROOT/ModelFiles"
            info "Auto-detected: modelfile → $dest (run ollama create manually on HOST)"
            do_copy "$src_file" "$dest"
            UPDATED=$((UPDATED + 1)) || true
            if [ "$DRY_RUN" = false ]; then mv "$src_file" "$DEPLOYED_DIR/$fname"; fi
            continue
        fi

        # Rule 3: Shell scripts (*.sh) → JARVIS_ROOT + home dir
        if [[ "$fname" == *.sh ]]; then
            info "Auto-detected: shell script → $JARVIS_ROOT + $HOME"
            do_copy "$src_file" "$JARVIS_ROOT/$fname" "true"
            do_copy "$src_file" "$HOME/$fname" "true"
            UPDATED=$((UPDATED + 1)) || true
            if [ "$DRY_RUN" = false ]; then mv "$src_file" "$DEPLOYED_DIR/$fname"; fi
            # Log suggestion to add to DEST_MAP for custom routing
            write_log "AUTO_DEPLOYED $fname as shell script — consider adding to DEST_MAP for custom routing"
            continue
        fi

        # Rule 4: Python files matching known pipeline names → JARVIS_ROOT
        if [[ "$fname" == *.py ]]; then
            info "Auto-detected: Python file → $JARVIS_ROOT/$fname"
            do_copy "$src_file" "$JARVIS_ROOT/$fname"
            UPDATED=$((UPDATED + 1)) || true
            if [ "$DRY_RUN" = false ]; then mv "$src_file" "$DEPLOYED_DIR/$fname"; fi
            write_log "AUTO_DEPLOYED $fname as Python file — consider adding to DEST_MAP for multi-location routing"
            continue
        fi

        # Rule 5: Markdown/HTML docs → docs/
        if [[ "$fname" == *.md ]] || [[ "$fname" == *.html ]]; then
            mkdir -p "$JARVIS_ROOT/docs"
            info "Auto-detected: doc file → $JARVIS_ROOT/docs/$fname"
            do_copy "$src_file" "$JARVIS_ROOT/docs/$fname"
            UPDATED=$((UPDATED + 1)) || true
            if [ "$DRY_RUN" = false ]; then mv "$src_file" "$DEPLOYED_DIR/$fname"; fi
            continue
        fi

        # Rule 6: JSON/YAML config files → JARVIS_ROOT
        if [[ "$fname" == *.json ]] || [[ "$fname" == *.yaml ]] || [[ "$fname" == *.yml ]]; then
            info "Auto-detected: config file → $JARVIS_ROOT/$fname"
            do_copy "$src_file" "$JARVIS_ROOT/$fname"
            UPDATED=$((UPDATED + 1)) || true
            if [ "$DRY_RUN" = false ]; then mv "$src_file" "$DEPLOYED_DIR/$fname"; fi
            continue
        fi

        # No rule matched — log it and skip (never silently discard)
        warn "UNRECOGNIZED: $fname — no DEST_MAP entry and no auto-detection rule matched"
        warn "  Extension: ${fname##*.}"
        warn "  To deploy: add to DEST_MAP in $0"
        warn "  Or rename with a known extension (.py .sh .md .html .modelfile)"
        write_log "SKIPPED $fname — unrecognized type"
        UNKNOWN=$((UNKNOWN + 1)) || true
        continue
    fi

    dest_string="${DEST_MAP[$fname]}"

    # SKIP prefix — never overwrite
    if [[ "$dest_string" == SKIP:* ]]; then
        reason="${dest_string#SKIP:}"
        info "SKIPPED $fname — reason: $reason"
        SKIPPED=$((SKIPPED + 1)) || true
        continue
    fi

    # Split destinations by pipe
    IFS='|' read -ra destinations <<< "$dest_string"

    file_ok=true
    for dest_entry in "${destinations[@]}"; do

        # ── MODELFILE special handling ────────────────────────────────────────
        if [[ "$dest_entry" == MODELFILE:* ]]; then
            ollama_name="${dest_entry#MODELFILE:}"
            # Find the file dest (non-MODELFILE entry) for where to save the file
            modelfile_dest="$HOME/$fname"
            for d in "${destinations[@]}"; do
                if [[ "$d" != MODELFILE:* ]]; then
                    modelfile_dest="$d"
                    break
                fi
            done
            echo "      🦙 Modelfile → Ollama model: $ollama_name"
            deploy_modelfile "$src_file" "$modelfile_dest" "$ollama_name" || file_ok=false
            continue
        fi

        # ── WS_COMPONENT handling ─────────────────────────────────────────────
        if [[ "$dest_entry" == WS_COMPONENT:* ]]; then
            comp_name="${dest_entry#WS_COMPONENT:}"
            deploy_component "$src_file" "$comp_name"
            continue
        fi

        # ── EXEC prefix — copy + chmod +x ────────────────────────────────────
        make_exec=false
        actual_dest="$dest_entry"
        if [[ "$dest_entry" == EXEC:* ]]; then
            make_exec=true
            actual_dest="${dest_entry#EXEC:}"
        fi

        # ── Regular copy ─────────────────────────────────────────────────────
        if [ -f "$actual_dest" ]; then
            echo "      Overwriting: $actual_dest"
        else
            echo "      Creating:    $actual_dest"
        fi

        if do_copy "$src_file" "$actual_dest" "$make_exec"; then
            [ "$make_exec" = true ] && echo "      +x applied"
        else
            err "Failed to copy to $actual_dest"
            file_ok=false
        fi
    done

    if [ "$file_ok" = true ]; then
        log "$fname — deployed"
        UPDATED=$((UPDATED + 1)) || true
        # Move deployed file out of updater folder — keeps it clean
        if [ "$DRY_RUN" = false ]; then
            mv "$src_file" "$DEPLOYED_DIR/$fname"
            write_log "MOVED $fname → deployed/$fname"
        fi
    else
        err "$fname — one or more deployments failed"
        err "  File left in updater for retry: $fname"
        ERRORS=$((ERRORS + 1)) || true
        # Do NOT move failed files — leave them for retry
    fi
done

# ═══════════════════════════════════════════════════════════════════════════════
# ── SUMMARY ───────────────────────────────────════════════════════════════════

section "Update Summary"
echo ""
echo -e "  ${GREEN}Updated:${NC}  $UPDATED file(s)"
echo -e "  ${YELLOW}Skipped:${NC}  $SKIPPED file(s)"
echo -e "  ${BLUE}Unknown:${NC}  $UNKNOWN file(s)  (add to DEST_MAP to auto-deploy)"
[ "$ERRORS" -gt 0 ] && echo -e "  ${RED}Errors:${NC}   $ERRORS file(s)"
echo ""

if [ "$DRY_RUN" = false ]; then
    if [ "$UPDATED" -gt 0 ]; then
        echo -e "  Backups saved to: ${CYAN}$BACKUP_DIR${NC}"
        echo -e "  Log appended to:  ${CYAN}$LOG_FILE${NC}"
    fi
    echo ""
    echo -e "  Deployed files moved to: ${CYAN}$DEPLOYED_DIR${NC}"
    echo ""
    echo -e "  ${BOLD}Done.${NC} If slack_bridge.py was updated, restart the bridge:"
    echo -e "  ${CYAN}cd /var/home/kmonette/OpenJarvis && ./start_qcai.sh${NC}"
fi

[ "$ERRORS" -gt 0 ] && exit 1 || exit 0