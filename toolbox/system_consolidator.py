import os, shutil

ROOT = "/var/home/kmonette/OpenJarvis"
STRUCTURE = {
    "bin": ["launch_qcai.sh", "stop_qcai.sh", "registry/refresh_links.sh"],
    "core": ["slack_bridge.py", "qcai_modern_3d.py", "qcai_token_monitor.py"],
    "config": [".env", "ENV_STATUS.json", "SYSTEM_STATUS.json", "registry/agents.json", "registry/tools.json", "registry/pulse_config.json"],
    "data": ["registry/truth.json", "registry/update_history.json", "workspaces"],
    "archive": [] # Purifier handles this
}

def consolidate():
    print("🏗️ Consolidator: Building Sovereign Structure...")
    for folder in STRUCTURE:
        folder_path = os.path.join(ROOT, folder)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

    # Move files based on the manifest
    for folder, files in STRUCTURE.items():
        for item in files:
            source = os.path.join(ROOT, item)
            dest = os.path.join(ROOT, folder, os.path.basename(item))
            
            if os.path.exists(source):
                print(f"🚚 Moving {item} -> {folder}/")
                # Use move for files, copytree for folders if needed
                if os.path.isdir(source):
                    if not os.path.exists(dest):
                        shutil.copytree(source, dest)
                        shutil.rmtree(source)
                else:
                    shutil.move(source, dest)

    print("✅ Consolidation Complete. OpenJarvis is now a Modular Entity.")

if __name__ == "__main__":
    consolidate()
