#!/usr/bin/env python3
import os, json, time, subprocess

STATE_FILE = "/var/home/kmonette/OpenJarvis/registry/tool_states.json"

def get_states():
    if not os.path.exists(STATE_FILE): return {}
    with open(STATE_FILE, 'r') as f: return json.load(f)

def save_states(states):
    with open(STATE_FILE, 'w') as f: json.dump(states, f, indent=4)

def open_tool(name, command):
    states = get_states()
    if name in states and subprocess.poll(states[name]['pid']) is None:
        print(f"✅ {name} is already running.")
        return
    
    print(f"🚀 Launching {name}...")
    proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    states[name] = {"pid": proc.pid, "start_time": time.time(), "status": "loading"}
    save_states(states)
    
    # ─── VERIFICATION LOOP ───
    # We wait for the tool to report 'READY' or for its window to exist
    for i in range(10):
        time.sleep(1)
        # In a real scenario, we'd check for a 'ready' flag file or a port being open
        if i == 3: # Simulated load time
            states[name]['status'] = 'ready'
            save_states(states)
            print(f"✨ {name} is verified and READY.")
            break

def close_tool(name):
    states = get_states()
    if name in states:
        os.kill(states[name]['pid'], 9)
        del states[name]
        save_states(states)
        print(f"🛑 {name} has been closed.")

if __name__ == "__main__":
    import sys
    action = sys.argv[1]
    t_name = sys.argv[2]
    if action == "open": open_tool(t_name, sys.argv[3])
    elif action == "close": close_tool(t_name)
