# Official Qwen Mobile tool-call extractor 对齐修正预注册

冻结时间：2026-08-08 09:39（Asia/Hong_Kong）  
状态：在任何修正 parser 补跑生成调用之前冻结

## 1. 发现与证据

固定官方来源为 Qwen3-VL commit `96588727e44c78b25ba03ea03b8e12f7e64fd0da` 的 `cookbooks/mobile_agent.ipynb`。notebook 的真实执行代码从输出的 `<tool_call>...</tool_call>` 中提取 JSON 并执行，不解析 Thought 的句数或段落数。本地旧 parser 除验证工具 JSON 外，还要求 Thought 与 Action 都严格单行，因而会拒绝官方 extractor 本会执行的合法动作。

这项修正不是看过 evaluator 结果后改变任务策略，而是官方接口对齐：模型输出的工具名、动作 schema、参数、坐标范围和 JSON 仍须合法；多 tool call 仍因动作歧义 fail closed。

## 2. 冻结代码与测试

- 修正 parser：`05_project/src/raven_m/official_qwen_mobile/protocol.py`
- parser SHA-256：`88a6a7c17f2d3e1d54c5318b6ac14cdf1f88ad1086317032fc7fedcb3391bd93`
- parser 测试 SHA-256：`1cdb5f3a0475dcb900048e1ac64aef949f7ccef53b248e6cc26e765d06533a9e`
- 相关测试：23 passed
- 冻结官方 system prompt SHA-256 仍为 `9d060af15f62acb31b9fb197649ec001d4096491d7fb102de929316944b3e26d`

## 3. 机械资格规则

严格 parser 套件结束后，只补跑同时满足以下条件的 episode：

1. 原记录 `termination_reason == official_output_invalid`；
2. 原记录具有明确 `protocol_error_steps`；
3. 将该步**原始模型文本**交给本文件冻结的新 parser 后可得到一个合法官方 `mobile_use` tool call；
4. task class、task seed、goal hash、params hash 与原生 max steps 可在原 57-instance manifest 中精确匹配。

若原输出使用 schema 外动作（例如 `paste`）、JSON 无效、参数非法或存在多个工具调用，则不进入替换集合，继续作为真实协议失败。

当前运行中机械规则已识别三条 provisional replacement key：

- `ExpenseAddMultipleFromMarkor / 20260807`
- `MarkorTranscribeVideo / 20260807`
- `OsmAndTrack / 20260807`

最终集合由 `build_official_parser_replacement_manifest.py` 在严格套件结束后重新计算；只能增加后续同规则命中的 episode，不能凭人工偏好增删。

## 4. 补跑匹配与污染边界

- 模型、revision、权重、官方 system/user prompt、sampling、解码 seed、任务参数与原生 action budget 全部不变；
- 不增加记忆、planner、critic、guard、UI tree、evaluator 信息或失败案例专用提示；
- 补跑只替换受本地 over-strict prose envelope 影响的同一 `(task_class, task_seed)`；
- 旧 episode、截图、events 与 evaluator 输出不删除、不覆盖，使用 validity overlay 标注为 `local_over_strict_parser`；
- 最终合并器必须保证每个 key 恰有一条科学有效记录，重复有效 key 直接报错；
- 补跑结果无论成功或失败均接受，不据结果再次修改 parser 后冒充同一冻结实验。

## 5. 停止规则

补跑集合全部完成后，先生成纠正后的 57-key baseline 与失败分布。若又发现不同的官方接口偏差，停止进入科研救援，保留证据并另立修正协议；不得在同一补跑中静默改变实现。
