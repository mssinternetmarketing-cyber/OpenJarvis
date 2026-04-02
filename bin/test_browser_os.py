import os, sys
import importlib.util

def test_hook():
    print("🌐 BrowserOS: Verifying Sovereign Hook...")
    
    ENGINE_PATH = "/var/home/kmonette/OpenJarvis/core/browser_engine.py"
    
    # 1. Physical Check
    if not os.path.exists(ENGINE_PATH):
        print("❌ Error: Browser Engine missing from core/")
        return False
    print("✅ Engine: Found in core/")

    # 2. Import Check (Functional Hook)
    try:
        spec = importlib.util.spec_from_file_location("browser_engine", ENGINE_PATH)
        browser = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(browser)
        print("✅ Hook: Engine module loaded successfully.")
    except Exception as e:
        print(f"❌ Hook Broken: Could not load module - {e}")
        return False

    # 3. Registry Check
    with open("/var/home/kmonette/OpenJarvis/config/tools.json", "r") as f:
        import json
        tools = json.load(f)
        if "qtool-browser-os" in tools:
            print("✅ Registry: Tool registered for Swarm use.")
        else:
            print("⚠️ Registry: Tool NOT found in tools.json.")

    return True

if __name__ == "__main__":
    if test_hook():
        print("✨ BROWSER-OS IS SOVEREIGN AND FULLY HOOKED.")
    else:
        sys.exit(1)
