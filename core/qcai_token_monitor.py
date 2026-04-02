# Purpose: Evolution Training via Token Usage Metrics
import json, time, os

METRICS_FILE = "/var/home/kmonette/OpenJarvis/registry/token_metrics.json"

def log_token_usage(agent_name, token_count, success_rate):
    if not os.path.exists(METRICS_FILE):
        data = {}
    else:
        with open(METRICS_FILE, 'r') as f: data = json.load(f)
    
    if agent_name not in data: data[agent_name] = {"total": 0, "history": []}
    
    data[agent_name]["total"] += token_count
    data[agent_name]["history"].append({
        "timestamp": time.time(),
        "tokens": token_count,
        "success": success_rate
    })
    
    # Prune history to last 100 entries to save RAM
    data[agent_name]["history"] = data[agent_name]["history"][-100:]
    
    with open(METRICS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

print("⚡ Token Evolution Monitor: ONLINE")
