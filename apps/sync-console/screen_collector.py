"""WeChat 4.x collector using window capture and macOS Vision OCR.

This is the fallback for WeChat builds that expose menus but not chat controls
through macOS Accessibility. It never sends messages; it only opens an exact
group search result and reads the visible message pane.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import AppKit
from Quartz import (
    CGEventCreateKeyboardEvent, CGEventCreateMouseEvent, CGEventPost,
    CGEventSetFlags, CGPreflightScreenCaptureAccess, CGRequestScreenCaptureAccess,
    CGWindowListCopyWindowInfo, CGWindowListCreateImage,
    CGPoint, CGRectNull, kCGEventFlagMaskCommand, kCGEventLeftMouseDown,
    kCGEventLeftMouseUp, kCGHIDEventTap, kCGNullWindowID,
    kCGWindowBounds, kCGWindowImageBoundsIgnoreFraming,
    kCGWindowListOptionIncludingWindow, kCGWindowListOptionOnScreenOnly,
    kCGWindowNumber, kCGWindowOwnerPID,
)
from Vision import VNImageRequestHandler, VNRecognizeTextRequest, VNRequestTextRecognitionLevelAccurate

BUNDLE = "com.tencent.xinWeChat"
PRIMARY_TEACHER = "蔡老师"
ATTACHMENT_PATTERN = re.compile(r"\.(?:pdf|m4a|docx?|xlsx?|pptx?|zip)$", re.I)


@dataclass(frozen=True)
class OcrLine:
    text: str
    x: float
    y: float
    width: float
    height: float


def normalise(value: str) -> str:
    compact = re.sub(r"\s+", "", value).replace("(", "（").replace(")", "）")
    return re.sub(r"（\d+）$", "", compact)


def screen_recording_authorized() -> bool:
    return bool(CGPreflightScreenCaptureAccess())


def request_screen_recording_access() -> bool:
    """Ask macOS to show its standard Screen Recording permission prompt."""
    if screen_recording_authorized():
        return True
    CGRequestScreenCaptureAccess()
    return False


def running_wechat() -> Any:
    apps = AppKit.NSRunningApplication.runningApplicationsWithBundleIdentifier_(BUNDLE)
    if not apps:
        raise RuntimeError("未检测到正在运行的微信。请先登录 Mac 版微信。")
    app = apps[0]
    app.activateWithOptions_(AppKit.NSApplicationActivateIgnoringOtherApps)
    return app


def screen_ocr_ready() -> bool:
    return screen_recording_authorized() and bool(
        AppKit.NSRunningApplication.runningApplicationsWithBundleIdentifier_(BUNDLE)
    )


def wechat_window(app: Any) -> tuple[int, dict[str, float]]:
    pid = int(app.processIdentifier())
    windows = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID) or []
    candidates = [item for item in windows if int(item.get(kCGWindowOwnerPID, -1)) == pid]
    if not candidates:
        raise RuntimeError("未找到微信窗口。请确保微信窗口没有被关闭。")
    window = max(candidates, key=lambda item: float((item.get(kCGWindowBounds) or {}).get("Width", 0)) * float((item.get(kCGWindowBounds) or {}).get("Height", 0)))
    bounds = window.get(kCGWindowBounds) or {}
    return int(window[kCGWindowNumber]), {
        "x": float(bounds.get("X", 0)), "y": float(bounds.get("Y", 0)),
        "width": float(bounds.get("Width", 0)), "height": float(bounds.get("Height", 0)),
    }


def capture_lines(app: Any) -> tuple[list[OcrLine], dict[str, float]]:
    if not screen_recording_authorized():
        raise RuntimeError("尚未授予“屏幕录制”权限。请先点击网页中的授权按钮。")
    window_id, bounds = wechat_window(app)
    image = CGWindowListCreateImage(
        CGRectNull, kCGWindowListOptionIncludingWindow, window_id, kCGWindowImageBoundsIgnoreFraming
    )
    if image is None:
        raise RuntimeError("无法截取微信窗口。请在系统设置中为运行服务的终端授予“屏幕录制”权限。")
    request = VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLevel_(VNRequestTextRecognitionLevelAccurate)
    request.setRecognitionLanguages_(["zh-Hans", "en-US"])
    request.setUsesLanguageCorrection_(False)
    handler = VNImageRequestHandler.alloc().initWithCGImage_options_(image, {})
    ok, error = handler.performRequests_error_([request], None)
    if not ok:
        raise RuntimeError(f"微信窗口文字识别失败：{error}")
    lines: list[OcrLine] = []
    for observation in request.results() or []:
        candidates = observation.topCandidates_(1)
        if not candidates:
            continue
        text = str(candidates[0].string()).strip()
        if not text:
            continue
        box = observation.boundingBox()
        x = bounds["x"] + box.origin.x * bounds["width"]
        y = bounds["y"] + (1 - box.origin.y - box.size.height) * bounds["height"]
        lines.append(OcrLine(text, x, y, box.size.width * bounds["width"], box.size.height * bounds["height"]))
    return lines, bounds


def send_key(keycode: int, command: bool = True) -> None:
    down = CGEventCreateKeyboardEvent(None, keycode, True)
    up = CGEventCreateKeyboardEvent(None, keycode, False)
    if command:
        CGEventSetFlags(down, kCGEventFlagMaskCommand)
        CGEventSetFlags(up, kCGEventFlagMaskCommand)
    CGEventPost(kCGHIDEventTap, down)
    CGEventPost(kCGHIDEventTap, up)


def click(x: float, y: float) -> None:
    point = CGPoint(x, y)
    CGEventPost(kCGHIDEventTap, CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, point, 0))
    CGEventPost(kCGHIDEventTap, CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, point, 0))


def open_group(app: Any, group: str) -> None:
    pasteboard = AppKit.NSPasteboard.generalPasteboard()
    pasteboard.clearContents()
    pasteboard.setString_forType_(group, AppKit.NSPasteboardTypeString)
    send_key(3)  # Command+F
    time.sleep(.2)
    send_key(0)  # Command+A
    send_key(9)  # Command+V
    time.sleep(.65)
    lines, bounds = capture_lines(app)
    matches = [line for line in lines if normalise(line.text) == normalise(group)]
    if not matches:
        raise RuntimeError(f"未能在微信窗口中识别到精确群名“{group}”。请将微信群窗口置于前台后重试。")
    # Search results live in the left sidebar. Click its exact OCR line rather
    # than accepting a possibly unrelated default search result.
    sidebar_matches = [line for line in matches if line.x < bounds["x"] + bounds["width"] * .45]
    target = sidebar_matches[0] if sidebar_matches else matches[0]
    click(target.x + target.width / 2, target.y + target.height / 2)
    time.sleep(.7)
    after, after_bounds = capture_lines(app)
    header_matches = [
        line for line in after
        if normalise(line.text) == normalise(group)
        and line.x > after_bounds["x"] + after_bounds["width"] * .24
        and line.y < after_bounds["y"] + after_bounds["height"] * .2
    ]
    if not header_matches:
        raise RuntimeError(f"微信未确认打开“{group}”。为避免误读其他会话，本次同步已停止。")


def is_interface_noise(text: str) -> bool:
    compact = normalise(text).lower()
    if compact in {"pdf", "qi", "群聊名称", "群公告", "群主未设置", "备注", "我在本群的昵称", "查找聊天内容", "查看更多", "添加"}:
        return True
    if re.fullmatch(r"(?:昨天)?\d{1,2}:\d{2}", compact) or re.fullmatch(r"星期[一二三四五六日天](?:\d{1,2}:\d{2})?", compact):
        return True
    if re.fullmatch(r"\d+(?:\.\d+)?m(?:未下载)?", compact):
        return True
    if "未下载" in compact or re.search(r"\d{7,}", compact):
        return True
    if len(compact) <= 2 and not re.search(r"\.(?:pdf|m4a|docx?|xlsx?)$", compact):
        return True
    return False


def source_date_for(label: str, fallback: str) -> str:
    """Turn WeChat's relative day labels into a stable ISO date when possible."""
    today = datetime.now().astimezone().date()
    compact = normalise(label)
    if compact.startswith("昨天"):
        return (today - timedelta(days=1)).isoformat()
    if compact.startswith("今天") or re.fullmatch(r"\d{1,2}:\d{2}", compact):
        return today.isoformat()
    return fallback


def is_time_marker(text: str) -> bool:
    compact = normalise(text)
    return bool(re.fullmatch(r"(?:今天|昨天)?\d{1,2}:\d{2}", compact) or re.fullmatch(r"星期[一二三四五六日天]", compact))


def is_teacher_marker(text: str) -> bool:
    return PRIMARY_TEACHER in normalise(text)


def collect_visible_messages(group: str, limit: int = 60) -> list[dict[str, str]]:
    app = running_wechat()
    open_group(app, group)
    lines, bounds = capture_lines(app)
    left = bounds["x"] + bounds["width"] * .25
    right = bounds["x"] + bounds["width"] * .72
    top = bounds["y"] + bounds["height"] * .12
    bottom = bounds["y"] + bounds["height"] * .86
    pane_lines = [
        line for line in sorted(lines, key=lambda item: (item.y, item.x))
        if left <= line.x < right and top <= line.y <= bottom
        and normalise(line.text) != normalise(group)
    ]
    active_date = datetime.now().astimezone().date().isoformat()
    active_date = datetime.now().astimezone().date().isoformat()
    active_message: list[OcrLine] = []
    active_message_date = active_date
    teacher_open = False
    merged: list[tuple[str, str]] = []

    def flush_message() -> None:
        nonlocal active_message
        if active_message:
            merged.append((" ".join(line.text for line in active_message), active_message_date))
        active_message = []

    for line in pane_lines:
        if is_time_marker(line.text):
            active_date = source_date_for(line.text, active_date)
            continue
        if is_teacher_marker(line.text):
            flush_message()
            active_message_date = active_date
            teacher_open = True
            continue
        if is_interface_noise(line.text):
            continue
        if teacher_open:
            active_message.append(line)
    flush_message()
    result = [{
        "sender": PRIMARY_TEACHER,
        "text": text,
        "source_time": message_date,
        "message_date": message_date,
        "message_type": "附件" if ATTACHMENT_PATTERN.search(text) else "文字",
    } for text, message_date in merged]
    return result[-limit:]
