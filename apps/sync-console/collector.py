"""Local WeChat reader adapted from BiboyQG/WeChat-MCP's Accessibility approach."""

from __future__ import annotations

import time
import re
from collections import Counter
from typing import Any

import AppKit
from ApplicationServices import (
    AXUIElementCopyAttributeValue, AXUIElementCreateApplication, AXUIElementPerformAction,
    AXUIElementSetAttributeValue, AXIsProcessTrusted, AXValueGetType, AXValueGetValue,
    kAXChildrenAttribute, kAXIdentifierAttribute, kAXListRole, kAXPositionAttribute,
    kAXRaiseAction, kAXRoleAttribute, kAXSizeAttribute, kAXStaticTextRole,
    kAXTextAreaRole, kAXTitleAttribute, kAXValueAttribute, kAXValueCGPointType,
    kAXValueCGSizeType, kAXPlaceholderValueAttribute, kAXWindowsAttribute,
    kAXFocusedWindowAttribute,
)
from Quartz import (
    CGEventCreateKeyboardEvent, CGEventCreateMouseEvent, CGEventCreateScrollWheelEvent,
    CGEventPost, CGEventSetFlags, CGEventSetLocation, CGPoint, kCGEventFlagMaskCommand,
    kCGEventLeftMouseDown, kCGEventLeftMouseUp, kCGHIDEventTap, kCGScrollEventUnitLine,
)

BUNDLE = "com.tencent.xinWeChat"


def ax_get(element: Any, attribute: Any) -> Any:
    error, value = AXUIElementCopyAttributeValue(element, attribute, None)
    return value if error == 0 else None


def walk(element: Any):
    """Walk both ordinary AX children and app-level window roots.

    WeChat 4.x may expose no kAXChildrenAttribute on the application element
    while still exposing its UI beneath kAXWindowsAttribute.
    """
    seen: set[int] = set()

    def visit(node: Any):
        if node is None or id(node) in seen:
            return
        seen.add(id(node))
        yield node
        descendants = list(ax_get(node, kAXChildrenAttribute) or [])
        if attribute(node, kAXRoleAttribute) == "AXApplication":
            descendants.extend(ax_get(node, kAXWindowsAttribute) or [])
            focused = ax_get(node, kAXFocusedWindowAttribute)
            if focused is not None:
                descendants.append(focused)
        for child in descendants:
            yield from visit(child)

    yield from visit(element)


def attribute(element: Any, attr: Any) -> str:
    value = ax_get(element, attr)
    return value if isinstance(value, str) else ""


def get_wechat(activate: bool = True) -> Any:
    apps = AppKit.NSRunningApplication.runningApplicationsWithBundleIdentifier_(BUNDLE)
    if not apps:
        raise RuntimeError("未检测到正在运行的微信。请先登录 Mac 版微信。")
    app = apps[0]
    if activate:
        app.activateWithOptions_(AppKit.NSApplicationActivateIgnoringOtherApps)
    return AXUIElementCreateApplication(app.processIdentifier())


def wechat_is_ready() -> bool:
    try:
        return bool(AXIsProcessTrusted()) and bool(
            AppKit.NSRunningApplication.runningApplicationsWithBundleIdentifier_(BUNDLE)
        )
    except Exception:
        return False


def accessibility_is_trusted() -> bool:
    try:
        return bool(AXIsProcessTrusted())
    except Exception:
        return False


def accessibility_diagnostics() -> dict[str, Any]:
    """Return non-message AX metadata to diagnose WeChat UI changes safely."""
    app = get_wechat(activate=False)
    root_children = ax_get(app, kAXChildrenAttribute) or []
    windows = ax_get(app, kAXWindowsAttribute) or []
    focused = ax_get(app, kAXFocusedWindowAttribute)
    hints: list[dict[str, str]] = []
    roles: Counter[str] = Counter()
    identifiers: list[str] = []
    for element in walk(app):
        role = attribute(element, kAXRoleAttribute)
        identifier = attribute(element, kAXIdentifierAttribute)
        title = attribute(element, kAXTitleAttribute)
        roles[role or "(none)"] += 1
        if identifier and identifier not in identifiers:
            identifiers.append(identifier)
        if role in (kAXTextAreaRole, kAXListRole) or any(
            marker in identifier.lower() for marker in ("search", "session", "message", "title")
        ):
            hints.append({"role": role, "identifier": identifier, "title": title})
    return {
        "trusted": accessibility_is_trusted(),
        "root_role": attribute(app, kAXRoleAttribute),
        "root_children": len(root_children),
        "windows": len(windows),
        "has_focused_window": focused is not None,
        "role_counts": dict(roles.most_common()),
        "identifiers": identifiers[:80],
        "elements": hints[:120],
    }


def point(element: Any) -> tuple[float, float] | None:
    ref = ax_get(element, kAXPositionAttribute)
    if ref is None or AXValueGetType(ref) != kAXValueCGPointType:
        return None
    ok, value = AXValueGetValue(ref, kAXValueCGPointType, None)
    return (float(value.x), float(value.y)) if ok else None


def size(element: Any) -> tuple[float, float] | None:
    ref = ax_get(element, kAXSizeAttribute)
    if ref is None or AXValueGetType(ref) != kAXValueCGSizeType:
        return None
    ok, value = AXValueGetValue(ref, kAXValueCGSizeType, None)
    return (float(value.width), float(value.height)) if ok else None


def point_from_attribute(element: Any, attr: Any, value_type: Any) -> tuple[float, float] | None:
    ref = ax_get(element, attr)
    if ref is None or AXValueGetType(ref) != value_type:
        return None
    ok, value = AXValueGetValue(ref, value_type, None)
    if not ok:
        return None
    return float(value.x), float(value.y)


def find_chat(app: Any, name: str) -> Any | None:
    target = normalize_chat_name(name)
    for element in walk(app):
        identifier = attribute(element, kAXIdentifierAttribute)
        if identifier.startswith("session_item_") and normalize_chat_name(identifier[len("session_item_"):]) == target:
            return element
    return None


def normalize_chat_name(name: str) -> str:
    return re.sub(r"[（(]\d+[）)]$", "", name.strip()).strip()


def current_chat_name(app: Any) -> str | None:
    for element in walk(app):
        if attribute(element, kAXIdentifierAttribute) == "big_title_line_h_view":
            title = attribute(element, kAXValueAttribute) or attribute(element, kAXTitleAttribute)
            return normalize_chat_name(title) if title else None
    return None


def click(element: Any) -> None:
    pos = point(element)
    element_size = size(element)
    if not pos or not element_size:
        raise RuntimeError("无法定位微信群会话的位置。")
    x, y = pos[0] + element_size[0] / 2, pos[1] + element_size[1] / 2
    CGEventPost(kCGHIDEventTap, CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, CGPoint(x, y), 0))
    CGEventPost(kCGHIDEventTap, CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, CGPoint(x, y), 0))


def find_search(app: Any) -> Any | None:
    candidates: list[Any] = []
    for element in walk(app):
        if attribute(element, kAXRoleAttribute) != kAXTextAreaRole:
            continue
        title = attribute(element, kAXTitleAttribute).lower()
        identifier = attribute(element, kAXIdentifierAttribute).lower()
        placeholder = attribute(element, kAXPlaceholderValueAttribute).lower()
        if any(token in f"{title} {identifier} {placeholder}" for token in ("search", "搜索")):
            return element
        candidates.append(element)
    # Some WeChat 4.x builds omit the accessible label. Its sidebar search
    # field is the left-most editable control, so use it only as a last resort.
    leftmost = [(point(item), item) for item in candidates]
    leftmost = [(pos, item) for pos, item in leftmost if pos]
    return min(leftmost, key=lambda pair: pair[0][0])[1] if leftmost else None


def find_exact_result(app: Any, name: str) -> Any | None:
    target = normalize_chat_name(name)
    for element in walk(app):
        identifier = attribute(element, kAXIdentifierAttribute)
        if identifier == "search_list":
            for child in walk(element):
                text = attribute(child, kAXValueAttribute) or attribute(child, kAXTitleAttribute)
                if text and normalize_chat_name(text) == target:
                    return child
    return None


def send_key(keycode: int, command: bool = True) -> None:
    down = CGEventCreateKeyboardEvent(None, keycode, True)
    if command:
        CGEventSetFlags(down, kCGEventFlagMaskCommand)
    up = CGEventCreateKeyboardEvent(None, keycode, False)
    if command:
        CGEventSetFlags(up, kCGEventFlagMaskCommand)
    CGEventPost(kCGHIDEventTap, down)
    CGEventPost(kCGHIDEventTap, up)


def open_chat(app: Any, name: str) -> None:
    if current_chat_name(app) == normalize_chat_name(name):
        return
    found = find_chat(app, name)
    if found:
        click(found)
        time.sleep(.35)
        return
    search = find_search(app)
    if not search:
        # Recent WeChat builds sometimes hide the sidebar input from the AX
        # tree. Cmd+F still invokes its native global search reliably.
        pasteboard = AppKit.NSPasteboard.generalPasteboard()
        pasteboard.clearContents()
        pasteboard.setString_forType_(name, AppKit.NSPasteboardTypeString)
        send_key(3)  # Command+F
        time.sleep(.2)
        send_key(0)  # Command+A
        send_key(9)  # Command+V
        time.sleep(.35)
        send_key(36, command=False)  # Return
        time.sleep(.6)
        if current_chat_name(app) == normalize_chat_name(name):
            return
        raise RuntimeError(f"微信未确认打开“{name}”。请先在微信中手动打开该群，再点击同步。")
    AXUIElementPerformAction(search, kAXRaiseAction)
    AXUIElementSetAttributeValue(search, kAXValueAttribute, "")
    pasteboard = AppKit.NSPasteboard.generalPasteboard()
    pasteboard.clearContents()
    pasteboard.setString_forType_(name, AppKit.NSPasteboardTypeString)
    send_key(0)
    send_key(9)
    time.sleep(.5)
    exact = find_chat(app, name) or find_exact_result(app, name)
    if not exact:
        raise RuntimeError(f"微信中未找到精确群名“{name}”。")
    click(exact)
    time.sleep(.5)


def find_messages(app: Any) -> Any:
    for element in walk(app):
        if attribute(element, kAXRoleAttribute) == kAXListRole and attribute(element, kAXTitleAttribute) == "Messages":
            return element
    raise RuntimeError("微信无障碍树中找不到消息列表。请检查辅助功能权限。")


def scroll_to_bottom(messages: Any) -> None:
    pos = point(messages)
    element_size = size(messages)
    if not pos or not element_size:
        return
    x, y = pos[0] + element_size[0] / 2, pos[1] + element_size[1] / 2
    for _ in range(5):
        event = CGEventCreateScrollWheelEvent(None, kCGScrollEventUnitLine, 1, -900)
        CGEventSetLocation(event, CGPoint(x, y))
        CGEventPost(kCGHIDEventTap, event)
        time.sleep(.05)


def collect_visible_messages(group: str, limit: int = 60) -> list[dict[str, str]]:
    if not accessibility_is_trusted():
        raise RuntimeError("当前终端尚未获得 macOS“辅助功能”权限。请在系统设置中授权后重试。")
    app = get_wechat()
    open_chat(app, group)
    messages = find_messages(app)
    scroll_to_bottom(messages)
    result: list[dict[str, str]] = []
    for element in ax_get(messages, kAXChildrenAttribute) or []:
        text = attribute(element, kAXValueAttribute) or attribute(element, kAXTitleAttribute)
        if text:
            result.append({"sender": "群成员", "text": text})
    return result[-limit:]
