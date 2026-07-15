#!/bin/zsh
set -euo pipefail

APP_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPOSITORY_ROOT="$(cd "$APP_ROOT/../.." && pwd)"
TARGET="$HOME/Applications/六六学习记忆.app"
CONTENTS="$TARGET/Contents"
LAUNCHER="$APP_ROOT/native/run_console_server.sh"

cd "$APP_ROOT"
npm run build
rm -rf "$TARGET"
mkdir -p "$CONTENTS/MacOS" "$CONTENTS/Resources"

swiftc "$APP_ROOT/native/Desktop/Sources/main.swift" \
  -parse-as-library \
  -o "$CONTENTS/MacOS/Hunter66LearningMemory" \
  -framework Cocoa -framework WebKit
cp "$APP_ROOT/native/Desktop/Info.plist" "$CONTENTS/Info.plist"
printf '#!/bin/zsh\nexec "%s/apps/sync-console/.venv/bin/python" "%s/apps/sync-console/server.py"\n' "$REPOSITORY_ROOT" "$REPOSITORY_ROOT" > "$CONTENTS/Resources/run-server.sh"
chmod +x "$CONTENTS/Resources/run-server.sh"
codesign --force --deep --sign - "$TARGET" >/dev/null
chmod +x "$LAUNCHER"

# The desktop app owns its child server after the user presses Connect.  A
# launchd agent cannot inherit the same privacy context and caused restart loops.
LEGACY_LABEL="com.xiafelex.hunter66-sync-console"
LEGACY_AGENT="$HOME/Library/LaunchAgents/$LEGACY_LABEL.plist"
launchctl bootout "gui/$(id -u)" "$LEGACY_AGENT" 2>/dev/null || true
rm -f "$LEGACY_AGENT"
echo "$TARGET"
