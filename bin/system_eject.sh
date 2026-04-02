#!/bin/bash
echo "🛑 INITIATING SOVEREIGN EJECT..."

# 1. Identify the current Shell Level (SHLVL)
echo "Current Shell Level: $SHLVL"

# 2. Clear Environment Path Caches
hash -r
unset OCI_RUNTIME
unset CONTAINER_ID

# 3. Force-Kill any orphaned OpenJarvis processes
echo "🧹 Terminating background agents..."
pkill -f "flow_coordinator"
pkill -f "launch_qcai"

# 4. Instructions for the user to break the nest
echo "------------------------------------------------"
echo "✅ Environment Cleansed."
echo "⚠️  TO FINISH: Type 'exit' manually until the (openjarvis) prefix is GONE."
echo "⚠️  Then run: cd /var/home/kmonette/OpenJarvis"
echo "------------------------------------------------"
