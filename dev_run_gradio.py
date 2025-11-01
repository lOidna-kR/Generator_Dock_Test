"""Development helper to run app_gradio.py with auto-reload.

Usage:
    python dev_run_gradio.py

This script watches Python files in the project directory and restarts
`app_gradio.py` automatically whenever a change is detected.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from watchfiles import PythonFilter, run_process


ROOT = Path(__file__).resolve().parent
APP_PATH = ROOT / "app_gradio.py"


def launch() -> int:
    """Start the Gradio app as a subprocess."""

    print("🚀 Gradio 앱을 실행합니다…")
    return subprocess.call([sys.executable, str(APP_PATH)], cwd=str(ROOT))


def main() -> None:
    if not APP_PATH.exists():
        print("app_gradio.py 파일을 찾을 수 없습니다. 경로를 확인하세요.")
        sys.exit(1)

    ignore_paths = {
        ROOT / "venv",
        ROOT / "Data" / "Result",
        ROOT / "Logs",
        ROOT / ".git",
    }

    print("🔁 Auto-reload 모드로 Gradio 앱을 실행합니다.")
    print("   Python 파일이 변경되면 프로세스가 자동으로 재시작됩니다. (Ctrl+C 종료)")

    run_process(
        str(ROOT),
        target=launch,
        watch_filter=PythonFilter(ignore_paths={str(path) for path in ignore_paths}),
    )


if __name__ == "__main__":
    main()
