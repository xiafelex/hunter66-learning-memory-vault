# 微信 4.1 数据库初始化

同步台已经实现了群消息去重、归档和自动更新。当前 Mac 微信 4.1 没有向无障碍接口公开聊天控件，日常同步改用“窗口截图 + macOS Vision 中文 OCR”，不需要数据库解密或 SIP 修改。

## 日常自动同步

在 macOS 的“系统设置 -> 隐私与安全性 -> 屏幕录制”中，开启启动同步服务的 Codex 或终端。之后保持微信登录，网页同步按钮会精确搜索“六六班级”、打开目标会话并识别可见消息。自动检查任务会运行相同的本地流程。

## 可选：一次性历史导入

1. 在手机微信中打开“设置 -> 通用 -> 聊天记录迁移与备份 -> 迁移到电脑”，选择“六六班级”并完成迁移。
2. 按 [BIBOYANG425/wechat-chat-history-mac](https://github.com/BIBOYANG425/wechat-chat-history-mac) 的 Apple Silicon / WeChat 4.1 流程提取一次数据库密钥。
3. 该流程目前要求在恢复模式中临时关闭 SIP，随后运行 lldb 密钥扫描脚本；这是系统安全设置，必须由设备所有者亲自操作。完成密钥提取后可立即重新开启 SIP。
4. 使用该项目提供的解密脚本生成聊天数据库，并将 `decrypted/` 保留在：

```text
~/Library/Application Support/Hunter66/wechat-export-local/decrypted/
```

至少需要存在：

```text
decrypted/contact/contact.db
decrypted/message/message_*.db
```

## 完成后的效果与限制

同步台会自动识别这个目录。点击“同步六六班级”会从多个消息分片读取群聊、跳过已处理消息，并写入：

```text
data/raw-inputs/wechat/
data/teacher-requirements/
```

网页中的自动检查开关会建立当前用户的 `launchd` 任务，每天 18:30 执行同一套同步流程。

已解密的数据库可用于查询已有历史；但微信 4.1 的运行时密钥可能在微信重启、升级或新增数据库分片后失效。部分社区项目要求在这些场景重新提取密钥。因此，SIP 临时关闭适合作为一次性历史导入方案，不适合作为长期自动抓取新消息的常规方案。

## 不要提交的内容

解密后的数据库、导出 JSON、密钥和自动化日志都只能保留在本机；仓库的 `.gitignore` 已排除 `private/`，不要把这些文件加入 Git。
