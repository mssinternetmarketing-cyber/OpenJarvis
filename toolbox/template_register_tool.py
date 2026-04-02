import json, sys, os

# USAGE: python3 template_register_tool.py <id> <command> <description>
if len(sys.argv) < 4:
    print("❌ Usage: python3 template_register_tool.py <id> <command> <description>")
    sys.exit(1)

tool_id = sys.argv[1]
command = sys.argv[2]
description = sys.argv[3]
path = "/var/home/kmonette/OpenJarvis/config/tools.json"

try:
    with open(path, "r") as f:
        tools = json.load(f)

    tools[tool_id] = {
        "command": command,
        "description": description,
        "access_level": "standard"
    }

    with open(path, "w") as f:
        json.dump(tools, f, indent=4)
    print(f"📦 Registered: {tool_id}")
except Exception as e:
    print(f"❌ Failed to register tool: {e}")
