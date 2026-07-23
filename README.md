# RAVEN-M Research Starter Repository

当前资料准备完成度与未闭合项见 [`RESOURCE_STATUS.md`](RESOURCE_STATUS.md)。

这是课题三“MLLM 驱动的 Mobile-use Agent 的记忆管理研究”的完整实验仓库。

资料底座、Qwen3-VL-32B 精确版本后端、AndroidWorld 本地环境、
B0/B1/B2/B3 baseline、RAVEN-M Strict/Full、协议审计、统计脚本与
消融控制均已实现。当前正在执行最终非 Hard G7 门；在
`protocol-v1` 预注册与 Git tag 生成之前，代码会机械阻止任何正式
Hard episode。

## 仓库结构

```text
RAVEN-M-Research/
├── 00_admin/                 # 考核原文、研究计划、决策记录
├── 01_sources/               # benchmark/model/作者与实验室官方来源
├── 02_literature/            # 论文 PDF、题录、BibTeX、阅读笔记、检索记录
├── 03_code/                  # 第三方代码克隆目录与 commit 锁
├── 04_protocols/             # 后续冻结的 benchmark/实验协议
├── 05_project/               # RAVEN-M、baseline、runner、schema、tests
├── reports/                  # 门禁报告与最终自动生成结果
├── runs/                     # 本地原始轨迹（不进入 Git）
├── checksums/                # 本地资料 SHA-256
└── scripts/                  # 下载、克隆、快照和校验脚本
```

## 当前资料层级

- `P0_must_read`：开始方法设计前必须全文阅读，优先覆盖 AndroidWorld、周晟老师/Eagle Lab 直接相关工作以及最接近的 2026 memory 方法。
- `P1_core`：用于补齐 baseline、规划/反思、压缩与程序性记忆的核心邻域。
- `P2_extended`：PDF 已全部在本地，但按实验问题选读，不应阻塞第一周环境与 baseline。

完整清单见：

- `02_literature/metadata/papers.csv`
- `03_code/manifests/repositories.csv`
- `01_sources/source_ledger.csv`
- `00_admin/requirements_trace.md`

## 实验顺序

1. 阅读考核原文和 master plan，但以考核原文为最高优先级。
2. 运行 `scripts/fetch_papers.ps1` 获取 P0/P1 论文。
3. 运行 `scripts/clone_repositories.ps1` 获取官方开源实现并写入 commit lock。
4. 先精读 PG-Agent、HAR-GUI、ProBench、MP-GUI、LAMO，再读 HyMEM、MAGNET、UI-Copilot、D-Artemis。
5. G3/G4/G6/G7 全部通过后冻结 protocol-v1。
6. 按物化的 364-episode blocked schedule 依次执行 breadth、S0、
   confirmatory 和 ablation/control。
7. 只使用冻结的分析脚本生成统计、表格和图。

完整复现命令与门禁见
[`reports/reproduction_guide.md`](reports/reproduction_guide.md)。

## 资料纪律

- 论文 venue/status 只以 proceedings、出版社、OpenReview 或作者官方页面为依据。
- GitHub 仓库必须由论文、作者主页或正式项目页反向确认，名称相同不等于官方实现。
- 每次下载和克隆都记录 URL、访问日期、commit 或 SHA-256。
- 模型权重不在本阶段下载，也不进入 Git。
- `third_party` 与论文 PDF 在本地保留，但父仓库只追踪清单、锁文件与校验和，避免 Git 历史膨胀。
