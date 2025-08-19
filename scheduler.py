import subprocess
import time
import os

# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "credentials/secret-manager.json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/home/artem_iakovenko/service-account/secret-manager.json"

while True:
    subprocess.run(["python", "main.py"])
    print("\nCompleted! 24h pause")
    time.sleep(60*24)
