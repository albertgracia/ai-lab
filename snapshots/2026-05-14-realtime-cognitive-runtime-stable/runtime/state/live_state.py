import shutil
import time
import traceback
from datetime import datetime
from pathlib import Path

from runtime.state.system_state import build_system_state


INTERVAL_SECONDS = 5
HISTORY_INTERVAL_SECONDS = 60

CURRENT_SNAPSHOT = Path("/opt/ai-lab-data/snapshots/current/system_snapshot.json")
HISTORY_ROOT = Path("/opt/ai-lab-data/snapshots/history")


def save_history_snapshot():
    if not CURRENT_SNAPSHOT.exists():
        return

    now = datetime.now()
    day_dir = HISTORY_ROOT / now.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)

    target = day_dir / f"system_snapshot_{now.strftime('%H-%M-%S')}.json"
    shutil.copy2(CURRENT_SNAPSHOT, target)


def main():
    print("[AI-LAB] live_state started")
    print(f"[AI-LAB] refresh interval: {INTERVAL_SECONDS}s")

    last_history = 0

    while True:
        try:
            build_system_state()
            print("[AI-LAB] snapshot refreshed")

            now = time.time()
            if now - last_history >= HISTORY_INTERVAL_SECONDS:
                save_history_snapshot()
                print("[AI-LAB] history snapshot saved")
                last_history = now

        except Exception as exc:
            print("[AI-LAB] ERROR refreshing snapshot")
            print(str(exc))
            traceback.print_exc()

        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
