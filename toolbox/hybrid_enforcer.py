import os, shutil

ROOT = "/var/home/kmonette/OpenJarvis"

# THE ROOT-RESIDENT LIST: Never moved, never touched.
ROOT_RESIDENTS = [
    "CODE_OF_CONDUCT.md", "CONTRIBUTING.md", "ENV_STATUS.json",
    "LICENSE", "mkdocs.yml", "pyproject.toml", "README.md",
    "REVIEW.md", "uv.lock"
]

MAPPING = {
    ".py": "core",
    ".sh": "bin",
    ".json": "config", # Except ENV_STATUS
    ".env": "config"
}

def enforce_hybrid_structure():
    print("🛡️ Enforcer: Aligning Hybrid-Sovereign Structure...")
    
    for item in os.listdir(ROOT):
        item_path = os.path.join(ROOT, item)
        
        # Only process files in the root
        if os.path.isfile(item_path):
            if item in ROOT_RESIDENTS:
                print(f"✅ PROTECTED (Root-Resident): {item}")
                continue
            
            # Logic for moving everything else
            ext = os.path.splitext(item)[1]
            target_folder = MAPPING.get(ext, "archive")
            
            # Security: Ensure we don't move the .env to the wrong place if it's in the list
            if item == ".env": target_folder = "config"

            # Create folder if it doesn't exist
            os.makedirs(os.path.join(ROOT, target_folder), exist_ok=True)

            print(f"📦 Relocating: {item} -> {target_folder}/")
            shutil.move(item_path, os.path.join(ROOT, target_folder, item))

    print("✨ HYBRID STRUCTURE LOCKED.")

if __name__ == "__main__":
    enforce_hybrid_structure()
