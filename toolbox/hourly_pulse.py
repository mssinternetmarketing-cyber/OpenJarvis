import time, os, subprocess
def trigger_pulse():
    print("🕒 Hourly Pulse Initiated...")
    subprocess.run(["python3", "/var/home/kmonette/OpenJarvis/agents/compression_agent.py"])
if __name__ == "__main__":
    trigger_pulse()
