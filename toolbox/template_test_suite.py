import subprocess, sys

# USAGE: python3 template_test_suite.py <command_name>
def test_tool(cmd):
    print(f"🧪 Testing Tool Integrity: {cmd}")
    result = subprocess.run([cmd, "--help"], capture_output=True)
    if result.returncode == 0 or result.returncode == 2: # Typical success/help codes
        print(f"✅ Tool '{cmd}' passed initial flight test.")
        return True
    print(f"❌ Tool '{cmd}' failed. Rolling back registration.")
    return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_tool(sys.argv[1])
