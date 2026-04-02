#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# qcai-install-commands — Install or refresh all QCAI host commands
#
# ONE COMMAND that does everything:
#   1. Verifies install_host_commands.sh is present and up to date
#   2. Runs it to create/refresh all ~/bin wrappers
#   3. Ensures ~/bin is in PATH
#   4. Rebuilds wrappers for any agent-created commands in the registry
#   5. Reports full command list when done
#
# Safe to run multiple times — idempotent.
# Protected commands are always reinstalled from source; they cannot be
# overwritten by agent tools. Agent tools are reinstalled from their
# commands/scripts/ registry entries.
#
# Usage:
#   qcai-install-commands              # install everything
#   qcai-install-commands --check      # check what's installed, no changes
#   qcai-install-commands --agent-only # only reinstall agent-created tools
#   qcai-install-commands --host-only  # only reinstall system commands
#
# Can be run from HOST terminal or inside distrobox.
# Agents can invoke this via: bash $JARVIS_ROOT/qcai-install-commands.sh
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

JARVIS_ROOT="/var/home/kmonette/OpenJarvis"
BIN_DIR="$HOME/bin"
COMMANDS_HOST_DIR="$JARVIS_ROOT/commands"
INSTALL_SCRIPT="$JARVIS_ROOT/install_host_commands.sh"
COMMANDS_JSON="$COMMANDS_HOST_DIR/registry/commands.json"
DISTROBOX_NAME="openjarvis-box"

# ── Colors ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'
BOLD='\033[1m'; NC='\033[0m'; RED='\033[0;31m'; BLUE='\033[0;34m'

log()     { echo -e "${GREEN}  ✅${NC} $*"; }
warn()    { echo -e "${YELLOW}  ⚠️ ${NC} $*"; }
err()     { echo -e "${RED}  ❌${NC} $*"; }
info()    { echo -e "${BLUE}  ℹ️ ${NC} $*"; }
section() { echo -e "\n${BOLD}${CYAN}$*${NC}"; }

# ── Flags ─────────────────────────────────────────────────────────────────────
CHECK_ONLY=false
AGENT_ONLY=false
HOST_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --check)      CHECK_ONLY=true ;;
        --agent-only) AGENT_ONLY=true ;;
        --host-only)  HOST_ONLY=true ;;
        --help|-h)
            head -40 "$0" | grep "^#" | sed 's/^# \?//'
            exit 0 ;;
    esac
done

# ── Protected commands — these are ALWAYS reinstalled from install_host_commands.sh
# Agents cannot overwrite or remove these.
PROTECTED_COMMANDS=(
    qcai-launch qcai-stop qcai-restart qcai-reset qcai-fresh
    qcai-update qcai-status qcai-logs qcai-update-updater
    qcai-viz qcai-viz-pause qcai-viz-resume qcai-viz-update
    qcai-trainer qcai-mode qcai-install-commands
)

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🔧 QCAI Command Installer"
[ "$CHECK_ONLY" = true ] && echo "  Mode: CHECK ONLY (no changes)" || true
[ "$AGENT_ONLY" = true ] && echo "  Mode: Agent tools only" || true
[ "$HOST_ONLY"  = true ] && echo "  Mode: System commands only" || true
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Ensure ~/bin exists and is in PATH ───────────────────────────────────────
mkdir -p "$BIN_DIR"

if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    warn "~/bin not in PATH — adding now for this session"
    export PATH="$BIN_DIR:$PATH"
    # Persist to shell rc
    for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
        if [ -f "$rc" ] && ! grep -q 'HOME/bin' "$rc"; then
            echo "" >> "$rc"
            echo '# QCAI commands' >> "$rc"
            echo 'export PATH="$HOME/bin:$PATH"' >> "$rc"
            log "Added ~/bin to PATH in $rc"
        fi
    done
fi

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: Install / refresh system (protected) commands
# ─────────────────────────────────────────────────────────────────────────────
if [ "$AGENT_ONLY" = false ]; then
    section "Step 1: System Commands (protected)"

    if [ ! -f "$INSTALL_SCRIPT" ]; then
        err "install_host_commands.sh not found at $INSTALL_SCRIPT"
        err "Run 'qcai-update' first to deploy it, then retry."
        exit 1
    fi

    INSTALL_LINES=$(wc -l < "$INSTALL_SCRIPT")
    if [ "$INSTALL_LINES" -lt 50 ]; then
        err "install_host_commands.sh appears to be a stub ($INSTALL_LINES lines)"
        err "Run 'qcai-update' to deploy the real version first."
        exit 1
    fi

    if [ "$CHECK_ONLY" = true ]; then
        info "Would run: bash $INSTALL_SCRIPT"
        info "Checking which protected commands exist:"
        for cmd in "${PROTECTED_COMMANDS[@]}"; do
            if [ -f "$BIN_DIR/$cmd" ]; then
                echo "  ✅ $cmd"
            else
                echo "  ❌ $cmd  (missing)"
            fi
        done
    else
        info "Running install_host_commands.sh ($INSTALL_LINES lines)..."
        bash "$INSTALL_SCRIPT"
        log "System commands installed"

        # Self-install: make this script available as qcai-install-commands
        SELF_PATH="$JARVIS_ROOT/qcai-install-commands.sh"
        if [ -f "$SELF_PATH" ]; then
            cat > "$BIN_DIR/qcai-install-commands" << WRAPPER
#!/usr/bin/env bash
# Install/refresh all QCAI host commands
distrobox enter $DISTROBOX_NAME -- bash "$SELF_PATH" "\$@"
WRAPPER
            chmod +x "$BIN_DIR/qcai-install-commands"
            log "qcai-install-commands → self-registered"
        fi
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: Reinstall agent-created commands from registry
# ─────────────────────────────────────────────────────────────────────────────
if [ "$HOST_ONLY" = false ]; then
    section "Step 2: Agent-Created Commands"

    if [ ! -f "$COMMANDS_JSON" ]; then
        info "No agent command registry found at $COMMANDS_JSON"
        info "(Agents will populate this as they create tools)"
    else
        # Parse JSON with python3 (available in distrobox)
        AGENT_CMDS=$(python3 - << 'PYEOF' 2>/dev/null
import json, sys
try:
    with open("/var/home/kmonette/OpenJarvis/commands/registry/commands.json") as f:
        data = json.load(f)
    active = [c for c in data.get("commands", []) if c.get("status") == "active"]
    for c in active:
        print(f"{c['name']}|{c['script']}|{c.get('description','')[:60]}")
except Exception as e:
    print(f"ERROR:{e}", file=sys.stderr)
PYEOF
        )

        if [ -z "$AGENT_CMDS" ]; then
            info "No active agent commands in registry yet"
        else
            AGENT_COUNT=0
            while IFS='|' read -r cmd_name script_path description; do
                [ -z "$cmd_name" ] && continue

                # Safety: never reinstall if name matches a protected command
                IS_PROTECTED=false
                for pc in "${PROTECTED_COMMANDS[@]}"; do
                    if [ "$cmd_name" = "$pc" ]; then
                        IS_PROTECTED=true
                        break
                    fi
                done

                if [ "$IS_PROTECTED" = true ]; then
                    warn "$cmd_name is protected — skipping agent reinstall"
                    continue
                fi

                if [ "$CHECK_ONLY" = true ]; then
                    if [ -f "$BIN_DIR/$cmd_name" ]; then
                        echo "  ✅ $cmd_name  →  $description"
                    else
                        echo "  ❌ $cmd_name  (missing wrapper)  →  $description"
                    fi
                    continue
                fi

                # Determine script type
                EXT="${script_path##*.}"
                if [ "$EXT" = "sh" ]; then
                    RUNNER="bash"
                else
                    RUNNER="python3"
                fi

                if [ ! -f "$script_path" ]; then
                    warn "$cmd_name: script not found at $script_path — skipping"
                    continue
                fi

                # Write wrapper
                cat > "$BIN_DIR/$cmd_name" << WRAPPER
#!/usr/bin/env bash
# Agent-created command: $cmd_name
# $description
# Script: $script_path
distrobox enter $DISTROBOX_NAME -- $RUNNER "$script_path" "\$@"
WRAPPER
                chmod +x "$BIN_DIR/$cmd_name"
                log "$cmd_name  →  $description"
                AGENT_COUNT=$((AGENT_COUNT + 1))
            done <<< "$AGENT_CMDS"

            [ "$CHECK_ONLY" = false ] && log "$AGENT_COUNT agent command(s) reinstalled" || true
        fi
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: Summary
# ─────────────────────────────────────────────────────────────────────────────
section "Installed Commands"

echo ""
echo "  🔒 Protected system commands:"
for cmd in "${PROTECTED_COMMANDS[@]}"; do
    if [ -f "$BIN_DIR/$cmd" ]; then
        echo "    ✅  $cmd"
    else
        echo "    ❌  $cmd  (not installed)"
    fi
done

echo ""
echo "  🔧 Agent-created commands:"
if [ -f "$COMMANDS_JSON" ]; then
    python3 - << 'PYEOF' 2>/dev/null
import json, os
try:
    bin_dir = os.path.expanduser("~/bin")
    with open("/var/home/kmonette/OpenJarvis/commands/registry/commands.json") as f:
        data = json.load(f)
    active = [c for c in data.get("commands", []) if c.get("status") == "active"]
    if not active:
        print("    (none yet)")
    else:
        for c in active:
            exists = "✅" if os.path.exists(os.path.join(bin_dir, c["name"])) else "❌"
            print(f"    {exists}  {c['name']:<30} {c.get('description','')[:50]}")
except Exception as e:
    print(f"    (registry read error: {e})")
PYEOF
else
    echo "    (no registry yet)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$CHECK_ONLY" = true ]; then
    echo "  Check complete. Run without --check to install."
else
    echo "  ✅ All commands installed. Open a new terminal or run:"
    echo "     source ~/.bashrc"
fi
echo ""
echo "  Useful next steps:"
echo "    qcai-mode status          — check current operating mode"
echo "    qcai-launch               — start the full system"
echo "    LIST COMMANDS  (in Slack) — see all commands including agent tools"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
