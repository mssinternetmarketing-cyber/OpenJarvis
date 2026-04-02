import os, sys, subprocess

ROOT = "/var/home/kmonette/OpenJarvis"
ENV_PATH = os.path.join(ROOT, "config/.env")
BIN_PATH = os.path.join(ROOT, "bin/launch_qcai.sh")
LOG_PATH = os.path.join(ROOT, "logs/debug.log")

def diagnostic():
    print(f"👻 QCAI Ghost Check: Initiating Deep Scan...\n{'-'*40}")
    fail_flag = False

    # 1. Secret Vault Check
    if os.path.exists(ENV_PATH):
        print("🔑 Secrets: [SECURE] File found in config/")
        if "--reveal-secrets" in sys.argv:
            print("🔓 REVEALING SECRETS:")
            with open(ENV_PATH, 'r') as f:
                print(f.read())
    else:
        print("❌ Secrets: [MISSING] Potential system amnesia.")
        fail_flag = True

    # 2. Execution Permissions (Corrected to X_OK)
    if os.access(BIN_PATH, os.X_OK):
        print("🚀 Launcher: [READY] Execution bits confirmed.")
    else:
        print("❌ Launcher: [PERMISSION DENIED] Check chmod settings.")
        fail_flag = True

    # 3. I/O Stream Check
    try:
        # Ensure log dir exists
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, 'a'):
            os.utime(LOG_PATH, None)
        print("📝 Logs: [OPEN] Write access verified.")
    except Exception as e:
        print(f"❌ Logs: [LOCKED] {e}")
        fail_flag = True

    # 4. Storage Check
    try:
        usage = subprocess.check_output(['df', '-h', ROOT]).decode().split('\n')[1].split()
        print(f"💾 Storage: [{usage[4]} used] Available space on {usage[0]}")
    except:
        print("💾 Storage: [⚠️] Could not retrieve disk metrics.")

    print(f"{'-'*40}")
    if fail_flag:
        print("⚠️ GHOST CHECK FAILED: Correct errors before starting Marathon.")
        sys.exit(1)
    else:
        print("✨ GHOST CHECK PASSED: System is stable.")

if __name__ == "__main__":
    diagnostic()
