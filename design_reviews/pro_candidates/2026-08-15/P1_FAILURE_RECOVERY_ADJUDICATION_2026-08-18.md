# P1 failure recovery：TCRA-R2 收敛与 G0 裁决（2026-08-18）

## 裁决

`PREFLIGHT_INVALID_NO_LIVE`。本方向不产生七题 live，也不能被记作 `0/7`。

原始 Pro 文档提出唯一机制 TCRA-R2：冻结 R2 先生成基础提案 A；只有可见轨迹形成两份重复失败支持、当前回到 anchor、A 又准备进入相同失败路线时，才用同一 Qwen 额外生成一个候选 B；确定性 arbiter 只检查协议合法性和路线偏离，通过后执行 B。每个 episode 最多一次辅助调用。

在当前仓库事实边界 `152f3b92f6ad1d87f20fa0e6a54101a0d2c07711` 上，完整读取该设计后，按文档冻结的 E1/E2、12-action window、route RLE 2–6、A1-R9 0.05 action family、至少 6 个剩余 native actions 进行了 19 条正式 R2 episode 的零生成重放。审计使用 raw PNG、实际 canonical action 和正式 result 中的 episode/hash 绑定，不调用模型。

结果：

- 19/19 正式 R2 episode 完成哈希核验；
- `generation_calls=0`；
- 两种独立枚举路径逐事件一致；
- 失败任务覆盖 6 题、4 个任务族；
- 但 R2 成功题 `SimpleCalendarAddOneEvent` 在 step 13、14 出现两个 call-gated `E2_CLOSED_ROUTE_REPEAT`；
- 因此违反原设计 §2.9 的硬门：六个 R2 成功 episode 中 call-gated ERE 必须为 0。

冻结事件分别为：

1. step 13，blocked route `tap:0.90:0.50 → tap:0.75:0.75`，剩余 21 个 native actions；
2. step 14，blocked route `tap:0.75:0.75 → tap:0.90:0.50`，剩余 20 个 native actions。

这不是代码崩溃或证据缺失，而是设计假设被自己的历史硬负控否定。若在看到成功标签后增加重复次数、改 route 长度、加入 Calendar 例外或调整动作区域，就会违反原文“detector 配置冻结后不得根据 label 调参”的规定，并形成 task-aware 事后修补。故不做这种最小名义、实质行为性的热修。

## 与现有失败机制的关系

TCRA 的研究问题是合理的：R9/SYS-TRRC 已显示“检测或提示”不自动变成不同且有效的执行动作。它新增 A/B 仲裁能缩短因果链。但本次 G0 证明冻结 trigger 不能同时满足“跨失败任务有覆盖”和“R2 六成功零误触发”。因此不能在当前身份下进入 live，更不能因为用户要求所有**科学有效**候选跑七题而把一个 G0 无效设计强行送入模型。

## 证据

- machine-readable audit：`evidence/p1_failure_recovery/P1_TCRA_R2_ZERO_GENERATION_AUDIT.json`
- canonical content SHA-256：`6023923ffa8deed63e61a1a4117019f9591ba36f20beb939eb6beed43ff86240`
- raw file manifest：该 JSON 内含 19 个 episode、events、before/after PNG 的相对路径、大小与 SHA-256；
- hash chain：同文件内 `M0`–`M4`；
- 实现/复算脚本：`implementation/scripts/audit_p1_tcra_r2.py`。

## 不允许的结论

- 不能说 TCRA live 为 `0/7`，因为没有合法 live；
- 不能说 failure recovery 整个问题族被否定；
- 不能把失败题 6/4-family 覆盖当作收益而忽略成功题误触发；
- 不能在 P2/P3 中按具体任务或这两个 Calendar step 写规则。

下一步按预注册顺序进入 P2 long-horizon coordination，P1 的具体 live task 内容不作为 P2 逐题调参依据。
