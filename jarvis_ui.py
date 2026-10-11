from jarvis.bootstrap import bootstrap_agent
from jarvis.ui.main_window import run_app


if __name__ == "__main__":
    bootstrap_agent()
    raise SystemExit(run_app())