import subprocess
import time

while True:
    subprocess.run(["python", "main.py"])
    print("\nCompleted! 24h pause")
    time.sleep(60*24)
