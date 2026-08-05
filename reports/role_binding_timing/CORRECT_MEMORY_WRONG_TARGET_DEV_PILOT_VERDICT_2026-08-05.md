# Correct Memory, Wrong Target：DEV Pilot 最终判定

日期：2026-08-05  
研究阶段：开发集机制筛查（development-contaminated）  
结论等级：仅用于决定是否继续投入，不允许作为 confirmatory claim

## 1. 最终结论

本轮没有得到“正确的 source fact 在 destination grounding 之前出现，会提高错误目标率”的正向证据。三轮实验共完成 96 个条件单元、192 次本地模型调用；所有输出均可解析，正确值回忆率始终为 100%，但三轮的 `Timing × Ambiguity` 交互均为 0。

最关键的是 v0.3：当任务达到预注册的资格条件时，低歧义准确率为 100%，Early/ Late 在高低歧义条件下也全部选对，错误目标率均为 0。因此 Stage 1 的效应门没有通过，不能进入 `Destination-First Binding Gate` 的方法实现。

按照事先冻结的 stop rule，本项目应停止继续“挽救”这一具体 timing 假设。继续增加规则、修改样本或在同一批截图上寻找能出效果的措辞，只会增加开发污染，不能形成可信创新。

## 2. 被检验的具体问题

我们固定了：

- 同一张真实 AndroidWorld 截图；
- 同一条完全正确的 source fact；
- 同一任务、模型 revision、temperature、两次 model calls 和 action budget；
- Early/ Late 每个 matched pair 的真实 Qwen tokenizer 文本 token 总数完全相同；
- 第一次调用负责定位 destination，第二次调用负责给出第一次目标动作。

唯一核心操纵是：正确 fact 在 destination grounding 前出现（Early），还是在 grounding commitment 后出现（Late）。主要指标为第一次目标动作是否指向错误对象。

冻结模型为 `Qwen/Qwen3-VL-32B-Instruct`，revision 为 `0cfaf48183f594c314753d30a4c4974bc75f3ccb`，backend 为 `qwen3_vl_32b_transformers_bf16_4x4090_v1`。

## 3. 三轮结果

| Pilot | 候选信息 | 低歧义准确率 | Early-Low 错误率 | Late-Low 错误率 | Early-High 错误率 | Late-High 错误率 | 交互 | 资格 | 信号 |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| v0.1 | target ID + 屏幕文字 + 人工 visual cue + bounds | 100% | 0% | 0% | 0% | 0% | 0 | 通过 | 未通过 |
| v0.2 | target ID + bounds；必须自己从截图建立文字—区域映射 | 25% | 75% | 75% | 87.5% | 87.5% | 0 | 未通过 | 未通过 |
| v0.3 | target ID + 屏幕原文字段 + bounds；不提供人工 visual cue | 100% | 0% | 0% | 0% | 0% | 0 | 通过 | 未通过 |

共同指标：

- 每轮 32/32 单元有效；
- parser failure 均为 0%；
- exact value recall 均为 100%；
- 三轮合计 192 次生成调用；
- reported prompt tokens 合计 639,192；
- reported completion tokens 合计 7,233；
- 各轮均无选择性重试。

原始结果：

- `05_project/artifacts/role_binding_timing/stage1_dev_pilot_v0_1/summary.json`
- `05_project/artifacts/role_binding_timing/stage1_dev_pilot_v0_2/summary.json`
- `05_project/artifacts/role_binding_timing/stage1_dev_pilot_v0_3/summary.json`

## 4. v0.2 为什么不能算 timing 假设的反例

v0.2 去掉了候选的屏幕文字，只给 target ID 和像素 bounds。模型必须先读截图，再自行判断每个匿名 bounds 对应哪一行。它在低歧义条件下也只有 25% 准确率，说明失败发生在 destination grounding 之前。

逐样本可以看到：第一次 grounding 一旦选错匿名区域，第二次 action call 通常会忠实沿用这个错误 commitment；Early 与 Late 的错误完全一致。这证明 v0.2 测到的是截图—区域绑定困难，不是正确记忆出现时机造成的 role-binding amplification。

## 5. v0.3 为什么构成停止证据

v0.3 只恢复截图中本来就存在的文字标签，用于把匿名 target ID 对应到真实 UI 行；它没有恢复 `medical icon`、`second recipe card` 等人工语义解释。这样既消除了 v0.2 的基础 grounding floor，也没有把额外推理答案直接写进 visual cue。

在这个合格设置下：

- 模型始终准确回忆正确值；
- 低歧义任务全部选对；
- 高歧义任务也全部选对；
- 没有 source-as-target；
- 没有 grounding 后 drift；
- Early 与 Late 没有任何行为差异。

因此当前证据呈现出一个清楚的边界：

> 当 destination 能被可靠定位时，正确 source fact 的出现早晚没有造成可观察的错目标；当 destination 不能可靠定位时，错误由视觉/区域 grounding 主导，而且仍与 fact timing 无关。

## 6. 允许和不允许的结论

允许：

- 在这 8 个开发模板、3 个 app 场景和当前 Qwen revision 上，没有观察到 GPT Pro 所预测的 timing effect；
- v0.2 暴露了截图文字与匿名候选区域之间的 grounding floor；
- 当前没有资格开发或宣称 `Destination-First Binding Gate` 有效；
- 继续投入应转向新的 grounding/perception 问题或新的独立研究假设。

不允许：

- 宣称所有 GUI agent 都不存在该效应；
- 把 0/8 当作严密的普遍 causal null bound；
- 把 v0.2 的高错误率归因于 memory；
- 在看过这些结果后修改同一批任务，再把新结果称为 held-out；
- 因为假设失败而直接实现 Gate，并用方法结果反向证明机制存在。

## 7. 决策

Stage 1 资格门在 v0.3 通过，但 Timing × Ambiguity 效应门失败。正式决策为：

1. 不扩大到 48 个 base instances；
2. 不运行 Stage 1 confirmatory study；
3. 不实现 Destination-First Binding Gate；
4. 冻结 v0.1—v0.3 为开发期结果；
5. 下一步若继续研究，必须提出一个新的、可证伪的问题，而不是继续调整这批模板。

目前最直接的新问题不是“怎样让 memory 更复杂”，而是：AndroidWorld hard 任务中，模型在已经知道 destination 文本时，为什么仍会把它映射到错误的视觉区域或控件，以及这种错误在真实任务中的占比是否足够高。这个方向与本轮 v0.2 暴露的 first-broken-edge 一致，但它是新的 grounding 研究问题，需要重新做 novelty audit 和预注册，不能沿用本轮的正向假设。
