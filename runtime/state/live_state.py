import time
import traceback

from runtime.state.system_state import build_system_state


INTERVAL_SECONDS = 5


def main():
    print("[AI-LAB] live_state started")
    print(f"[AI-LAB] refresh interval: {INTERVAL_SECONDS}s")

    while True:
        try:
            build_system_state()
            print("[AI-LAB] snapshot refreshed")
        except Exception as exc:
            print("[AI-LAB] ERROR refreshing snapshot")
            print(str(exc))
            traceback.print_exc()

        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
