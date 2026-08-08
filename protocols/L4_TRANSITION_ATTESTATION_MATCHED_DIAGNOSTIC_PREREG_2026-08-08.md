# L4 Transition Attestation：matched diagnostic 预注册

冻结时间：2026-08-08 16:40（Asia/Hong_Kong）  
状态：在任何本诊断生成调用之前冻结  
性质：同实例配对因果诊断；不是 pristine held-out，不宣称域外泛化

## 1. 基线证据与单一假设

最终官方 Qwen3-VL-32B Hard 基线包含 57 个唯一有效键，成功 7/57。自动审计中有 39 条重复状态轨迹、14 条连续停滞轨迹、21 条模型自称成功而 evaluator 不同意的轨迹。

本轮只检验一个窄假设：官方历史直接保存模型自写的 `Action:` 摘要，会把“想做什么”错误升级成“已经做成什么”；当动作后页面没有可观察变化时，这种历史会促成同状态重复和错误进度累积。若把该步历史替换为经过后状态证明的执行事实，模型可能更早换策略。

跨任务资格证据：

- `ExpenseDeleteMultiple2/20260808`：基线 reward 0，34 次调用，误入详情页后最长连续停滞 27 步；
- `OsmAndTrack/20260808`：基线 reward 0，120 次调用，轨迹编辑器仍显示 `points: 0` 后最长连续停滞 72 步。

## 2. 唯一干预

保持原官方系统提示、当前截图单图输入和工具 schema 不变。只增加可选的历史策略 `transition_attested_action_summaries_v1`：

1. 若动作已由 Android 正常执行，且动作前后 activity 相同、UI 树哈希相同、`changed_pixel_fraction_gt_5 < 0.001`，不把模型原始语义摘要写入下一步历史；
2. 改写为确定性事实：执行了哪个规范化动作，但没有观察到页面或 UI 转移，原摘要声称的语义效果未被验证；不得在同一状态下重复同一动作；
3. 其他步骤继续使用模型原始 `Action:` 摘要，不增加任务答案、隐藏 UI 内容或 evaluator 信息；
4. 日志同时保存 `model_action_summary`、`committed_history_summary` 与触发原因，保证干预可审计。

本轮不实现目标身份匹配、Destination-First Binding、结构化工作记忆、额外 critic 或完成检查；避免一次改变多个机制。

## 3. 冻结任务与顺序

任务 manifest：`androidworld_hard_v2_l4_transition_attestation_matched_diagnostic.final.json`

1. Pilot：`ExpenseDeleteMultiple2/20260808`，原生预算 34；
2. Frozen confirmation：`OsmAndTrack/20260808`，原生预算 120。

两条都已在基线中观察，因此 confirmation 只表示代码在 pilot 后保持冻结并跨任务运行，不表示未污染 held-out。Pilot 结束后不得修改历史文案、阈值、提示词或控制器再把第二条称为 frozen confirmation；若必须修改，则停止本预注册并另立版本。

## 4. 模型、采样与匹配

- 模型：`Qwen/Qwen3-VL-32B-Instruct`
- model revision：`0cfaf48183f594c314753d30a4c4974bc75f3ccb`
- runtime：stock vLLM，BF16，单张 RTX PRO 6000 96GB
- generation seed：3407
- temperature：0.7
- top_p：0.8
- top_k：20
- presence_penalty：1.5
- repetition_penalty：1.0
- max_tokens：32768
- 请求超时：120 秒；只允许传输级、同 idempotency key 的响应恢复，不重复 Android 动作
- 动作预算：与各自基线的原生 34/120 完全一致
- 图像：仅当前截图；不提供历史截图、UI 树或 evaluator
- 调用/动作/耗时：分别报告，不用额外预算换取未披露优势

## 5. 预先冻结的结果判定

每条报告 evaluator reward、模型调用数、Android 动作数、总耗时、最长连续停滞、停滞动作总数、虚假成功和终止原因。

机制级正向信号必须同时满足：

1. 最长连续停滞相对同实例基线至少下降 50%；
2. 不以 reward 仍为 0 的更早虚假成功来换取较短轨迹；
3. 没有新增协议错误、执行失败或基础设施错误。

任务级正向信号为 evaluator reward 高于对应基线。只有两条均满足机制级正向信号，且至少一条满足任务级正向信号，才允许把该机制扩展到更大任务集；否则如实记录为“减少循环但未改善任务”或“无效”。无论结果如何，本轮都不直接触发 Destination-First Binding Gate。

## 6. 停止与污染规则

- 任一条发生 L0、ADB 非幂等超时、MediaStore 初始化异常或 SSH 未恢复故障时，标记基础设施无效，只允许同一冻结版本精确替补；
- 不按 reward 选择替补，不覆盖旧 episode；
- Pilot 失败后不在同一任务上调阈值、改文案并冒充新验证；
- confirmation 结束后先分析证据，再决定是否另立新假设；
- 正式报告区分基线、matched diagnostic 和未来 held-out，不合并成功率分母。

## 7. 预实现文件哈希

- `controller.py`: `d8efb5ff350f8885456672404f9b71937663e8bf3b1418dcb3c80b28cfba0235`
- `protocol.py`: `88a6a7c17f2d3e1d54c5318b6ac14cdf1f88ad1086317032fc7fedcb3391bd93`
- `run_official_qwen_mobile.py`: `92fe9927e38475c67cbc3062e1a133a606dd8f90f5bd96ed342abaa286f583c6`
- `run_official_qwen_h01.ps1`: `0ef82a64b74feefc4b349591da0ff281ec79ea4999c19dc1f68a107a8829df25`
- backend config: `b8204fbf1288666854eb508663e1792223f50c4824178c33fe827e153a36294c`
- source 57-instance manifest: `2d0fe5521b618143c89caeab0ab44d3566690384d5ddc01f4f480c8b6a532a79`

实现完成后必须追加实现后哈希和测试结果，随后才可启动任何生成调用。

## 8. 实现冻结记录（生成调用前追加）

- 预注册正文冻结哈希：`900204ce84442b3b2be085018b273b7506576f1dca705972da670de81c2ddd85`
- 实现后 `controller.py`：`e198fed3ff44dc25c11ddedbf3734dca90e4cf97bf08f7afc2e9abf898ee0245`
- 实现后 `run_official_qwen_mobile.py`：`bd92fe26087b3ad4f5a8a1ff69ec7d6d6bc208226303ac87f1fa298618faa48b`
- 实现后 `run_official_qwen_h01.ps1`：`ff42d8c86e92a078cfb2d3a0f1555fcb3cb7adee43f43fed261b9e39af38dd58`
- 冻结诊断 manifest：`20638f4df2c4beaa6f76fe6e5a32641890bf69e2f845da289e027a473e252525`
- `05_project/tests/official_qwen_mobile`：25 tests passed
- PowerShell launcher 语法解析：PASS

实现与测试到此冻结。之后若代码、阈值、文案、任务顺序或参数任一变化，本预注册失效，必须另立版本。
