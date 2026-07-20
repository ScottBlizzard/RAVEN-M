# Protocols

这里用于保存后续实验中必须提前冻结、且不能根据结果随意改动的协议。

计划至少包含：

- `environment_lock.md`：AndroidWorld、Android Emulator、ADB、Python、CUDA、模型服务版本。
- `task_manifest.csv`：正式使用的 AndroidWorld Hard 任务及排除理由。
- `model_config.yaml`：Qwen3-VL-32B-Instruct 的推理与采样配置。
- `baseline_protocol.md`：公平 token budget、最大步数、重试、超时和失败定义。
- `scoring_protocol.md`：TSR、平均步数、token、延迟、恢复率及 bootstrap 置信区间。
- `run_naming.md`：随机种子、run ID、日志与截图命名规则。

在 baseline 首次正式计分前，应将这些文件纳入 Git 并冻结版本。

