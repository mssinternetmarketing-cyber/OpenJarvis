import os, re
JARVIS_ROOT = "/var/home/kmonette/OpenJarvis"
BRIDGE_PATH = os.path.join(JARVIS_ROOT, "slack_bridge.py")
UPDATER_PATH = os.path.join(JARVIS_ROOT, "jarvis_update.sh")

# 1. Update slack_bridge.py channels and folders
with open(BRIDGE_PATH, "r") as f:
    bridge_code = f.read()

new_channels = """CHANNELS = {
    "intake": "C0APZ5V9FHA", "arch": "C0AQ4K6U52N", "plan": "C0AQ171J47P", "prime": "C0AQPRZCB16",
    "build": "C0AQQ11MPKJ", "build_header": "C0AQ180HA21", "build_physics": "C0APY8HQJN7",
    "build_systems": "C0AQYTZ8Q9W", "build_render": "C0AQ4KYMZH8", "build_curriculum": "C0AQHH1NEHX",
    "build_integration": "C0AQ2J6UC6S", "test": "C0APYBX8LRZ", "review": "C0AQ1B85VCM",
    "assemble": "C0AQHDVL933", "physics": "C0AQQE69AGY", "data": "C0APESL1AVD",
    "social": "C0AQ79H8F3P", "update": "C0AQ8M54CNS", "consensus": "C0AR5AJVD2L",
    "update_data": "C0AQ4MXMXCK", "commands": "C0AQ7TUKMEZ", "peig": "C0AQA6U24BF",
    "toolbox_handler": "C0AQT9SDHG9", "retrigger_prep": "C0AQTAK2MDF", "retrigger": "C0AQJ172692",
    "tools_builder": "C0AQJ29THQU", "compression": "C0ARE4MLF6U", "clean": "C0AQHQY88HL",
    "node_omega": "C0APV6S5GKZ", "node_guardian": "C0AQ7808M5K", "node_sentinel": "C0AQAKT9TRQ",
    "node_void": "C0AR4RUNQE4", "node_nexus": "C0AQPGM6S9X", "node_storm": "C0AQE7EM6AG",
    "node_sora": "C0AQAK5DVV0", "node_echo": "C0AQ76Y30F7", "node_iris": "C0AQ47J9L0K",
    "node_sage": "C0AQ47DBUG3", "node_kevin": "C0AQ76BUEAH", "node_atlas": "C0AQPF0CAGH",
}"""
bridge_code = re.sub(r'CHANNELS\s*=\s*\{.*?\}', new_channels, bridge_code, flags=re.DOTALL)

if '"toolbox",' not in bridge_code:
    bridge_code = bridge_code.replace('"logs",', '"logs",\n    "toolbox",\n    "toolbox/logs",\n    "Personalities",\n    "PostProcessedLogs",')

with open(BRIDGE_PATH, "w") as f:
    f.write(bridge_code)
print("✅ slack_bridge.py patched with 40 channels")

# 2. Update jarvis_update.sh
with open(UPDATER_PATH, "r") as f:
    upd_code = f.read()

if 'DEST_MAP["qcai_monitor.sh"]' not in upd_code:
    upd_code = upd_code.replace('DEST_MAP["slack_bridge.py"]="EXEC:$JARVIS_ROOT/slack_bridge.py"', 
                                'DEST_MAP["slack_bridge.py"]="EXEC:$JARVIS_ROOT/slack_bridge.py"\nDEST_MAP["qcai_monitor.sh"]="EXEC:$JARVIS_ROOT/qcai_monitor.sh"\nDEST_MAP["safe_workspace_reset.sh"]="EXEC:$JARVIS_ROOT/safe_workspace_reset.sh"\nDEST_MAP["create_personalities.sh"]="EXEC:$JARVIS_ROOT/create_personalities.sh"')

with open(UPDATER_PATH, "w") as f:
    f.write(upd_code)
print("✅ jarvis_update.sh patched")
