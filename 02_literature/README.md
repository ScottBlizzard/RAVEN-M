# Literature Library

## 阅读顺序

### P0：方法冻结前必须全文读完

1. AndroidWorld：环境、task generator、evaluator、reset 与实验单位。
2. PG-Agent：Page Graph、RAG、multi-agent decomposition；明确不能重复的贡献。
3. HAR-GUI：history-aware reasoning、action summarization、training-based memory。
4. ProBench：过程信息、错误分析和仅看 final state 的局限。
5. MP-GUI：GUI perception 与 memory 的因果边界。
6. LAMO：multi-role orchestration 已经解决了什么。
7. HyMEM、MAGNET、UI-Copilot、D-Artemis、ReMe：2026 最近邻方法。
8. 周晟老师/Eagle Lab 的 ChartAccessMobile、Dual-branch RAG、Web Accessibility Copilot：理解其可审计、人机协同、GUI/accessibility 研究偏好。
9. Mobile-Agent-v2：经典 Planner/Decision/Reflection/Memory 系统参照。

### P1：baseline 和方法设计期阅读

SeeClick、Mobile-Agent-v3.5、MobileUse、GUI-Critic-R1、Agent S、Agent S2、Agent Workflow Memory、CoMEM。

### P2：按实验问题查阅

14 篇 PDF 已全部在本地，主要用于历史压缩、RL 对照、自演化、效率、工具调用和基础性 AppAgent；它们按问题选读，不阻塞环境部署与 B0/B3。

## 每篇论文必须回答的问题

使用 `notes/PAPER_READING_TEMPLATE.md`，至少记录：

- 论文身份和代码是否真的核验；
- memory 表示、写入、更新、检索与失效；
- 是否训练、使用什么模型和 benchmark；
- 最强实验是否真正隔离 memory 机制；
- 哪部分可以复用；
- 与 RAVEN-M 的重叠风险；
- 阅读后必须删掉、修改或补充的设计。

## 本地 PDF 规则

PDF 文件不进入父 Git 历史；`metadata/papers.csv` 保存 URL、优先级和本地文件名，`checksums/papers.sha256.csv` 保存完整性信息。
