import Cocoa
import WebKit

private let consoleURL = URL(string: "http://127.0.0.1:8765/")!

final class AppDelegate: NSObject, NSApplicationDelegate, WKNavigationDelegate {
    private var window: NSWindow!
    private var webView: WKWebView!
    private var serverProcess: Process?
    private var retryCount = 0
    private var connectButton: NSButton!
    private var statusLabel: NSTextField!
    private var spinner: NSProgressIndicator!
    private var qrImageView: NSImageView?
    private var qqLoginStarted = false
    private var qqLoginChecks = 0

    func applicationDidFinishLaunching(_ notification: Notification) {
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .default()
        webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = self
        webView.setValue(false, forKey: "drawsBackground")

        window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 1240, height: 820),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = "六六学习记忆"
        window.center()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        showLauncher()
    }

    func applicationWillTerminate(_ notification: Notification) {
        serverProcess?.terminate()
    }

    private func showLauncher() {
        let view = NSView()
        view.wantsLayer = true
        view.layer?.backgroundColor = NSColor(red: 0.96, green: 0.98, blue: 0.99, alpha: 1).cgColor

        let coverMark = NSTextField(labelWithString: "六")
        coverMark.font = .systemFont(ofSize: 42, weight: .bold)
        coverMark.textColor = .white
        coverMark.alignment = .center
        coverMark.wantsLayer = true
        coverMark.layer?.backgroundColor = NSColor(red: 0.00, green: 0.39, blue: 0.49, alpha: 1).cgColor
        coverMark.layer?.cornerRadius = 16
        coverMark.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([
            coverMark.widthAnchor.constraint(equalToConstant: 84),
            coverMark.heightAnchor.constraint(equalToConstant: 84),
        ])

        let title = NSTextField(labelWithString: "六六学习记忆")
        title.font = .systemFont(ofSize: 28, weight: .bold)
        title.textColor = NSColor(red: 0.08, green: 0.19, blue: 0.28, alpha: 1)
        title.alignment = .center

        let subtitle = NSTextField(wrappingLabelWithString: "把每日作业、老师要求、错词和成长记录，慢慢整理成自己的学习记忆。")
        subtitle.font = .systemFont(ofSize: 14)
        subtitle.textColor = NSColor(red: 0.32, green: 0.43, blue: 0.50, alpha: 1)
        subtitle.alignment = .center
        subtitle.maximumNumberOfLines = 2

        statusLabel = NSTextField(labelWithString: "服务尚未连接")
        statusLabel.font = .systemFont(ofSize: 13)
        statusLabel.textColor = NSColor(red: 0.37, green: 0.51, blue: 0.58, alpha: 1)
        statusLabel.alignment = .center

        connectButton = NSButton(title: "连接学习记忆", target: self, action: #selector(connectButtonPressed))
        connectButton.bezelStyle = .rounded
        connectButton.font = .systemFont(ofSize: 16, weight: .semibold)
        connectButton.contentTintColor = .white
        connectButton.wantsLayer = true
        connectButton.layer?.backgroundColor = NSColor(red: 0, green: 0.39, blue: 0.49, alpha: 1).cgColor
        connectButton.layer?.cornerRadius = 7
        connectButton.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([
            connectButton.widthAnchor.constraint(equalToConstant: 210),
            connectButton.heightAnchor.constraint(equalToConstant: 44),
        ])

        spinner = NSProgressIndicator()
        spinner.style = .spinning
        spinner.controlSize = .small
        spinner.isDisplayedWhenStopped = false

        let promise = NSTextField(labelWithString: "今天的小进步，也值得被记住")
        promise.font = .systemFont(ofSize: 13, weight: .medium)
        promise.textColor = NSColor(red: 0.07, green: 0.45, blue: 0.53, alpha: 1)
        promise.alignment = .center

        let stack = NSStackView(views: [coverMark, title, subtitle, promise, connectButton, spinner, statusLabel])
        stack.orientation = .vertical
        stack.alignment = .centerX
        stack.spacing = 14
        stack.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            stack.centerYAnchor.constraint(equalTo: view.centerYAnchor, constant: -24),
            stack.widthAnchor.constraint(lessThanOrEqualToConstant: 460),
        ])
        window.contentView = view
    }

    @objc private func connectButtonPressed() {
        retryCount = 0
        connectButton.isEnabled = false
        connectButton.title = "正在连接…"
        statusLabel.stringValue = "正在检查本地服务"
        spinner.startAnimation(nil)
        connectToConsole()
    }

    private func connectToConsole() {
        serviceIsReady { [weak self] ready in
            DispatchQueue.main.async {
                guard let self else { return }
                if ready {
                    // QQ is an optional message source. It must never block
                    // access to the learning workspace or the WeChat sync.
                    self.showConsole()
                    return
                }
                self.startServerIfNeeded()
                self.statusLabel.stringValue = "正在启动本地服务"
                self.retryConnection()
            }
        }
    }

    private func startServerIfNeeded() {
        guard serverProcess == nil,
              let launcher = Bundle.main.url(forResource: "run-server", withExtension: "sh") else { return }
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/bin/zsh")
        process.arguments = [launcher.path]
        process.standardOutput = FileHandle.nullDevice
        process.standardError = FileHandle.nullDevice
        do {
            try process.run()
            serverProcess = process
        } catch {
            showStartupError("无法启动本地服务：\(error.localizedDescription)")
        }
    }

    private func retryConnection() {
        retryCount += 1
        if retryCount > 30 {
            showStartupError("本地服务暂未就绪，请稍后再试。")
            return
        }
        statusLabel.stringValue = "正在连接本地服务（(retryCount)/30）"
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) { [weak self] in
            self?.connectToConsole()
        }
    }

    private func serviceIsReady(completion: @escaping (Bool) -> Void) {
        var request = URLRequest(url: consoleURL.appendingPathComponent("api/dashboard"))
        request.timeoutInterval = 0.8
        URLSession.shared.dataTask(with: request) { _, response, _ in
            completion((response as? HTTPURLResponse)?.statusCode == 200)
        }.resume()
    }

    private func checkQQBeforeOpeningConsole() {
        var request = URLRequest(url: consoleURL.appendingPathComponent("api/qq/status"))
        request.timeoutInterval = 2
        URLSession.shared.dataTask(with: request) { [weak self] data, _, _ in
            let payload = data.flatMap { try? JSONSerialization.jsonObject(with: $0) as? [String: Any] }
            let ready = payload?["ready"] as? Bool ?? false
            DispatchQueue.main.async {
                guard let self else { return }
                if ready {
                    self.showConsole()
                } else {
                    self.showQQLogin()
                }
            }
        }.resume()
    }

    private func showQQLogin() {
        let view = NSView()
        view.wantsLayer = true
        view.layer?.backgroundColor = NSColor(red: 0.96, green: 0.98, blue: 0.99, alpha: 1).cgColor

        let title = NSTextField(labelWithString: "登录 QQ 后继续")
        title.font = .systemFont(ofSize: 25, weight: .bold)
        title.textColor = NSColor(red: 0.08, green: 0.19, blue: 0.28, alpha: 1)
        title.alignment = .center

        let subtitle = NSTextField(wrappingLabelWithString: "请使用手机 QQ 扫描二维码。验证成功后会自动进入六六学习记忆。")
        subtitle.font = .systemFont(ofSize: 14)
        subtitle.textColor = NSColor(red: 0.32, green: 0.43, blue: 0.50, alpha: 1)
        subtitle.alignment = .center
        subtitle.maximumNumberOfLines = 2
        subtitle.widthAnchor.constraint(equalToConstant: 420).isActive = true

        let qr = NSImageView()
        qr.imageScaling = .scaleProportionallyUpOrDown
        qr.wantsLayer = true
        qr.layer?.backgroundColor = NSColor.white.cgColor
        qr.layer?.cornerRadius = 8
        qr.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([
            qr.widthAnchor.constraint(equalToConstant: 240),
            qr.heightAnchor.constraint(equalToConstant: 240),
        ])
        qrImageView = qr

        statusLabel = NSTextField(labelWithString: "正在准备 QQ 登录二维码…")
        statusLabel.font = .systemFont(ofSize: 13)
        statusLabel.textColor = NSColor(red: 0.37, green: 0.51, blue: 0.58, alpha: 1)
        statusLabel.alignment = .center

        let refresh = NSButton(title: "重新生成二维码", target: self, action: #selector(refreshQQLoginPressed))
        refresh.bezelStyle = .rounded

        let stack = NSStackView(views: [title, subtitle, qr, statusLabel, refresh])
        stack.orientation = .vertical
        stack.alignment = .centerX
        stack.spacing = 14
        stack.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            stack.centerYAnchor.constraint(equalTo: view.centerYAnchor),
        ])
        window.contentView = view
        if !qqLoginStarted {
            qqLoginStarted = true
            startQQLogin()
        } else {
            loadQQLoginQR(retry: 0)
            pollQQLogin()
        }
    }

    @objc private func refreshQQLoginPressed() {
        qqLoginChecks = 0
        startQQLogin()
    }

    private func startQQLogin() {
        statusLabel.stringValue = "正在生成新的 QQ 登录二维码…"
        var request = URLRequest(url: consoleURL.appendingPathComponent("api/qq/login/start"))
        request.httpMethod = "POST"
        request.timeoutInterval = 90
        URLSession.shared.dataTask(with: request) { [weak self] _, response, error in
            DispatchQueue.main.async {
                guard let self else { return }
                guard (response as? HTTPURLResponse)?.statusCode == 200, error == nil else {
                    self.statusLabel.stringValue = "二维码生成失败，请点击重新生成。"
                    return
                }
                self.statusLabel.stringValue = "请用手机 QQ 扫码，验证成功后会自动继续。"
                self.loadQQLoginQR(retry: 0)
                self.pollQQLogin()
            }
        }.resume()
    }

    private func loadQQLoginQR(retry: Int) {
        guard retry < 12 else { return }
        var components = URLComponents(url: consoleURL.appendingPathComponent("api/qq/login-qr"), resolvingAgainstBaseURL: false)!
        components.queryItems = [URLQueryItem(name: "t", value: String(Date().timeIntervalSince1970))]
        URLSession.shared.dataTask(with: components.url!) { [weak self] data, response, _ in
            DispatchQueue.main.async {
                guard let self else { return }
                if let data, (response as? HTTPURLResponse)?.statusCode == 200, let image = NSImage(data: data) {
                    self.qrImageView?.image = image
                } else {
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.7) {
                        self.loadQQLoginQR(retry: retry + 1)
                    }
                }
            }
        }.resume()
    }

    private func pollQQLogin() {
        qqLoginChecks += 1
        guard qqLoginChecks <= 120 else {
            statusLabel.stringValue = "二维码可能已过期，请点击重新生成。"
            return
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) { [weak self] in
            guard let self else { return }
            var request = URLRequest(url: consoleURL.appendingPathComponent("api/qq/status"))
            request.timeoutInterval = 2
            URLSession.shared.dataTask(with: request) { data, _, _ in
                let payload = data.flatMap { try? JSONSerialization.jsonObject(with: $0) as? [String: Any] }
                let ready = payload?["ready"] as? Bool ?? false
                DispatchQueue.main.async {
                    if ready {
                        self.showConsole()
                    } else {
                        self.pollQQLogin()
                    }
                }
            }.resume()
        }
    }

    private func showStartupError(_ message: String) {
        spinner.stopAnimation(nil)
        connectButton.isEnabled = true
        connectButton.title = "重新连接"
        statusLabel.stringValue = message
    }

    private func showConsole() {
        spinner.stopAnimation(nil)
        window.contentView = webView
        webView.load(URLRequest(url: consoleURL))
    }
}

@main
struct Hunter66Desktop {
    private static let delegate = AppDelegate()

    static func main() {
        let app = NSApplication.shared
        app.delegate = delegate
        app.setActivationPolicy(.regular)
        app.run()
    }
}
