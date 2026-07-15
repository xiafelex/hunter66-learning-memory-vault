# Hunter 六六学习记忆仓库

这个仓库用于长期保存 Hunter 六六学习过程中的重要记忆：知识点、学校老师要求、薄弱点、错题、复习计划、阶段复盘和原始材料摘要。

六六出生于 2017 年，目前小学二年级。仓库设计原则是：记录要短、证据要清楚、复习要能执行、后续 AI 要能读懂。

## 这个仓库保存什么

- 老师要求：作业格式、背诵范围、考试提醒、订正规则、课堂习惯要求。
- 知识点：语文、数学、英语等学科中需要掌握的概念、方法、易错点。
- 错题：题目来源、原题或摘要、错误答案、正确思路、错因、订正结果。
- 薄弱点：持续出现的问题，例如计算粗心、审题漏条件、拼音声调、英语单词拼写。
- 复习计划：按掌握度和日期安排的复习任务。
- 阶段报告：周复盘、月复盘、考试后分析。
- 原始输入：作业照片、老师通知、试卷、聊天记录摘要等材料的索引。

## 目录结构

```text
.
├── MEMORY.md                         # 给 AI 读取的长期记忆入口
├── memory_summary.md                 # 高频事实和近期重点摘要
├── docs/                             # 维护规范和使用说明
├── templates/                        # 录入模板
├── data/
│   ├── raw-inputs/                   # 原始材料摘要和来源索引
│   ├── teacher-requirements/         # 老师要求
│   ├── knowledge-points/             # 知识点卡片
│   ├── wrong-questions/              # 错题卡片
│   ├── weaknesses/                   # 薄弱点追踪
│   ├── review-plans/                 # 复习计划
│   └── reports/                      # 周/月/考试报告
│   ├── learning-state/               # 可同步的错词与复习进度
│   └── reference/                    # 可复现的公开词库索引
├── apps/sync-console/                # 六六学习记忆桌面应用
└── scripts/                          # 本地辅助脚本
```

## 日常使用

1. 收到老师通知或作业要求时，复制 `templates/teacher-requirement.md` 到 `data/teacher-requirements/`。
2. 发现错题时，复制 `templates/wrong-question.md` 到 `data/wrong-questions/对应学科/`。
3. 某类错误重复出现 2 次以上时，复制 `templates/weakness.md` 到 `data/weaknesses/`。
4. 每周运行一次复盘脚本：

```bash
python3 scripts/build_weekly_review.py
```

5. 重要结论沉淀到 `memory_summary.md`，细节继续留在各条记录里。

## 命名规则

文件名建议使用：

```text
YYYY-MM-DD-科目-简短主题.md
```

例如：

```text
2026-07-10-math-two-digit-addition-carry.md
2026-07-10-chinese-pinyin-tone.md
2026-07-10-teacher-homework-format.md
```

## 维护原则

- 不追求记录所有题，只记录能帮助下一次少错的内容。
- 错题不只记答案，更要记错因和下次提醒。
- 老师要求要保留来源和日期，避免口头要求混淆。
- 每条薄弱点都要有“下一步怎么练”，不要只贴标签。
- 涉及孩子隐私的照片、班级群截图、老师姓名等，默认不上传公开仓库。

## 多电脑同步

应用代码、KET 词库、错词和复习进度会提交到 GitHub；微信/QQ 原始聊天、二维码、语音缓存和本机登录状态只保留在当前电脑。另一台 Mac 的安装、同步和日常编辑步骤见 [多电脑使用说明](docs/second-mac-setup.md)。
