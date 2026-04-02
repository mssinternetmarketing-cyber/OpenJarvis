#!/bin/bash
# USAGE: ./template_new_agent.sh <name> <role_description>
NAME=$1
ROLE=$2

if [ -z "$NAME" ]; then echo "❌ Missing Agent Name"; exit 1; fi

# Create Personality
cat << P_EOF > "/var/home/kmonette/OpenJarvis/Personalities/${NAME}.md"
# 🤖 Agent: ${NAME}
- **Role:** ${ROLE}
- **Constraint:** Follow Sovereign Root Protocols.
P_EOF

# Create Placeholder Logic
cat << L_EOF > "/var/home/kmonette/OpenJarvis/agents/${NAME}.py"
print("🤖 ${NAME} initialized. Scanning for ${ROLE} objectives...")
L_EOF

chmod +x "/var/home/kmonette/OpenJarvis/agents/${NAME}.py"
echo "✅ Specialist '${NAME}' has been birthed into the Swarm."
