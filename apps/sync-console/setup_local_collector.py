#!/usr/bin/env python3
"""Install the local dependencies needed by the Accessibility-based collector."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"


def main() -> None:
    if not VENV.exists():
        subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=True)
    pip = VENV / "bin" / "pip"
    subprocess.run([
        str(pip), "install", "--upgrade", "pip", "pillow", "pyobjc-framework-Cocoa",
        "pyobjc-framework-ApplicationServices", "pyobjc-framework-Vision",
    ], check=True)
    print("安装完成。请在系统设置中为启动本服务的终端授予：辅助功能、屏幕录制。")


if __name__ == "__main__":
    main()
