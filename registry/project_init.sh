#!/usr/bin/env bash
# Purpose: Automated Workspace Creator for Option 3
PROJECT_NAME=$1
TASK_DESC=$2

if [ -z "$PROJECT_NAME" ]; then echo "Usage: !start -> Option 3 -> [Name] [Task]"; exit 1; fi

# 1. Create Environment
bash /var/home/kmonette/OpenJarvis/registry/switch_env.sh "$PROJECT_NAME" "standard"

# 2. Assign Mission
echo "# Project: $PROJECT_NAME" > "/var/home/kmonette/OpenJarvis/workspaces/$PROJECT_NAME/foundation/mission.md"
echo "**Task Description:** $TASK_DESC" >> "/var/home/kmonette/OpenJarvis/workspaces/$PROJECT_NAME/foundation/mission.md"

# 3. Notify Slack
python3 -c "import requests, os; token=os.environ.get('SLACK_BOT_TOKEN'); requests.post('https://slack.com/api/chat.postMessage', headers={'Authorization': f'Bearer {token}'}, json={'channel': 'C0APZ5V9FHA', 'text': '✅ Workspace $PROJECT_NAME Initialized. Mission: $TASK_DESC. Agents standby.'})"
