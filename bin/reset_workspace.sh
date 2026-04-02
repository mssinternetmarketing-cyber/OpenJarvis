#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# reset_workspace.sh v9.1 — QCAI Multi-Workspace Reset
# 
# WHAT: Resets the ACTIVE workspace cleanly.
#       All removed files are backed up — nothing is permanently deleted.
#       Restores clean base to protected/ master and qcai_3d.py.
#       Keeps: current_task.md, GROUND_TRUTH.md, INSTRUCTIONS.md
#
# BACKUPS: /var/home/kmonette/OpenJarvis/WorkspaceResetBackups/<workspace>/<timestamp>/
#
# Usage: ~/reset_workspace.sh
#        ~/reset_workspace.sh ws_2         (reset a specific workspace by name)
#        ~/reset_workspace.sh --list       (show all workspaces)
#        ~/reset_workspace.sh --dry-run    (preview what would be reset)
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

JARVIS_ROOT="/var/home/kmonette/OpenJarvis"
WORKSPACES_ROOT="$JARVIS_ROOT/workspaces"
BACKUPS_ROOT="$JARVIS_ROOT/WorkspaceResetBackups"
ACTIVE_WS_FILE="$WORKSPACES_ROOT/active_workspace.txt"

# ── Flags ─────────────────────────────────────────────────────────────────────
DRY_RUN=false
LIST_ONLY=false
TARGET_WS=""

for arg in "$@"; do
    case "$arg" in
        --dry-run)  DRY_RUN=true  ;;
        --list)     LIST_ONLY=true ;;
        --help|-h)
            echo "Usage: ~/reset_workspace.sh [workspace_name] [--dry-run] [--list]"
            echo "  No args        — reset active workspace"
            echo "  ws_2           — reset specific workspace"
            echo "  --dry-run      — preview only, no changes"
            echo "  --list         — show all workspaces"
            exit 0 ;;
        --*) ;;
        *)   TARGET_WS="$arg" ;;
    esac
done

# ── Colors ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'
BOLD='\033[1m'; NC='\033[0m'; RED='\033[0;31m'

log()     { echo -e "${GREEN}  ✅${NC} $*"; }
warn()    { echo -e "${YELLOW}  ⚠️ ${NC} $*"; }
err()     { echo -e "${RED}  ❌${NC} $*"; }
section() { echo -e "\n${BOLD}${CYAN}▶ $*${NC}"; }

# ── List mode ─────────────────────────────────────────────────────────────────
if [ "$LIST_ONLY" = true ]; then
    echo -e "${BOLD}Available Workspaces:${NC}"
    active=$(cat "$ACTIVE_WS_FILE" 2>/dev/null || echo "")
    for ws in "$WORKSPACES_ROOT"/ws_*/; do
        name=$(basename "$ws")
        marker="  "
        [ "$ws" = "$active/" ] && marker="▶ "
        desc=""
        for f in "$ws/WORKSPACE_BRIEF.md" "$ws/INSTRUCTIONS.md" "$ws/current_task.md"; do
            if [ -f "$f" ]; then
                desc=$(grep -v "^#" "$f" | head -1 | cut -c1-60)
                [ -n "$desc" ] && break
            fi
        done
        echo "  $marker$name  $desc"
    done
    exit 0
fi

# ── Resolve target workspace ───────────────────────────────────────────────────
if [ -n "$TARGET_WS" ]; then
    # Accept "ws_2", "2", or full path
    if [ -d "$TARGET_WS" ]; then
        WORKSPACE="$TARGET_WS"
    elif [ -d "$WORKSPACES_ROOT/$TARGET_WS" ]; then
        WORKSPACE="$WORKSPACES_ROOT/$TARGET_WS"
    elif [ -d "$WORKSPACES_ROOT/ws_$TARGET_WS" ]; then
        WORKSPACE="$WORKSPACES_ROOT/ws_$TARGET_WS"
    else
        err "Workspace not found: $TARGET_WS"
        err "Run: ~/reset_workspace.sh --list"
        exit 1
    fi
else
    # Use active workspace
    if [ -f "$ACTIVE_WS_FILE" ]; then
        WORKSPACE=$(cat "$ACTIVE_WS_FILE")
    else
        # Fall back to legacy workspace/ path if workspaces not set up yet
        WORKSPACE="$JARVIS_ROOT/workspace"
    fi
fi

WS_NAME=$(basename "$WORKSPACE")
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUPS_ROOT/$WS_NAME/$TIMESTAMP"

# ── Resolve internal paths ────────────────────────────────────────────────────
PROTECTED="$WORKSPACE/protected"
SANDBOX="$WORKSPACE/sandbox"
MASTER="$PROTECTED/qcai_3d_master.py"
PROMOTED="$WORKSPACE/qcai_3d.py"

# Clean base search order: workspace clean base → ws_1 clean base → Downloads
CLEAN_BASE=""
for candidate in \
    "$WORKSPACE/qcai_3d_CLEAN_BASE.py" \
    "$WORKSPACES_ROOT/ws_1/qcai_3d_CLEAN_BASE.py" \
    "$JARVIS_ROOT/workspace/qcai_3d_CLEAN_BASE.py" \
    "$HOME/Downloads/qcai_3d.py"; do
    if [ -f "$candidate" ]; then
        CLEAN_BASE="$candidate"
        break
    fi
done

# ── Header ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}  🔄 QCAI Workspace Reset v9.1${NC}"
echo -e "  Workspace: ${CYAN}$WS_NAME${NC} ($WORKSPACE)"
[ "$DRY_RUN" = true ] && echo -e "  ${YELLOW}DRY RUN — no changes will be made${NC}"
echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# ── Preflight ─────────────────────────────────────────────────────────────────
section "Preflight"

if [ ! -d "$WORKSPACE" ]; then
    err "Workspace directory not found: $WORKSPACE"
    exit 1
fi
log "Workspace exists: $WS_NAME"

if [ -z "$CLEAN_BASE" ]; then
    err "No clean base file found. Checked:"
    err "  $WORKSPACE/qcai_3d_CLEAN_BASE.py"
    err "  $WORKSPACES_ROOT/ws_1/qcai_3d_CLEAN_BASE.py"
    err "  $HOME/Downloads/qcai_3d.py"
    err "Place a clean qcai_3d.py in one of those locations and retry."
    exit 1
fi
BASE_LINES=$(wc -l < "$CLEAN_BASE")
log "Clean base: $(basename "$CLEAN_BASE") ($BASE_LINES lines)"
log "Backup destination: $BACKUP_DIR"

# ── Safe backup function ───────────────────────────────────────────────────────
safe_backup() {
    local src="$1"
    local rel="${src#$WORKSPACE/}"   # relative path within workspace
    local dest="$BACKUP_DIR/$rel"
    if [ -e "$src" ] && [ "$DRY_RUN" = false ]; then
        mkdir -p "$(dirname "$dest")"
        cp -r "$src" "$dest"
    fi
}

safe_remove() {
    local target="$1"
    if [ -e "$target" ]; then
        safe_backup "$target"
        if [ "$DRY_RUN" = false ]; then
            rm -rf "$target"
        else
            echo "    [DRY-RUN] would remove: $target"
        fi
    fi
}

safe_remove_contents() {
    local dir="$1"
    if [ -d "$dir" ]; then
        for item in "$dir"/*; do
            [ -e "$item" ] || continue
            safe_backup "$item"
            if [ "$DRY_RUN" = false ]; then
                rm -rf "$item"
            else
                echo "    [DRY-RUN] would remove: $item"
            fi
        done
    fi
}

# ── Create backup root ────────────────────────────────────────────────────────
section "Creating backup"
if [ "$DRY_RUN" = false ]; then
    mkdir -p "$BACKUP_DIR"
    log "Backup folder: $BACKUP_DIR"
else
    echo "    [DRY-RUN] would create: $BACKUP_DIR"
fi

# ── Ensure folder structure ───────────────────────────────────────────────────
section "Verifying folder structure"
if [ "$DRY_RUN" = false ]; then
    mkdir -p \
        "$PROTECTED" "$SANDBOX" \
        "$WORKSPACE/versions/intake" \
        "$WORKSPACE/versions/prime" \
        "$WORKSPACE/versions/builder" \
        "$WORKSPACE/versions/physics" \
        "$WORKSPACE/versions/output" \
        "$WORKSPACE/versions/coordinator" \
        "$WORKSPACE/checkpoints" \
        "$WORKSPACE/logs" \
        "$WORKSPACE/components_master" \
        "$WORKSPACE/components_promoted" \
        "$WORKSPACE/components_sandbox"
fi
log "Folder structure ready"

# ── Restore clean base ────────────────────────────────────────────────────────
section "Restoring clean base"
if [ "$DRY_RUN" = false ]; then
    # Back up existing promoted and master before overwriting
    safe_backup "$MASTER"
    safe_backup "$PROMOTED"
    cp "$CLEAN_BASE" "$MASTER"
    cp "$CLEAN_BASE" "$PROMOTED"
    log "protected/qcai_3d_master.py  ← $BASE_LINES lines"
    log "qcai_3d.py                   ← $BASE_LINES lines (promoted)"
else
    echo "    [DRY-RUN] would restore clean base to master + promoted"
fi

# ── Clear sandbox ─────────────────────────────────────────────────────────────
section "Clearing sandbox"
safe_remove "$SANDBOX/qcai_3d_working.py"
safe_remove "$SANDBOX/qcai_3d_candidate.py"
[ "$DRY_RUN" = false ] && log "sandbox/ cleared (backed up)" || true

# ── Remove stale agent output files ───────────────────────────────────────────
section "Removing stale agent outputs"
for f in \
    "$WORKSPACE/builder_code.py" \
    "$WORKSPACE/intake_brief.md" \
    "$WORKSPACE/physics_report.md" \
    "$WORKSPACE/prime_plan.md" \
    "$WORKSPACE/coordinator_sequence.md" \
    "$WORKSPACE/qcai_3d_running.py"; do
    safe_remove "$f"
done
[ "$DRY_RUN" = false ] && log "Stale agent files removed (backed up)" || true

# ── Clear versioned history ───────────────────────────────────────────────────
section "Clearing version history"
for dir in \
    "$WORKSPACE/versions/intake" \
    "$WORKSPACE/versions/prime" \
    "$WORKSPACE/versions/builder" \
    "$WORKSPACE/versions/physics" \
    "$WORKSPACE/versions/output" \
    "$WORKSPACE/versions/coordinator"; do
    safe_remove_contents "$dir"
done
[ "$DRY_RUN" = false ] && log "Version history cleared (backed up)" || true

# ── Clear component sandbox ───────────────────────────────────────────────────
section "Clearing component sandbox"
safe_remove_contents "$WORKSPACE/components_sandbox"
[ "$DRY_RUN" = false ] && log "components_sandbox/ cleared (backed up)" || true

# ── Clear checkpoints ────────────────────────────────────────────────────────
section "Clearing checkpoints"
safe_remove_contents "$WORKSPACE/checkpoints"
[ "$DRY_RUN" = false ] && log "Checkpoints cleared (backed up)" || true

# ── Reset logs (keep structure, clear content) ────────────────────────────────
section "Resetting logs"
if [ "$DRY_RUN" = false ]; then
    safe_backup "$WORKSPACE/logs/CHANGELOG.md"
    safe_backup "$WORKSPACE/logs/SUMMARY.md"
    safe_remove "$WORKSPACE/logs/metrics_log.jsonl"
    echo "# QCAI Agent Loop — Changelog" > "$WORKSPACE/logs/CHANGELOG.md"
    echo ""                              >> "$WORKSPACE/logs/CHANGELOG.md"
    echo "# QCAI Physics Summary Log"   > "$WORKSPACE/logs/SUMMARY.md"
    echo ""                             >> "$WORKSPACE/logs/SUMMARY.md"
    log "Logs reset (old logs backed up)"
else
    echo "    [DRY-RUN] would reset CHANGELOG.md and SUMMARY.md"
fi

# ── Files intentionally kept ──────────────────────────────────────────────────
section "Files preserved (not touched)"
for f in \
    "$WORKSPACE/current_task.md" \
    "$WORKSPACE/GROUND_TRUTH.md" \
    "$WORKSPACE/INSTRUCTIONS.md" \
    "$WORKSPACE/WORKSPACE_BRIEF.md"; do
    [ -f "$f" ] && echo "  🔒 $(basename "$f")" || true
done

# ── Backup manifest ───────────────────────────────────────────────────────────
if [ "$DRY_RUN" = false ] && [ -d "$BACKUP_DIR" ]; then
    find "$BACKUP_DIR" -type f | wc -l > /tmp/backup_count
    BACKUP_COUNT=$(cat /tmp/backup_count)
    echo "{\"workspace\":\"$WS_NAME\",\"timestamp\":\"$TIMESTAMP\",\"files_backed_up\":$BACKUP_COUNT}" \
        > "$BACKUP_DIR/manifest.json"
fi

# ── Final state ───────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}  ✅ Workspace reset complete — $WS_NAME${NC}"
echo ""
echo "  Clean base:  $BASE_LINES lines  [$(basename "$CLEAN_BASE")]"
if [ "$DRY_RUN" = false ]; then
    BCOUNT=$(find "$BACKUP_DIR" -type f 2>/dev/null | wc -l)
    echo "  Backup:      $BCOUNT files → $BACKUP_DIR"
fi
echo ""
echo "  Kept:  current_task.md  GROUND_TRUTH.md  INSTRUCTIONS.md"
echo "  Reset: sandbox  versions  components_sandbox  checkpoints  logs"
echo ""
echo "  Next: ~/launch_qcai.sh  →  LOAD_TASK in Slack"
echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
