# 可执行源文档覆盖门：同实例源阶段对照实验

## 一句话结论

在 3 个新的 Markor 跨应用任务实例上，外部可执行覆盖门把向前滚动从基线的 0 次提高到 64 次，并把截图中可恢复目标对象的微平均召回率从 0 提高到 12.5%；但它只打开 2/3 份文档、只在 1/3 任务中产生页尾证明、没有任何任务找齐全部对象，而且为此把模型调用从 82 次增加到 141 次。因此本轮没有通过预注册资格门，不授权继续实现 destination-write 或结构化记忆模块。

## 研究问题与证据边界

本轮只回答一个源阶段问题：当模型准备在尚未证明读完整份 Markor 文档时离开，控制器强制继续向前滚动，能否增加随后可从真实截图中恢复的任务相关对象？实验不运行到最终任务完成，不使用 native evaluator 形成任务成功率，也不比较完整框架优劣。三个任务类已经在前序诊断中被观察过；seed 20260809 是新实例，但本轮属于开发集机制实验，不是 pristine held-out 结果。

两组使用同一个三任务 manifest、同一 Qwen3-VL-32B-Instruct revision、同一解码设置、同一当前截图输入和同一 60 步上限。基线使用官方式 prompt/controller；干预组使用冻结的 coverage prompt 与 `SourceDocumentCoverageGate`。在 Markor `DocumentActivity` 内，只要页尾尚未证明，任何非向前扫描、Home、Back、answer 或 terminate 都会被替换为固定向前滑动。每张实际观察到的、去重后的文档截图随后只调用一次冻结的可见对象提取器；隐藏 `row_objects` 只在输出后用于评分。

## 主要结果

| 指标 | 匹配基线 | 可执行覆盖门 | 预注册要求 | 判定 |
|---|---:|---:|---:|---|
| 打开 Markor 文档 | 1/3 | 2/3 | 干预组 3/3 | 未通过 |
| 至少一次向前滚动 | 0/3 | 2/3 | 干预组 3/3 | 未通过 |
| 页尾证明 | 0/3 | 1/3 | 干预组 3/3 | 未通过 |
| 向前滚动总数 | 0 | 64 | 仅作过程计数 | --- |
| 提取器合法输出 | 3/3 | 65/65 | 干预组全部合法 | 通过 |
| 微平均精确率 | 0（无正预测） | 100%（1 TP，0 FP） | 干预组 100% | 通过 |
| 微平均召回率 | 0/8 = 0 | 1/8 = 12.5% | 干预组至少 75% | 未通过 |
| 召回率绝对增量 | --- | +12.5 个百分点 | 至少 +20 个百分点 | 未通过 |
| 完整找齐对象的任务 | 0/3 | 0/3 | 干预组至少 2/3 | 未通过 |
| 总资格门 | --- | --- | 八项全部通过 | **未通过** |

干预组的唯一正确恢复对象是 `RecipeAddMultipleRecipesFromMarkor2` 中的 `BBQ Chicken Quesadillas`。同一任务仍漏掉 `Cauliflower Fried "Rice"` 和 `Greek Salad Pita Pockets`；支出任务漏掉 `Pet Supplies` 与 `Dividends`；另一个菜谱任务因为从未打开 `recipes.txt`，三个目标对象全部记为 false negative。

## 三条轨迹分别说明了什么

### 1. 打开文档后强制滚动，不等于能在步数预算内读完

`ExpenseAddMultipleFromMarkor` 成功进入 `my_expenses.txt`。模型在覆盖仍开放时七次提出离开或非扫描动作，控制器均按实现契约改写为向前滚动；整条轨迹执行 53 次向前滚动，证明门确实改变了实际动作，而不是只改变自然语言解释。然而任务到达 60 步上限时仍没有获得页尾证明，且两个正确对象都没有出现在提取结果中。这里最早失败点从“完全不滚动”后移成了“可编辑长文档中的扫描推进过慢，原生动作预算不足”。

### 2. 只在 DocumentActivity 激活的门，来不及纠正“看见文件却没有打开”

`RecipeAddMultipleRecipesFromMarkor` 已进入 Markor 文件列表，屏幕上明确可见 `recipes.txt`，但模型没有点击文件，而是直接返回桌面并开始寻找 Broccoli。因为覆盖门只在 `DocumentActivity` 激活，这一错误发生在门获得权限之前；随后轨迹在启动器中重复搜索直到 60 步耗尽。该结果说明覆盖契约至少需要两个连续前置条件：先证明指定文件已经打开，再证明文件从起点遍历到终点。只实现第二个条件不足以保证源材料覆盖。

### 3. “一次滑动无变化”不是可靠的页尾证明

`RecipeAddMultipleRecipesFromMarkor2` 成功打开 `recipes.txt`，控制器在 step 9 把模型的 tap 改写为向前滑动。step 12 的一次滑动满足冻结判据：像素变化低于 0.001、Activity 不变、UI-tree hash 不变，于是系统记录 `bottom_attested=true`。但此后的同向滑动仍产生明显的新画面，说明前一次无变化可能只是手势未推进、编辑器焦点或渲染状态造成的 no-effect，而不是真正页尾。虽然冻结评分仍忠实把该任务计作“取得页尾证明”，机制解释必须更严格：这是一条被后续证据反驳的页尾判定，不能据此声称完成了全文遍历。

## 成本与净收益

源阶段基线共使用 82 次模型调用、323,495 个 prompt tokens 和 10,406 个 completion tokens；覆盖门条件使用 141 次调用、612,785 个 prompt tokens 和 21,119 个 completion tokens。也就是说，干预额外使用 59 次调用和 289,290 个 prompt tokens，才获得 1 个额外正确对象，且没有产生任何完整对象集合。离线提取器又从基线的 3 张截图增加到干预组的 65 张截图，分别消耗 8,223 与 178,199 个总 tokens。当前结果不是“用更多时间稳定换来更高准确率”，而是“成本大幅增加，召回只小幅上升，完整覆盖仍为零”。

## 合法结论与停止决定

本轮支持三个有限结论。第一，外部动作门能够真实阻止过早离开并显著增加向前扫描次数，因此 prompt-only 失败并不等于覆盖行为不可控制。第二，当前门的激活范围太晚：文件未打开时它没有权限纠错。第三，当前页尾判据把“手势无效”与“已经到底”混为一谈；可靠覆盖需要起点证明、单调位置证据和经过重复确认的终点证明，而不能只看一次截图与 UI tree 无变化。

本轮不支持“覆盖门提高了任务成功率”“Qwen 已经可靠读完整份文档”“结构化记忆应立即实现”或“该方法具有一般性优势”。按照冻结停止规则，八项资格条件只有合法 JSON 和精确率两项通过，因此不扩大到 destination-write 阶段，也不在这六个已观察 cells 上修改坐标、阈值或 prompt 后冒充 held-out。下一次若继续，应使用新的 seed 和新的预注册，先把 coverage contract 改成 `正确文件打开 -> 起点已证明 -> 单调向前覆盖 -> 连续页尾确认`，并给扫描动作单独预算；只有 object recall 先通过资格门，才进入目标绑定与写入实验。

## 协议偏差与有效性说明

基线截图提取在覆盖门 suite 启动前完成，而预注册文字写的是“两组 source-stage suites 完成后再提取”。这没有把隐藏标签暴露给在线 Agent，提取器与在线控制器也没有共享会话状态，但它改变了预注册的操作顺序，必须记为 protocol deviation，不能省略。覆盖门 suite 的本地监督壳在运行一小时后超时退出，但实际 Python runner 没有被终止，继续完成第三个任务并正常写出三条 `episode.json` 与 suite `aggregate.json`；端点和模拟器在前后均健康，因此这不是模型失败单元，也没有进行重试或拼接。

此外，干预组同时改变了 coverage prompt 和外部覆盖门，故本轮估计的是二者组成的干预包，而不是外部门的纯净单因素效应。三个任务、单一模型 revision 和单一设备环境也不足以外推一般效果。

## 可复核材料

- 预注册：`05_project/docs/SOURCE_DOCUMENT_COVERAGE_GATE_MATCHED_PREREG_2026-08-08.md`
- 三任务冻结清单：`05_project/configs/task_manifests/source_document_coverage_gate_markor_seed_20260809_v1.final.json`
- 基线 suite：`runs/official_qwen_mobile/official_qwen_20260808T195143_94ea41d5/`
- 覆盖门 suite：`runs/official_qwen_mobile/official_qwen_20260808T203045_cb017b51/`
- 基线提取：`runs/visible_object_extractor/visible_object_extractor_20260808T202947_07a5bea1/`
- 覆盖门提取：`runs/visible_object_extractor/visible_object_extractor_20260808T213357_49276721/`
- 机械比较 JSON：`reports/source_document_coverage_gate_matched_2026-08-08.json`
- 零调用覆盖契约审计：`reports/source_document_coverage_contract_audit_2026-08-08.json`
- 审计脚本：`05_project/scripts/audit_source_coverage_contract.py`
- 本报告：`reports/source_document_coverage_gate_matched_2026-08-08.md`
