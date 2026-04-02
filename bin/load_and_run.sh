#!/usr/bin/env bash
# load_and_run.sh
# Loads Slack tokens from OpenJarvis vault into environment, then runs the bridge.

set -e

echo "Loading tokens from OpenJarvis vault..."

export SLACK_BOT_TOKEN=$(jarvis vault get SLACK_BOT_TOKEN 2>/dev/null | tail -1)
export SLACK_APP_TOKEN=$(jarvis vault get SLACK_APP_TOKEN 2>/dev/null | tail -1)
export SLACK_SIGNING_SECRET=$(jarvis vault get SLACK_SIGNING_SECRET 2>/dev/null | tail -1)

if [[ -z "$SLACK_BOT_TOKEN" || -z "$SLACK_APP_TOKEN" || -z "$SLACK_SIGNING_SECRET" ]]; then
    echo "❌ Could not load tokens from vault. Make sure jarvis vault set was run."
    exit 1
fi

echo "✅ Tokens loaded"
echo "Starting Slack bridge..."

python3 /var/home/kmonette/OpenJarvis/slack_bridge.py
