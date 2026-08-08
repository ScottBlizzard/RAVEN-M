# SSH 隧道在模型返回后的卡死修正（2026-08-08）

## 观察事实

在 `RetroSavePlaylist/20260808` 已通过媒体初始化并运行到第 20 次模型调用时：

- 远端 vLLM 日志显示对应 `/v1/chat/completions` 已返回 HTTP 200；
- 远端 engine 随后为 `Running: 0`，GPU 利用率回到 0%；
- 本地 episode 停留在 `step_020_before`，没有写入模型返回或执行动作；
- 通过同一 SSH 端口转发访问 `/v1/models` 也超时；
- 远端模型 PID、权重显存与直接 SSH 登录均正常。

因此失败边界位于“远端响应已经完成—本地 HTTP 客户端收到响应”之间，是 SSH 隧道卡死，不是模型推理、Android 动作或 evaluator 失败。该 episode 的前 20 步保留用于审计，但整条不能进入最终科学有效集合。

## 冻结修正

不重启、不更换模型，也不改变任何生成参数。只增强传输层失效检测与恢复：

1. SSH tunnel 增加 `ServerAliveInterval=15`、`ServerAliveCountMax=2` 与 `TCPKeepAlive=yes`；
2. 启动已有的本地模型健康 watchdog；若 `/v1/models` 失败，停止失效的 SSH listener 并重建同端口转发；
3. 最终 replacement 的单次 HTTP deadline 从历史默认 3600 秒显式设为 120 秒，并写入 episode metadata；
4. 超时只会重试尚未产生 Android 动作的模型生成请求，沿用同一 idempotency key；不会重复点击、输入或 evaluator；
5. 若重建后仍无法恢复，则继续标基础设施无效，不强行计分。

`run_official_qwen_mobile.py` 的默认 deadline 仍为 3600 秒，旧 baseline 条件不被事后改写；120 秒仅用于本次明确标为 replacement 的最终键。VLLM client 测试通过，PowerShell launcher 语法检查通过。
