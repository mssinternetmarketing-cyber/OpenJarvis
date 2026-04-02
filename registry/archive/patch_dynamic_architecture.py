import os, re

JARVIS_ROOT = "/var/home/kmonette/OpenJarvis"

# The dynamic discovery engine that replaces the hardcoded list
dynamic_code = """# ─── Dynamic Component Registry ───
import os
MASTER_DIR = "/var/home/kmonette/OpenJarvis/components_master"
try:
    # Dynamically discovers c01_header.py, c02_physics.py, etc. and sorts them natively.
    # Zero hardcoding required. The system auto-expands as you drop files into master.
    COMPONENT_ORDER = sorted([f[:-3] for f in os.listdir(MASTER_DIR) if f.startswith('c') and f.endswith('.py')])
except Exception:
    COMPONENT_ORDER = []
"""

for filename in ["assembler.py", "component_manager.py"]:
    path = os.path.join(JARVIS_ROOT, filename)
    if os.path.exists(path):
        with open(path, "r") as f:
            code = f.read()
        
        # Strip out the static list and inject the dynamic self-discovery engine
        code = re.sub(r'COMPONENT_ORDER\s*=\s*\[.*?\]', dynamic_code, code, flags=re.DOTALL)
        
        with open(path, "w") as f:
            f.write(code)
        print(f"✅ Removed hardcoding from {filename}. It is now dynamically self-discovering.")
