import Cocoa
import ApplicationServices
import Carbon.HIToolbox
import CoreGraphics
import Vision

struct OcrLine: Codable {
    let text: String
    let x: CGFloat
    let y: CGFloat
    let width: CGFloat
    let height: CGFloat
}

struct CapturedMessage: Codable {
    let sender: String
    let text: String
    let source_time: String
}

func normalized(_ value: String) -> String {
    let compact = value.replacingOccurrences(of: " ", with: "")
        .replacingOccurrences(of: "\n", with: "")
        .replacingOccurrences(of: "(", with: "（")
        .replacingOccurrences(of: ")", with: "）")
    return compact.replacingOccurrences(of: "（[0-9]+）$", with: "", options: .regularExpression)
}

func isNoise(_ text: String) -> Bool {
    let value = normalized(text).lowercased()
    if ["pdf", "qi", "群聊名称", "群公告", "群主未设置", "备注", "我在本群的昵称", "查找聊天内容", "查看更多", "添加"].contains(value) { return true }
    if value.range(of: "^(昨天)?[0-9]{1,2}:[0-9]{2}$", options: .regularExpression) != nil { return true }
    if value.range(of: "^星期[一二三四五六日天]([0-9]{1,2}:[0-9]{2})?$", options: .regularExpression) != nil { return true }
    if value.range(of: "^[0-9]+(\\.[0-9]+)?m(未下载)?$", options: .regularExpression) != nil { return true }
    if value.contains("未下载") || value.range(of: "[0-9]{7,}", options: .regularExpression) != nil { return true }
    if value.count <= 2 && value.range(of: "\\.(pdf|m4a|docx?|xlsx?)$", options: .regularExpression) == nil { return true }
    return false
}

func wechatApplication() throws -> NSRunningApplication {
    guard let application = NSWorkspace.shared.runningApplications.first(where: { $0.bundleIdentifier == "com.tencent.xinWeChat" }) else {
        throw NSError(domain: "Hunter66", code: 1, userInfo: [NSLocalizedDescriptionKey: "未检测到正在运行的微信。"])
    }
    application.activate(options: [.activateIgnoringOtherApps])
    return application
}

func window(for application: NSRunningApplication) throws -> (CGWindowID, CGRect) {
    let all = CGWindowListCopyWindowInfo(.optionOnScreenOnly, kCGNullWindowID) as? [[String: Any]] ?? []
    let matches = all.filter { ($0[kCGWindowOwnerPID as String] as? Int32) == application.processIdentifier }
    guard let chosen = matches.max(by: {
        let lhs = ($0[kCGWindowBounds as String] as? NSDictionary).flatMap { CGRect(dictionaryRepresentation: $0) } ?? .zero
        let rhs = ($1[kCGWindowBounds as String] as? NSDictionary).flatMap { CGRect(dictionaryRepresentation: $0) } ?? .zero
        return lhs.width * lhs.height < rhs.width * rhs.height
    }), let number = chosen[kCGWindowNumber as String] as? NSNumber,
        let dict = chosen[kCGWindowBounds as String] as? NSDictionary,
        let bounds = CGRect(dictionaryRepresentation: dict) else {
        throw NSError(domain: "Hunter66", code: 2, userInfo: [NSLocalizedDescriptionKey: "未找到微信窗口。"])
    }
    return (CGWindowID(number.uint32Value), bounds)
}

func captureLines(application: NSRunningApplication) throws -> ([OcrLine], CGRect) {
    let (windowID, bounds) = try window(for: application)
    guard let image = CGWindowListCreateImage(.null, .optionIncludingWindow, windowID, .boundsIgnoreFraming) else {
        throw NSError(domain: "Hunter66", code: 3, userInfo: [NSLocalizedDescriptionKey: "无法截取微信窗口。"])
    }
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.recognitionLanguages = ["zh-Hans", "en-US"]
    request.usesLanguageCorrection = false
    let handler = VNImageRequestHandler(cgImage: image, options: [:])
    try handler.perform([request])
    return ((request.results ?? []).compactMap { observation in
        guard let candidate = observation.topCandidates(1).first else { return nil }
        let box = observation.boundingBox
        return OcrLine(
            text: candidate.string.trimmingCharacters(in: .whitespacesAndNewlines),
            x: bounds.minX + box.minX * bounds.width,
            y: bounds.minY + (1 - box.maxY) * bounds.height,
            width: box.width * bounds.width,
            height: box.height * bounds.height
        )
    }, bounds)
}

func sendKey(_ key: CGKeyCode, command: Bool = true) {
    let source = CGEventSource(stateID: .hidSystemState)
    let down = CGEvent(keyboardEventSource: source, virtualKey: key, keyDown: true)
    let up = CGEvent(keyboardEventSource: source, virtualKey: key, keyDown: false)
    if command {
        down?.flags = .maskCommand
        up?.flags = .maskCommand
    }
    down?.post(tap: .cghidEventTap)
    up?.post(tap: .cghidEventTap)
}

func click(_ x: CGFloat, _ y: CGFloat) {
    let point = CGPoint(x: x, y: y)
    let source = CGEventSource(stateID: .hidSystemState)
    CGEvent(mouseEventSource: source, mouseType: .leftMouseDown, mouseCursorPosition: point, mouseButton: .left)?.post(tap: .cghidEventTap)
    CGEvent(mouseEventSource: source, mouseType: .leftMouseUp, mouseCursorPosition: point, mouseButton: .left)?.post(tap: .cghidEventTap)
}

func openGroup(_ group: String, application: NSRunningApplication) throws {
    let pasteboard = NSPasteboard.general
    pasteboard.clearContents()
    pasteboard.setString(group, forType: .string)
    sendKey(CGKeyCode(kVK_ANSI_F))
    Thread.sleep(forTimeInterval: 0.2)
    sendKey(CGKeyCode(kVK_ANSI_A))
    sendKey(CGKeyCode(kVK_ANSI_V))
    Thread.sleep(forTimeInterval: 0.7)
    let (before, bounds) = try captureLines(application: application)
    let matches = before.filter { normalized($0.text) == normalized(group) && $0.x < bounds.minX + bounds.width * 0.45 }
    guard let target = matches.first else {
        throw NSError(domain: "Hunter66", code: 4, userInfo: [NSLocalizedDescriptionKey: "未能在微信中识别到目标群。"])
    }
    click(target.x + target.width / 2, target.y + target.height / 2)
    Thread.sleep(forTimeInterval: 0.8)
    let (after, afterBounds) = try captureLines(application: application)
    let opened = after.contains {
        normalized($0.text) == normalized(group)
        && $0.x > afterBounds.minX + afterBounds.width * 0.24
        && $0.y < afterBounds.minY + afterBounds.height * 0.2
    }
    if !opened {
        throw NSError(domain: "Hunter66", code: 5, userInfo: [NSLocalizedDescriptionKey: "未确认打开目标群，已停止同步。"])
    }
}

func captureMessages(group: String) throws -> [CapturedMessage] {
    let application = try wechatApplication()
    try openGroup(group, application: application)
    let (lines, bounds) = try captureLines(application: application)
    let left = bounds.minX + bounds.width * 0.25
    let right = bounds.minX + bounds.width * 0.735
    let top = bounds.minY + bounds.height * 0.12
    let bottom = bounds.minY + bounds.height * 0.86
    let candidates = lines.filter {
        $0.x >= left && $0.x < right && $0.y >= top && $0.y <= bottom
        && normalized($0.text) != normalized(group) && !isNoise($0.text)
    }.sorted { $0.y == $1.y ? $0.x < $1.x : $0.y < $1.y }
    var merged: [OcrLine] = []
    for line in candidates {
        let hasFileExtension = line.text.range(of: "\\.(pdf|m4a|docx?|xlsx?)$", options: .regularExpression) != nil
        if hasFileExtension, let previous = merged.last, line.y - previous.y < 34 {
            merged[merged.count - 1] = OcrLine(text: "\(previous.text) \(line.text)", x: previous.x, y: previous.y, width: line.width, height: line.height)
        } else {
            merged.append(line)
        }
    }
    return merged.map { CapturedMessage(sender: "群成员", text: $0.text, source_time: "") }
}

func argument(_ name: String) -> String? {
    guard let index = CommandLine.arguments.firstIndex(of: name), index + 1 < CommandLine.arguments.count else { return nil }
    return CommandLine.arguments[index + 1]
}

func accessibilityAccessGranted() -> Bool {
    let options = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true] as CFDictionary
    return AXIsProcessTrustedWithOptions(options)
}

let group = argument("--group")
let output = argument("--output")
if !CGPreflightScreenCaptureAccess() {
    CGRequestScreenCaptureAccess()
    fputs("请在系统设置中允许 Hunter66 Sync Agent 的屏幕录制权限。\n", stderr)
    exit(2)
}
guard let group, let output else { exit(0) }
if !accessibilityAccessGranted() {
    fputs("请在系统设置中允许 Hunter66 Sync Agent 的辅助功能权限。\n", stderr)
    exit(3)
}
do {
    let messages = try captureMessages(group: group)
    let data = try JSONEncoder().encode(messages)
    try data.write(to: URL(fileURLWithPath: output), options: .atomic)
    print("captured \(messages.count) messages")
} catch {
    fputs("\(error.localizedDescription)\n", stderr)
    exit(1)
}
