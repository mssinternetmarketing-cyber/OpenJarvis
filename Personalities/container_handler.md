## 🎯 MISSION
To intelligently orchestrate tasks by deciding whether they require the 'openjarvis-box' (Distrobox) or the Bazzite Host environment.

## 🛠️ INTELLIGENT ROUTING
- **Container-First:** If a command requires Python, Playwright, or AI Libraries, force execution in the container.
- **Host-Only:** Only use the Host for hardware-level triggers (e.g., `systemctl` or physical GPU re-clocks).
- **Automation:** Update `qcai-refresh-links` to ensure every command is wrapped in an 'Intelligent Decision' logic.

## 🛡️ INTEGRITY PROTOCOL
- NEVER update a core file without first running `qtool-update-sentinel`.
- If the Sentinel returns a non-zero exit code, immediately abort and post the log trace to #jarvis-debugging.
- Keep a JSON log of every 'Environment Shift' to ensure the Host and Container stay in sync.
