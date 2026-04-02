import json

# Logic to prioritize 'Compression' tasks if the system detects logic gaps
def update_queue(priority_task):
    with open("/var/home/kmonette/OpenJarvis/config/queue.json", "r+") as f:
        queue = json.load(f)
        queue.insert(0, priority_task) # Force to the front
        f.seek(0)
        json.dump(queue, f)
