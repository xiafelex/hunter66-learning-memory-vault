# 第二台 Mac 使用说明

这个仓库把可编辑的应用代码、KET 词库、错词和复习进度同步到 GitHub。微信/QQ 登录、原始聊天、OCR 截图、音频缓存和桌面应用本体仍是每台 Mac 独立的本机数据。

## 第一次安装

```bash
git clone git@github.com:xiafelex/hunter66-learning-memory-vault.git
cd hunter66-learning-memory-vault/apps/sync-console
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
npm ci
native/build_desktop_app.sh
```

随后从“应用程序”打开“六六学习记忆”，点击“连接学习记忆”。如需同步微信消息，在第二台电脑上分别登录微信，并重新授予屏幕录制和辅助功能权限。

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
