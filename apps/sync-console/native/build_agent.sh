#!/bin/zsh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$HOME/Library/Application Support/Hunter66/Hunter66SyncAgent.app"
mkdir -p "$APP/Contents/MacOS"
swiftc "$ROOT/native/Sources/main.swift" -o "$APP/Contents/MacOS/Hunter66SyncAgent" -framework Cocoa -framework Vision -framework CoreGraphics -framework ApplicationServices
cp "$ROOT/native/Info.plist" "$APP/Contents/Info.plist"
codesign --force --deep --sign - "$APP" >/dev/null
echo "$APP"
