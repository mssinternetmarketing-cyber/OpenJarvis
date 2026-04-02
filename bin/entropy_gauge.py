import os, glob

ROOT = "/var/home/kmonette/OpenJarvis"
LOG_LIMIT_KB = 500  # Threshold to trigger background clean

def check_entropy():
    log_size = os.path.getsize(f"{ROOT}/logs/debug.log") / 1024
    uncompressed_files = len(glob.glob(f"{ROOT}/*.py")) # Files in root that shouldn't be there
    
    if log_size > LOG_LIMIT_KB or uncompressed_files > 0:
        return "HIGH"
    return "LOW"

if __name__ == "__main__":
    print(check_entropy())
