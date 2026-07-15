# 六六班级同步台

本地网页控制台。点击“同步六六班级”后，采集器通过窗口截图和 macOS Vision OCR 打开目标群、读取最新可见消息、去重，并写入学习记忆仓库。

## 首次使用

```bash
cd apps/sync-console
python3 setup_local_collector.py
.venv/bin/python server.py
```

另开一个终端启动网页开发服务器：

```bash
npm install
npm run dev
```

打开 Vite 提示的地址。生产模式先执行 `npm run build`，然后只需运行 `.venv/bin/python server.py` 并访问 `http://127.0.0.1:8765`。

## 权限

为运行 `server.py` 的终端授予 macOS 的“辅助功能”和“屏幕录制”权限。采集器不发送消息，不读取其他群；它只定位精确名称为“六六班级”的会话。

## 微信 4.1 初始化

当前 Mac 微信 4.1 在这台机器上没有向 Accessibility API 公开聊天控件，因此一键同步会优先使用“微信窗口截图 + macOS Vision 中文 OCR”。首次只需：

1. 在 macOS 的“系统设置 -> 隐私与安全性 -> 屏幕录制”中，开启启动服务的 Codex 或终端。
2. 保持 Mac 微信登录状态。
3. 打开网页后点击“同步六六班级”。

这个路径不需要 SIP，也不依赖数据库密钥。数据库初始化仅作为一次性历史导入的可选方案，详见 [数据库初始化说明](../../docs/wechat-bootstrap.md)。

## 自动更新

在网页中打开自动检查开关后，会创建当前用户的 `launchd` 任务，每天 18:30 运行一次同步。自动化日志和去重状态仅保存在 `private/sync-console/`，该目录默认不提交到 Git。

## 桌面应用

已构建本机应用：`~/Applications/六六学习记忆.app`。日常只需双击打开，点击“连接学习记忆”后才启动本地服务；关闭 App 会一并关闭这次服务。应用本身只显示本地同步台，不会以 App 身份读取微信数据。

修改前端或服务端后，可重新执行：

```bash
cd apps/sync-console
native/build_desktop_app.sh
```
