# GPU 8 小时执行目标：完成审计

审计日期：2026-08-08（Asia/Hong_Kong）

## 审计结论

本轮从约 00:09 的开卡资格检查开始，08:32 时已连续超过 8 小时，并继续工作至超过 16 小时。原目标中的 GPU/vLLM 资格、L0--L5 非侵入记录、single-step、8-step smoke、完整 57-key Hard、低级实现错误隔离、结果保存分析和基于分层证据的最小因果救援均有当前工件直接支持。目标已完成，但所有方法结果仍按实际证据报告：官方基线为 7/57，已运行的最小救援均未取得可扩大的正向结果。

## 逐项证据

| 原始要求 | 直接证据 | 审计结果 |
|---|---|---|
| 连续推进至少 8 小时 | `05_project/docs/GPU_8H_EXECUTION_PLAN_2026-08-08.md` 第 10 节保留 00:09 开始、08:32 已超过 8 小时及其后超过 16 小时的逐阶段事实；完整 Hard 的有效 episode 自身累计运行 28,316.04 秒 | 完成 |
| GPU 与 vLLM 资格门 | 冻结后端为单张 RTX PRO 6000 96GB、vLLM 0.26.0、BF16；1175/1175 个最终有效模型调用均记录同一模型、revision、runtime 和 backend，缺失元数据为 0 | 完成 |
| L0--L5 非侵入式分层记录 | 对最终 57 个科学有效 `episode.json` 做逐步审计：57/57 文件存在，1175 个 step event 全部同时含 `L0_runtime` 至 `L5_completion_evaluator`，缺失 step 为 0；模型仍只见当前截图，UIAutomator 仅作隐藏审计 | 完成 |
| Qwen3-VL-32B 官方 baseline 单步 | `official_qwen_20260808T003613_17297024/aggregate.json` 独立记录 1-step BrowserMultiply 链路 | 完成 |
| Qwen3-VL-32B 官方 baseline smoke | `official_qwen_20260808T003855_427a855e/aggregate.json` 独立记录 8-step smoke；未混入 Hard 成功率 | 完成 |
| 完整 Hard Pulse | `official_qwen32b_full_hard_combined_corrected_final.json` 通过 19 类 × 3 seed、57 个唯一科学有效键、无 in-progress 的完整性门；结果为完整成功 7、部分奖励 2、有效调用 1175 | 完成 |
| 排除并修复低级配置/接口错误 | 已隔离并记录 FlashInfer/SM12 sampler、失效 accessibility forwarder、UI 树后端、崩溃弹窗、过严 prose parser、SSH 隧道中断、ADB 前台输入、Retro MediaStore 等问题；无效旧结果保留，替补按任务键和 hash 合并，不按 reward 挑选 | 完成 |
| 保存并分析全部结果 | 原始 episode、截图、UI 记录、model call、transition、evaluator、aggregate、57-key 汇总、失败分类、逐例说明与正式报告均保留；自动审计得到 21 条虚假成功、39 条重复状态、14 条连续停滞 | 完成 |
| 依据分层证据实施最小因果救援 | 先做 H01 瞬时观察携带，再做 L4 Transition Attestation matched diagnostic；随后对象角色、完成验证与源文档覆盖均按资格门推进。救援没有正向净收益，均依预注册停止，没有在已观察任务上调参后冒充 held-out | 完成 |
| GPU 开启时不得无事等待 | 开卡后持续执行资格修复、单步、smoke、Hard、故障替补、离线审计、matched rescue、测试和报告；隧道中断时切换到 manifest 筛选、parser 回放、失败审计和 watchdog，而不是等待端点自行恢复 | 完成 |

## 关键一致性复核

- 最终 57 个有效 episode：`57/57` 原始文件可定位。
- 最终有效 step：`1175`。
- L0--L5 缺失 step：`0`。
- 模型调用元数据缺失：`0/1175`。
- 唯一模型：`Qwen/Qwen3-VL-32B-Instruct`。
- 唯一 revision：`0cfaf48183f594c314753d30a4c4974bc75f3ccb`。
- 唯一 runtime：`vllm_openai`。
- 唯一 backend：`qwen3_vl_32b_vllm_bf16_1xrtxpro6000_official_public_v1`。
- 当前本地模型健康接口仍返回上述 model id；模拟器 `emulator-5554` 状态为 `device`。
- 相关回归测试：52/52 通过。

## 工件哈希

| 工件 | SHA-256 |
|---|---|
| `05_project/docs/GPU_8H_EXECUTION_PLAN_2026-08-08.md` | `768A480793DC74FF60DAE26690B7CE41D48D9286570ED1D00B11E9D8EF25C886` |
| single-step `aggregate.json` | `CA7869F661E7F3BB3CD0E3FD8C62A979AFF02A10E51642A510BA9E9C2B666592` |
| 8-step smoke `aggregate.json` | `D7CD910E35DEF9BE06537F7091436971C19FC4830B45397C86716552829284F6` |
| `reports/official_qwen32b_full_hard_combined_corrected_final.json` | `81B798EE8561F37054354C5A41A16F6B4D7DAE3FB7EEBE473D5A08802876D242` |
| `reports/official_qwen32b_full_hard_failure_taxonomy_2026-08-08.md` | `A89826703BEB9BEF0EAE9E4EC7386F3ECCFACA860655973133C27F2CC71DDC5A` |
| `reports/official_qwen32b_hard_pulse_2026-08-08.md` | `2F71A0D9B894DD2C59B789835A1E54C3217E2B2ACEB14468974A6726E54CCDC7` |
| `reports/l4_transition_attestation_matched_diagnostic_2026-08-08.md` | `EA6ECFD4C9BF50E7F6EE293698990468DAB1BF4AAB9BAABD1D3B7AA45BD52A05` |
| `reports/source_document_coverage_gate_matched_2026-08-08.json` | `A4BBCBACE69F1F7205E80858A91FC4CF8B31B02C3B37A532DDE96DF9337E4CAD` |
| `reports/source_document_coverage_contract_audit_2026-08-08.json` | `05B2F39F1BA051739F410C53C0F2C104D7315812AE842693414454598507C24A` |

## 边界

“目标完成”指本轮承诺的工程资格、官方基线、分层记录、故障排除、证据分析与最小救援已经完成，不表示 RAVEN-M 已获得新的正向方法效果。当前可信结论是：官方式 Qwen3-VL-32B 在本地 AndroidWorld Hard 上具有非零能力；长程失败主要沿 source coverage、对象捕获、跨应用交接、字段写入和 evaluator closure 连续累积；现有最小救援不足以跨越资格门。
