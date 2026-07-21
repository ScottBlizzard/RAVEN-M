# 资料准备状态

更新时间：2026-07-21

本文件是资料库的入口状态页。它只描述已经在本地验证过的事实；规划中的内容不会被写成“已完成”。

## 当前完成度

| 类别 | 已准备 | 总数 | 当前结论 |
|---|---:|---:|---|
| P0 必读论文 PDF | 15 | 15 | 完整 |
| P1 核心论文 PDF | 8 | 8 | 完整 |
| P2 扩展论文 PDF | 14 | 14 | 完整 |
| 全部论文元数据 | 37 | 37 | 已登记 |
| 核心 BibTeX | 20 | 20 | 无重复 citation key |
| 第三方代码仓库 | 11 | 11 | 完整 |
| 官方网页快照 | 6 | 6 | 完整 |

机器可读的审计结果见 `checksums/audit_summary.json`。

## 已经准备好的关键材料

- 考核原始 PDF、文本抽取版、GPT Pro 主计划和原始提示词。
- AndroidWorld 官方代码、论文、任务列表网页快照。
- Qwen3-VL 官方代码、model card 与 mobile-agent cookbook 快照。
- 周晟老师个人主页与 Eagle Lab 主页快照。
- PG-Agent、HAR-GUI、ProBench、MP-GUI、LAMO 等直接对齐课题和实验室方向的论文。
- 2024—2026 年 GUI agent、移动智能体、反思、工作流记忆、结构化记忆相关核心论文。
- 11 个第三方仓库的本地浅克隆及精确 HEAD commit 锁定记录。
- 下载状态、代码来源、检索过程、BibTeX、SHA-256 校验和及完整性审计脚本。

## 缺口状态

第一阶段必须准备的核心论文、官方资料与开源仓库已经全部落地。此前未完成的 `MobileAgent` 已于 2026-07-21 成功浅克隆，锁定 commit 为 `11cea575561fb7800b5fb6b6cafa56f7a91de11f`。

当前没有需要用户手动补充克隆的仓库。

## 有意暂不执行的内容

- 不下载 Qwen3-VL 模型权重。
- 不安装 AndroidWorld、Android Emulator 或推理环境。
- 不运行 baseline 或正式计分任务。
- 不实现 RAVEN-M。

这些属于下一阶段的环境冻结、baseline 复现与方法实现，不应和“资料准备完成”混在一起。

## 推荐从这里开始

1. 读 `00_admin/requirements_trace.md`，确认每项官方要求对应的后续证据。
2. 按 `02_literature/README.md` 的 P0 顺序精读，并用统一模板记笔记。
3. 检查 `03_code/manifests/repositories.lock.csv`，后续实验始终以锁定 commit 为准。
4. 在 `04_protocols/` 冻结 AndroidWorld Hard 任务、模型配置和计分协议。
5. 协议冻结后，才在 `05_project/` 开始 baseline 与 RAVEN-M 实现。
