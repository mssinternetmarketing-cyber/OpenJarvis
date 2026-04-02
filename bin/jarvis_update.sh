#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# jarvis_update.sh — OpenJarvis Intelligent Update Script v2.2
# ═══════════════════════════════════════════════════════════════════════════════
# USAGE:
#   ./jarvis_update.sh              — scan and deploy all files in OpenJarvisUpdater/
#   ./jarvis_update.sh --dry-run    — show what WOULD be copied without doing it
#   ./jarvis_update.sh --list       — list all known file mappings
#   ./jarvis_update.sh --help       — show this message
#
# HOW IT WORKS:
#   1. Reads active workspace from workspaces/active_workspace.txt (defaults ws_1)
#   2. Scans every file in OpenJarvisUpdater/
#   3. Looks up each filename in the DESTINATION MAP
#   4. Always copies to: JARVIS_ROOT (primary) + active workspace (mirror/backup)
#   5. DEST_MAP entries override the default routing for named files
#   6. Auto-detection rules handle anything not in DEST_MAP
#   7. Handles .modelfile — runs ollama rm + ollama create
#   8. Handles .sh files — sets chmod +x automatically
#   9. Creates a timestamped backup of each file it overwrites
#  10. Prints a full report of what was updated, skipped, or unknown
#
# MANUAL DROPS — just drop any file in OpenJarvisUpdater/ and run qcai-update:
#   *.py       → JARVIS_ROOT/ + active workspace/
#   *.sh       → JARVIS_ROOT/ + ~/ + active workspace/
#   *.md       → JARVIS_ROOT/docs/ + active workspace/
#   *.json     → JARVIS_ROOT/ + active workspace/
#   c01-c13    → all workspace component dirs
#   cmd_*.sh   → install as host command
#   *.modelfile → ModelFiles/ + ollama rebuild
#
# ADD NAMED FILE ROUTING:
#   Edit the DESTINATION MAP below.
#   Format: ["filename"]="dest1|dest2|dest3"
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# ─── Paths ────────────────────────────────────────────────────────────────────

JARVIS_ROOT="/var/home/kmonette/OpenJarvis"
WS_ROOT="$JARVIS_ROOT/workspaces"
UPDATER_DIR="$JARVIS_ROOT/Updates/OpenJarvisUpdater"
KEVIN_RECS_DIR="$JARVIS_ROOT/Updates/KevinsUpdateRecommendations"
BACKUP_DIR="$JARVIS_ROOT/update_backups/$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$JARVIS_ROOT/logs/update_log.txt"
DEPLOYED_DIR="$JARVIS_ROOT/Updates/deployed/$(date +%Y%m%d_%H%M%S)"
COMMANDS_DIR="$JARVIS_ROOT/commands"
BIN_DIR="$HOME/bin"
DISTROBOX_NAME="openjarvis-box"

# ─── Active workspace resolution ──────────────────────────────────────────────
# Always reads active_workspace.txt. Falls back to ws_1.
# Every deployment mirrors to JARVIS_ROOT (primary) AND active workspace (backup).
ACTIVE_WS_FILE="$WS_ROOT/active_workspace.txt"
ACTIVE_WS=""
if [ -f "$ACTIVE_WS_FILE" ]; then
    ACTIVE_WS=$(cat "$ACTIVE_WS_FILE" 2>/dev/null || echo "")
fi
if [ -z "$ACTIVE_WS" ] || [ ! -d "$ACTIVE_WS" ]; then
    ACTIVE_WS="$WS_ROOT/ws_1"
fi
ACTIVE_WS_NAME=$(basename "$ACTIVE_WS")
DISTROBOX_NAME="openjarvis-box"

# ─── Flags ────────────────────────────────────────────────────────────────────

DRY_RUN=false
LIST_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --dry-run)  DRY_RUN=true  ;;
        --list)     LIST_ONLY=true ;;
        --help|-h)
            head -35 "$0" | grep "^#" | sed 's/^# \?//'
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
# Special prefixes:
#   MODELFILE:<ollama_name>  — rebuild Ollama model with this name
#   EXEC:                    — chmod +x after copy
#   WS_COMPONENT:            — copy to all workspace components_master + promoted
#   COMMAND:<cmd_name>       — install as ~/bin/<cmd_name> host command
# ═══════════════════════════════════════════════════════════════════════════════

declare -A DEST_MAP

# ── Bridge & pipeline files ───────────────────────────────────────────────────
# Pattern: JARVIS_ROOT (primary) | ACTIVE_WS (backup mirror) | other locations
DEST_MAP["slack_bridge.py"]="$JARVIS_ROOT/slack_bridge.py|$ACTIVE_WS/slack_bridge.py|$WS_ROOT/ws_2/slack_bridge.py"
DEST_MAP["assembler.py"]="$JARVIS_ROOT/assembler.py|$ACTIVE_WS/assembler.py"
DEST_MAP["component_manager.py"]="$JARVIS_ROOT/component_manager.py|$ACTIVE_WS/component_manager.py"
DEST_MAP["tester.py"]="$JARVIS_ROOT/tester.py|$ACTIVE_WS/tester.py"
DEST_MAP["reviewer.py"]="$JARVIS_ROOT/reviewer.py|$ACTIVE_WS/reviewer.py"
DEST_MAP["qcai_trainer.py"]="$JARVIS_ROOT/qcai_trainer.py|$ACTIVE_WS/qcai_trainer.py"
DEST_MAP["qcai_visualization.py"]="$JARVIS_ROOT/qcai_visualization.py|$ACTIVE_WS/qcai_visualization.py"
DEST_MAP["reset_workspace.sh"]="EXEC:$JARVIS_ROOT/reset_workspace.sh|EXEC:$HOME/reset_workspace.sh"
DEST_MAP["install_host_commands.sh"]="EXEC:$JARVIS_ROOT/install_host_commands.sh"

# ── Shell scripts ─────────────────────────────────────────────────────────────
DEST_MAP["start_qcai.sh"]="EXEC:$JARVIS_ROOT/start_qcai.sh"
DEST_MAP["load_and_run.sh"]="EXEC:$JARVIS_ROOT/load_and_run.sh"
DEST_MAP["stop_qcai.sh"]="EXEC:$JARVIS_ROOT/stop_qcai.sh|EXEC:$HOME/stop_qcai.sh"
DEST_MAP["launch_qcai.sh"]="EXEC:$JARVIS_ROOT/launch_qcai.sh|EXEC:$HOME/launch_qcai.sh"
# jarvis_update.sh is NOT in DEST_MAP — deploy via: qcai-update-updater

# ── Visualization scripts ─────────────────────────────────────────────────────
DEST_MAP["viz_loop.sh"]="EXEC:$JARVIS_ROOT/viz_loop.sh|EXEC:$HOME/viz_loop.sh"
DEST_MAP["viz_pause.sh"]="EXEC:$JARVIS_ROOT/viz_pause.sh|EXEC:$HOME/viz_pause.sh"
DEST_MAP["viz_resume.sh"]="EXEC:$JARVIS_ROOT/viz_resume.sh|EXEC:$HOME/viz_resume.sh"
DEST_MAP["update_viz.sh"]="EXEC:$JARVIS_ROOT/update_viz.sh|EXEC:$HOME/update_viz.sh"
DEST_MAP["qcai-install-commands.sh"]="EXEC:$JARVIS_ROOT/qcai-install-commands.sh|EXEC:$HOME/qcai-install-commands.sh"

# ── Modelfiles ────────────────────────────────────────────────────────────────
MODELFILES_DIR="$JARVIS_ROOT/ModelFiles"
DEST_MAP["qwen3.5-9b-qcai.modelfile"]="$MODELFILES_DIR/qwen3.5-9b-qcai.modelfile|MODELFILE:qwen3.5:9b-qcai"
DEST_MAP["qwen3-8b-jarvis.modelfile"]="$MODELFILES_DIR/qwen3-8b-jarvis.modelfile|MODELFILE:qwen3-8b-jarvis"

# ── QCAI visualizer — active workspace is always the target ──────────────────
DEST_MAP["qcai_3d.py"]="$ACTIVE_WS/qcai_3d.py|$ACTIVE_WS/protected/qcai_3d_master.py"

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

# ── Project docs — active workspace is source of truth, JARVIS_ROOT is backup ─
DEST_MAP["GROUND_TRUTH.md"]="$ACTIVE_WS/GROUND_TRUTH.md|$JARVIS_ROOT/GROUND_TRUTH.md"
DEST_MAP["current_task.md"]="$ACTIVE_WS/current_task.md|$JARVIS_ROOT/current_task.md"
DEST_MAP["INSTRUCTIONS.md"]="SKIP:managed_by_loop"
DEST_MAP["README.md"]="$JARVIS_ROOT/README.md|$ACTIVE_WS/README.md"
DEST_MAP["COMMAND_REFERENCE.html"]="$JARVIS_ROOT/docs/COMMAND_REFERENCE.html"
DEST_MAP["GITHUB_SETUP.md"]="$JARVIS_ROOT/docs/GITHUB_SETUP.md"
DEST_MAP["REVIEW.md"]="$JARVIS_ROOT/REVIEW.md|$ACTIVE_WS/REVIEW.md"

# ═══════════════════════════════════════════════════════════════════════════════
# ── LIST MODE ─────────────────────────────────────────────────────────────────

if [ "$LIST_ONLY" = true ]; then
    section "Known File Mappings (${#DEST_MAP[@]} entries)"
    for fname in $(echo "${!DEST_MAP[@]}" | tr ' ' '\n' | sort); do
        echo -e "  ${BOLD}$fname${NC}"
        IFS='|' read -ra dests <<< "${DEST_MAP[$fname]}"
        for dest in "${dests[@]}"; do
            echo "    -> $dest"
        done
    done
    exit 0
fi

# ═══════════════════════════════════════════════════════════════════════════════
# ── PREFLIGHT ─────────────────────────────────────────────────────────────────

section "OpenJarvis Updater v2.2 — $(date '+%Y-%m-%d %H:%M:%S')"
[ "$DRY_RUN" = true ] && warn "DRY RUN MODE — no files will be changed"
echo ""
info "Active workspace: $ACTIVE_WS_NAME  ($ACTIVE_WS)"
info "Primary deploy:   $JARVIS_ROOT"
info "Mirror/backup:    $ACTIVE_WS"
echo ""

if [ ! -d "$UPDATER_DIR" ]; then
    err "Updater folder not found: $UPDATER_DIR"
    echo "   Create it with: mkdir -p $UPDATER_DIR"
    exit 1
fi

shopt -s nullglob
update_files=("$UPDATER_DIR"/*)
shopt -u nullglob

if [ ${#update_files[@]} -eq 0 ]; then
    warn "No files found in $UPDATER_DIR — nothing to do."
    exit 0
fi

info "Found ${#update_files[@]} file(s) in $UPDATER_DIR"
echo ""

if [ "$DRY_RUN" = false ]; then
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$(dirname "$LOG_FILE")"
    mkdir -p "$DEPLOYED_DIR"
    mkdir -p "$JARVIS_ROOT/docs"
    mkdir -p "$JARVIS_ROOT/ModelFiles"
    mkdir -p "$ACTIVE_WS"
    mkdir -p "$WS_ROOT/ws_1/components_master"
    mkdir -p "$WS_ROOT/ws_1/components_promoted"
    mkdir -p "$WS_ROOT/ws_2"
    mkdir -p "$COMMANDS_DIR/scripts"
    mkdir -p "$COMMANDS_DIR/registry"
    mkdir -p "$BIN_DIR"
fi

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
        echo "      [DRY-RUN] cp $src -> $dest"
        return 0
    fi

    local dest_dir
    dest_dir="$(dirname "$dest")"
    [ ! -d "$dest_dir" ] && mkdir -p "$dest_dir"

    backup_file "$dest"
    cp "$src" "$dest"
    [ "$make_exec" = true ] && chmod +x "$dest"

    local _fname2; _fname2=$(basename "$src")
    write_log "COPIED $_fname2 -> $dest"
    return 0
}

# ─── WS_COMPONENT handler ─────────────────────────────────────────────────────
deploy_component() {
    local src="$1"
    local comp_name="$2"
    local fname
    fname="$(basename "$src")"
    local deployed=0

    for ws_dir in "$WS_ROOT"/ws_*/; do
        [ -d "$ws_dir" ] || continue
        ws_id="$(basename "$ws_dir")"
        for tier in components_master components_promoted; do
            local dest_dir="$ws_dir$tier"
            local dest_file="$dest_dir/$fname"
            if [ -d "$dest_dir" ] || [ "$DRY_RUN" = true ]; then
                if [ "$DRY_RUN" = true ]; then
                    echo "      [DRY-RUN] cp $src -> $dest_file"
                else
                    mkdir -p "$dest_dir"
                    backup_file "$dest_file"
                    cp "$src" "$dest_file"
                    write_log "COMPONENT $fname -> $ws_id/$tier"
                fi
                deployed=$((deployed + 1)) || true
            fi
        done
    done

    local legacy="$JARVIS_ROOT/workspaces/ws_1/components_master/$fname"
    if [ -f "$legacy" ] || [ -d "$(dirname "$legacy")" ]; then
        if [ "$DRY_RUN" = true ]; then
            echo "      [DRY-RUN] cp $src -> $legacy"
        else
            backup_file "$legacy"
            cp "$src" "$legacy" 2>/dev/null || true
            write_log "COMPONENT $fname -> legacy workspace"
        fi
        deployed=$((deployed + 1)) || true
    fi

    echo "      deployed to $deployed location(s) across workspaces"
}

# ─── COMMAND handler — deploy script and install ~/bin wrapper ────────────────
deploy_command() {
    local src="$1"
    local cmd_name="$2"  # the ~/bin command name
    local fname
    fname="$(basename "$src")"
    local ext="${fname##*.}"

    # Determine script destination
    local script_dest="$COMMANDS_DIR/scripts/$fname"

    echo "      🔧 Commands Agent tool: $cmd_name"
    if [ "$DRY_RUN" = true ]; then
        echo "      [DRY-RUN] cp $src -> $script_dest"
        echo "      [DRY-RUN] create ~/bin/$cmd_name wrapper"
        return 0
    fi

    # Copy script to commands/scripts/
    backup_file "$script_dest"
    cp "$src" "$script_dest"
    chmod +x "$script_dest"
    write_log "COMMAND_SCRIPT $fname -> $script_dest"

    # Create ~/bin wrapper that runs inside distrobox
    local wrapper="$BIN_DIR/$cmd_name"
    mkdir -p "$BIN_DIR"
    if [ "$ext" = "sh" ]; then
        cat > "$wrapper" << WEOF
#!/usr/bin/env bash
# Auto-generated by jarvis_update.sh — Commands Agent tool
# Created: $(date '+%Y-%m-%d %H:%M:%S')
distrobox enter $DISTROBOX_NAME -- bash "$script_dest" "\$@"
WEOF
    else
        # Python or other
        cat > "$wrapper" << WEOF
#!/usr/bin/env bash
# Auto-generated by jarvis_update.sh — Commands Agent tool
# Created: $(date '+%Y-%m-%d %H:%M:%S')
distrobox enter $DISTROBOX_NAME -- python3 "$script_dest" "\$@"
WEOF
    fi
    chmod +x "$wrapper"
    write_log "COMMAND_WRAPPER $cmd_name -> $wrapper"

    # Append to command registry JSON
    local registry="$COMMANDS_DIR/registry/commands.json"
    local ts
    ts=$(date '+%Y-%m-%d %H:%M:%S')
    if [ ! -f "$registry" ]; then
        echo '{"commands":[]}' > "$registry"
    fi

    # Use python3 to safely update JSON (avoids sed fragility)
    python3 - << PYEOF 2>/dev/null || true
import json, sys
with open('$registry') as f:
    data = json.load(f)
# Remove existing entry for this cmd_name if any
data['commands'] = [c for c in data['commands'] if c.get('name') != '$cmd_name']
data['commands'].append({
    'name': '$cmd_name',
    'script': '$script_dest',
    'wrapper': '$wrapper',
    'created': '$ts',
    'source': 'commands_agent'
})
with open('$registry', 'w') as f:
    json.dump(data, f, indent=2)
print(f"Registry updated: {len(data['commands'])} commands")
PYEOF

    log "Command installed: $cmd_name"
    echo ""
    echo "  ┌─────────────────────────────────────────────────┐"
    echo "  │  🔧 NEW TOOL CREATED BY AGENTS                  │"
    echo "  │                                                   │"
    echo "  │  Command: $cmd_name"
    echo "  │  Script:  $script_dest"
    echo "  │  Usage:   $cmd_name [args]"
    echo "  └─────────────────────────────────────────────────┘"
    write_log "COMMAND_INSTALLED $cmd_name from $fname"
}

# ─── Modelfile handler ────────────────────────────────────────────────────────
deploy_modelfile() {
    local src="$1"
    local modelfile_dest="$2"
    local ollama_name="$3"

    if [ "$DRY_RUN" = false ]; then
        backup_file "$modelfile_dest"
        cp "$src" "$modelfile_dest"
        write_log "MODELFILE $(basename "$src") -> $modelfile_dest"
    else
        echo "      [DRY-RUN] cp $src -> $modelfile_dest"
    fi

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
        echo "      ⚠️  ollama not in PATH (likely inside distrobox)"
        echo "      ✅ Modelfile saved to: $modelfile_dest"
        echo ""
        echo "      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "      Run these on the HOST (outside distrobox):"
        echo "      ollama rm $ollama_name"
        echo "      ollama create $ollama_name -f $modelfile_dest"
        echo "      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        write_log "OLLAMA_MANUAL_REQUIRED $ollama_name -- run on HOST"
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# ── MAIN LOOP ─────────────────────────────────────────────────────────────────

section "Processing Files"

for src_file in "${update_files[@]}"; do
    [ -f "$src_file" ] || continue
    fname="$(basename "$src_file")"
    echo ""
    echo -e "${BOLD}📄 $fname${NC}"

    # ── Look up in DEST_MAP first ──────────────────────────────────────────────
    if [ -z "${DEST_MAP[$fname]+_}" ]; then

        # ── Auto-detection rules ──────────────────────────────────────────────

        # Rule 0: Commands Agent scripts — prefix "cmd_" triggers COMMAND install
        if [[ "$fname" == cmd_*.sh ]] || [[ "$fname" == cmd_*.py ]]; then
            cmd_name="${fname#cmd_}"          # strip cmd_ prefix
            cmd_name="${cmd_name%.*}"         # strip extension
            cmd_name="${cmd_name//_/-}"       # underscores → hyphens for readability
            info "Auto-detected: Commands Agent tool -> $cmd_name"
            deploy_command "$src_file" "$cmd_name"
            UPDATED=$((UPDATED + 1)) || true
            if [ "$DRY_RUN" = false ]; then mv "$src_file" "$DEPLOYED_DIR/$fname"; fi
            continue
        fi

        # Rule 1: QCAI component files c01-c13
        if [[ "$fname" =~ ^c[0-9][0-9]_.*\.py$ ]]; then
            comp_name="${fname%.py}"
            info "Auto-detected: QCAI component -> all workspace component dirs"
            deploy_component "$src_file" "$comp_name"
            UPDATED=$((UPDATED + 1)) || true
            if [ "$DRY_RUN" = false ]; then mv "$src_file" "$DEPLOYED_DIR/$fname"; fi
            continue
        fi

        # Rule 2: Modelfiles
        if [[ "$fname" == *.modelfile ]]; then
            dest="$JARVIS_ROOT/ModelFiles/$fname"
            mkdir -p "$JARVIS_ROOT/ModelFiles"
            info "Auto-detected: modelfile -> $dest (run ollama create manually on HOST)"
            do_copy "$src_file" "$dest"
            UPDATED=$((UPDATED + 1)) || true
            if [ "$DRY_RUN" = false ]; then mv "$src_file" "$DEPLOYED_DIR/$fname"; fi
            continue
        fi

        # Rule 3: Shell scripts (*.sh) -> JARVIS_ROOT + home dir + active workspace
        if [[ "$fname" == *.sh ]]; then
            info "Auto-detected: shell script -> $JARVIS_ROOT + $HOME + $ACTIVE_WS_NAME"
            do_copy "$src_file" "$JARVIS_ROOT/$fname" "true"
            do_copy "$src_file" "$HOME/$fname" "true"
            do_copy "$src_file" "$ACTIVE_WS/$fname" "true"
            UPDATED=$((UPDATED + 1)) || true
            if [ "$DRY_RUN" = false ]; then mv "$src_file" "$DEPLOYED_DIR/$fname"; fi
            write_log "AUTO_DEPLOYED $fname as shell script"
            continue
        fi

        # Rule 4: Python files -> JARVIS_ROOT + active workspace mirror
        if [[ "$fname" == *.py ]]; then
            info "Auto-detected: Python file -> $JARVIS_ROOT + $ACTIVE_WS_NAME"
            do_copy "$src_file" "$JARVIS_ROOT/$fname"
            do_copy "$src_file" "$ACTIVE_WS/$fname"
            UPDATED=$((UPDATED + 1)) || true
            if [ "$DRY_RUN" = false ]; then mv "$src_file" "$DEPLOYED_DIR/$fname"; fi
            write_log "AUTO_DEPLOYED $fname as Python file"
            continue
        fi

        # Rule 5: Markdown/HTML docs -> active workspace (primary) + docs/
        if [[ "$fname" == *.md ]] || [[ "$fname" == *.html ]]; then
            mkdir -p "$JARVIS_ROOT/docs"
            info "Auto-detected: doc file -> $ACTIVE_WS_NAME + $JARVIS_ROOT/docs/"
            do_copy "$src_file" "$ACTIVE_WS/$fname"
            do_copy "$src_file" "$JARVIS_ROOT/docs/$fname"
            UPDATED=$((UPDATED + 1)) || true
            if [ "$DRY_RUN" = false ]; then mv "$src_file" "$DEPLOYED_DIR/$fname"; fi
            continue
        fi

        # Rule 6: JSON/YAML config files -> JARVIS_ROOT + active workspace
        if [[ "$fname" == *.json ]] || [[ "$fname" == *.yaml ]] || [[ "$fname" == *.yml ]]; then
            info "Auto-detected: config file -> $JARVIS_ROOT + $ACTIVE_WS_NAME"
            do_copy "$src_file" "$JARVIS_ROOT/$fname"
            do_copy "$src_file" "$ACTIVE_WS/$fname"
            UPDATED=$((UPDATED + 1)) || true
            if [ "$DRY_RUN" = false ]; then mv "$src_file" "$DEPLOYED_DIR/$fname"; fi
            continue
        fi

        # No rule matched
        warn "UNRECOGNIZED: $fname — no DEST_MAP entry and no auto-detection rule matched"
        warn "  To make a tool: rename with cmd_ prefix (e.g. cmd_qcai-health.sh)"
        warn "  Or add to DEST_MAP for custom routing"
        write_log "SKIPPED $fname -- unrecognized type"
        UNKNOWN=$((UNKNOWN + 1)) || true
        continue
    fi

    dest_string="${DEST_MAP[$fname]}"

    # SKIP prefix
    if [[ "$dest_string" == SKIP:* ]]; then
        reason="${dest_string#SKIP:}"
        info "SKIPPED $fname — reason: $reason"
        SKIPPED=$((SKIPPED + 1)) || true
        continue
    fi

    IFS='|' read -ra destinations <<< "$dest_string"

    file_ok=true
    for dest_entry in "${destinations[@]}"; do

        # ── MODELFILE special handling ────────────────────────────────────────
        if [[ "$dest_entry" == MODELFILE:* ]]; then
            ollama_name="${dest_entry#MODELFILE:}"
            modelfile_dest="$HOME/$fname"
            for d in "${destinations[@]}"; do
                if [[ "$d" != MODELFILE:* ]]; then
                    modelfile_dest="$d"
                    break
                fi
            done
            echo "      🦙 Modelfile -> Ollama model: $ollama_name"
            deploy_modelfile "$src_file" "$modelfile_dest" "$ollama_name" || file_ok=false
            continue
        fi

        # ── WS_COMPONENT handling ─────────────────────────────────────────────
        if [[ "$dest_entry" == WS_COMPONENT:* ]]; then
            comp_name="${dest_entry#WS_COMPONENT:}"
            deploy_component "$src_file" "$comp_name"
            continue
        fi

        # ── COMMAND handling ──────────────────────────────────────────────────
        if [[ "$dest_entry" == COMMAND:* ]]; then
            cmd_name="${dest_entry#COMMAND:}"
            deploy_command "$src_file" "$cmd_name"
            continue
        fi

        # ── EXEC prefix ───────────────────────────────────────────────────────
        make_exec=false
        actual_dest="$dest_entry"
        if [[ "$dest_entry" == EXEC:* ]]; then
            make_exec=true
            actual_dest="${dest_entry#EXEC:}"
        fi

        # ── Regular copy ──────────────────────────────────────────────────────
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
        if [ "$DRY_RUN" = false ]; then
            mv "$src_file" "$DEPLOYED_DIR/$fname"
            write_log "MOVED $fname -> deployed/$fname"
        fi
    else
        err "$fname — one or more deployments failed"
        err "  File left in updater for retry: $fname"
        ERRORS=$((ERRORS + 1)) || true
    fi
done

# ═══════════════════════════════════════════════════════════════════════════════
# ── SUMMARY ───────────────────────────────────════════════════════════════════

section "Update Summary"
echo ""
echo -e "  ${GREEN}Updated:${NC}  $UPDATED file(s)"
echo -e "  ${YELLOW}Skipped:${NC}  $SKIPPED file(s)"
echo -e "  ${BLUE}Unknown:${NC}  $UNKNOWN file(s)  (see above for UNRECOGNIZED warnings)"
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
    echo -e "  ${BOLD}Routing summary:${NC}"
    echo -e "    Primary:   ${CYAN}$JARVIS_ROOT${NC}"
    echo -e "    Workspace: ${CYAN}$ACTIVE_WS${NC} (mirror/backup)"
    echo ""
    echo -e "  ${BOLD}Done.${NC} If slack_bridge.py was updated, restart the bridge:"
    echo -e "  ${CYAN}qcai-restart${NC}"
    echo ""
    echo -e "  To deploy more files, drop them in:"
    echo -e "  ${CYAN}$UPDATER_DIR${NC}"
    echo -e "  then run: ${CYAN}qcai-update${NC}"
fi

[ "$ERRORS" -gt 0 ] && exit 1 || exit 0
