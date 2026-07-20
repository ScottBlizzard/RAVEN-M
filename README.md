# RAVEN-M Research Starter Repository

当前资料准备完成度与未闭合项见 [`RESOURCE_STATUS.md`](RESOURCE_STATUS.md)。

这是课题三“MLLM 驱动的 Mobile-use Agent 的记忆管理研究”的本地研究启动仓库。

当前阶段只解决一件事：把考核规定、研究计划、官方技术资料、必读论文和开源实现整理成可追溯的资料底座。这里暂不实现 RAVEN-M，也不开始 AndroidWorld 正式计分实验。

## 仓库结构

```text
RAVEN-M-Research/
├── 00_admin/                 # 考核原文、研究计划、决策记录
├── 01_sources/               # benchmark/model/作者与实验室官方来源
├── 02_literature/            # 论文 PDF、题录、BibTeX、阅读笔记、检索记录
├── 03_code/                  # 第三方代码克隆目录与 commit 锁
├── 04_protocols/             # 后续冻结的 benchmark/实验协议
├── 05_project/               # 后续自己的 RAVEN-M 实现
├── checksums/                # 本地资料 SHA-256
└── scripts/                  # 下载、克隆、快照和校验脚本
```

## 当前资料层级

- `P0_must_read`：开始方法设计前必须全文阅读，优先覆盖 AndroidWorld、周晟老师/Eagle Lab 直接相关工作以及最接近的 2026 memory 方法。
- `P1_core`：用于补齐 baseline、规划/反思、压缩与程序性记忆的核心邻域。
- `P2_extended`：已登记但按需阅读，不应阻塞第一周环境与 baseline。

完整清单见：

- `02_literature/metadata/papers.csv`
- `03_code/manifests/repositories.csv`
- `01_sources/source_ledger.csv`
- `00_admin/requirements_trace.md`

## 第一阶段使用顺序

1. 阅读考核原文和 master plan，但以考核原文为最高优先级。
2. 运行 `scripts/fetch_papers.ps1` 获取 P0/P1 论文。
3. 运行 `scripts/clone_repositories.ps1` 获取官方开源实现并写入 commit lock。
4. 先精读 PG-Agent、HAR-GUI、ProBench、MP-GUI、LAMO，再读 HyMEM、MAGNET、UI-Copilot、D-Artemis。
5. 只有在 AndroidWorld、Qwen3-VL 和方法重叠核验完成后，才在 `05_project/` 中开始实现。

## 资料纪律

- 论文 venue/status 只以 proceedings、出版社、OpenReview 或作者官方页面为依据。
- GitHub 仓库必须由论文、作者主页或正式项目页反向确认，名称相同不等于官方实现。
- 每次下载和克隆都记录 URL、访问日期、commit 或 SHA-256。
- 模型权重不在本阶段下载，也不进入 Git。
- `third_party` 与论文 PDF 在本地保留，但父仓库只追踪清单、锁文件与校验和，避免 Git 历史膨胀。
