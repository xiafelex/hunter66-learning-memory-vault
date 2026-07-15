#!/usr/bin/env python3
"""Runs the native screen-capture agent, then hands its JSON to the local vault writer."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / "private" / "sync-console"
AGENT = Path.home() / "Library" / "Application Support" / "Hunter66" / "Hunter66SyncAgent.app" / "Contents" / "MacOS" / "Hunter66SyncAgent"
GROUP = "六六班级"


def main() -> None:
    if (Path.home() / ".local" / "bin" / "wechat-cli").exists():
        subprocess.run([sys.executable, str(Path(__file__).with_name("server.py")), "--sync-once"], check=True)
        return
    if not AGENT.exists():
        raise SystemExit("Hunter66 Sync Agent 尚未安装。请先运行 native/build_agent.sh。")
    PRIVATE.mkdir(parents=True, exist_ok=True)
    output = PRIVATE / "scheduled-capture.json"
    # LaunchServices preserves the app bundle identity for macOS TCC permissions.
    # Running the inner executable directly from launchd does not.
    subprocess.run(
        ["/usr/bin/open", "-W", str(AGENT), "--args", "--group", GROUP, "--output", str(output)],
        check=True,
    )
    subprocess.run([sys.executable, str(Path(__file__).with_name("server.py")), "--sync-input", str(output)], check=True)


if __name__ == "__main__":
    main()
