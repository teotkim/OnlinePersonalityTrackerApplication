import sys
import time
import threading
import traceback
from pathlib import Path

LOG = Path(__file__).parent / "error.log"


def log(msg):
    print(msg)
    with open(LOG, "a") as f:
        f.write(msg + "\n")


try:
    import rag
    import ui
    from monitor import Monitor
    from personality import infer
except Exception:
    LOG.write_text(traceback.format_exc())
    raise

UPDATE_INTERVAL = 60


def inference_loop():
    while True:
        try:
            time.sleep(UPDATE_INTERVAL)
            rag.force_flush()
            context = rag.build_context()
            if not context.strip():
                continue
            ui.update_status("Running inference…", spin=True)
            profile = infer(context)
            rag.insert_snapshot(profile)
            ui.update_profile(profile)
        except Exception as e:
            ui.update_status(f"Inference error: {e}", spin=False)
            log(f"[inference error] {traceback.format_exc()}")


def start_agent(_window):
    try:
        monitor = Monitor()
        threading.Thread(target=inference_loop, daemon=True).start()
        log("[agent] Monitor started.")
        monitor.run(callback=lambda e: rag.push_event(e.app, e.title, e.url, e.duration))
    except Exception:
        log(f"[agent crash] {traceback.format_exc()}")


def main():
    try:
        rag.init()
        agent_thread = threading.Thread(target=start_agent, args=(None,), daemon=True)
        ui.start(on_ready=lambda w: agent_thread.start())
    except Exception:
        log(f"[main crash] {traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
