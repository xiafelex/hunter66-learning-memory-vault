# 多电脑使用说明

这个仓库把可编辑的应用代码、KET 词库、错词和复习进度同步到 GitHub。微信/QQ 登录、原始聊天、OCR 截图、音频缓存和桌面应用本体仍是每台 Mac 独立的本机数据。

## 第二台 Mac：完整同步与抓群消息

```bash
git clone git@github.com:xiafelex/hunter66-learning-memory-vault.git
cd hunter66-learning-memory-vault/apps/sync-console
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
npm ci
native/build_desktop_app.sh
```

随后从“应用程序”打开“六六学习记忆”，点击“连接学习记忆”。如需同步微信消息，在第二台电脑上分别登录微信，并重新授予屏幕录制和辅助功能权限。

## Windows：学习与编辑工作站

Windows 可以同步和编辑代码、词库、错词与复习进度，也可以在浏览器中使用单词测试、听写和复习功能；不能运行 macOS 的微信屏幕 OCR、辅助功能采集或“六六学习记忆.app”。群消息同步仍在 Mac 上进行。

在 Windows PowerShell 中首次执行：

```powershell
git clone https://github.com/xiafelex/hunter66-learning-memory-vault.git
cd hunter66-learning-memory-vault\apps\sync-console
py -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
npm ci
npm run build
.\.venv\Scripts\python server.py
```

随后在 Windows 浏览器打开 `http://127.0.0.1:8765`。关闭 PowerShell 就会停止本地网页服务；需要使用时重新运行最后一行即可。

## 每次开始编辑前

在仓库根目录执行：

```bash
git pull --rebase
```

这会把另一台电脑最新提交的代码、错词和复习进度先取回来，再开始修改。

## 每次完成修改后

```bash
git status
git add apps data/learning-state data/reference README.md docs .gitignore
git commit -m "更新六六学习记忆"
git push origin main
```

如果 `git pull --rebase` 提示冲突，先不要推送；保留冲突文件，处理后再继续。日常双电脑使用时，尽量不要同时编辑同一条错词或同一个文件。

## 不会同步到 GitHub 的内容

- 微信和 QQ 的原始聊天记录、截图、附件与 OCR 中间结果。
- 登录二维码、会话状态、服务日志和音频缓存。
- `~/Applications/六六学习记忆.app`，第二台 Mac 需要按首次安装步骤自行构建。

手工整理的老师要求、知识点、错题和阶段报告仍可正常提交；自动从群聊生成的老师消息文件会留在本机，避免把大量群聊记录带入远端历史。
