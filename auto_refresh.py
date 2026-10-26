
import subprocess
import sys
import time
from datetime import datetime

while True:
    print(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}] Starting refresh...", flush=True)

    try:
        subprocess.run(
            [sys.executable, "live_sync.py"],
            check=True
        )

        subprocess.run(
            [sys.executable, "excel_live_report.py"],
            check=True
        )

        print("Refresh completed successfully.", flush=True)

    except subprocess.CalledProcessError as error:
        print(f"Refresh failed: {error}", flush=True)

    print("Next refresh in 5 minutes. Press Ctrl+C to stop.", flush=True)
    time.sleep(300)
