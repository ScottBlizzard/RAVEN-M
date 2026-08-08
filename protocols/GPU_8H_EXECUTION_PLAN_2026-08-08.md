# Qwen3-VL-32B 开卡后 8 小时执行计划

版本：2026-08-08 v1.0  
状态：开卡前冻结；执行中只能追加事实记录，不能悄悄改写已发生结果。  
主目标：在 AndroidWorld 上建立可信的 Qwen3-VL-32B 官方公开 Mobile Agent 基线，完成冻结 Hard Pulse，并用非侵入式分层证据定位失败原因和开展最小因果救援。

## 1. 本轮只回答什么

本轮优先回答一个问题：

> 同一个 Qwen3-VL-32B，在 Qwen 官方公开的移动代理提示词、消息组织、坐标协议、vLLM 运行时和推荐生成参数下，是否具备完成 AndroidWorld Hard 任务的非零能力？

随后才回答：

> 旧 B3/M0 的全零结果中，有多少来自模型能力，有多少来自我们自己的配置、协议、动作接口、控制器或完成判断？

本轮不同时复刻更多外部框架，不在结果出来前添加 memory、planner、critic 或 guard，不把安装成功、格式正确或页面跳转当成任务成功。

## 2. 开卡前必须已经具备的条件

- vLLM 独立环境：`/root/autodl-tmp/envs/qwen_vllm`
- 固定运行时：`vllm==0.26.0`
- 模型目录：`/root/autodl-tmp/models/Qwen3-VL-32B-Instruct-modelscope`
- 14 个 safetensors 分片，共 `66,714,912,872` bytes
- 权重 SHA-256 清单：`/root/autodl-tmp/models/Qwen3-VL-32B-Instruct-modelscope.sha256`
- 权重清单 SHA-256：`18e0909c7d993853d6d0f62443461a74009754f90db026a1723cab80121c7872`
- 官方 Qwen 代码 commit：`96588727e44c78b25ba03ea03b8e12f7e64fd0da`
- 官方 Mobile Agent system prompt SHA-256：`9d060af15f62acb31b9fb197649ec001d4096491d7fb102de929316944b3e26d`
- 模型 revision：`0cfaf48183f594c314753d30a4c4974bc75f3ccb`
- 本地与远端官方基线单元测试通过
- 零生成 preflight 通过
- 无卡时一键脚本必须拒绝运行

任何一项不满足，先在无卡模式修复；开卡后发现漂移时，立即记录并修复，而不是继续产生不可解释数据。

## 3. 固定实验条件

### 3.1 模型与生成

- 模型：`Qwen/Qwen3-VL-32B-Instruct`
- 推理：stock vLLM OpenAI-compatible server
- dtype：BF16
- tensor parallel：1
- temperature：0.7
- top-p：0.8
- top-k：20
- presence penalty：1.5
- repetition penalty：1.0
- generation seed：3407
- max output tokens：32768
- vLLM max model length：65536
- max concurrent sequences：1

### 3.2 Agent 行为

- 使用官方公开 Mobile Agent system prompt；不添加 RAVEN-M 指令。
- 每一步只输入当前截图、任务目标和官方格式的文字动作历史。
- 坐标为官方 0--999 网格，再确定性映射到实际屏幕像素。
- 不使用历史截图、UI tree、evaluator 反馈、memory、planner、critic、guard 或输出修复调用。
- 模型声称 `terminate(success)` 只是声明；最终成功只由 AndroidWorld evaluator 决定。

### 3.3 任务与重复

- 冻结任务：H01、H06、H09、H17。
- 使用冻结 manifest 和 seed，不重新生成更容易的参数。
- 正式 baseline 每个 cell 一次，不因失败而重跑。
- 基础设施无效尝试保留原始目录，标为 `INFRASTRUCTURE_INVALID`，不计入成功率。
- 看过任务后产生的修改只能叫 diagnostic/rescue，不能冒充 held-out baseline。

## 4. 从第一步开始记录的六层证据

分层记录必须是旁路记录：只观察并写盘，不改变模型输入、动作或 evaluator。

### L0：运行环境与模型服务

每次模型调用记录：时间、GPU、显存、服务 PID、模型 ID、revision、vLLM 版本、请求耗时、prompt/completion tokens、HTTP 状态、异常、OOM 和重试。

可回答：失败是不是服务、显存、隧道、超时或版本问题？

### L1：视觉输入与目标定位

记录：原始截图、尺寸、SHA-256、当前 app/activity、模型 Thought、Action、原始坐标。

可回答：模型有没有看到正确对象？目标语义正确但坐标错误，还是目标本身就判断错了？

注意：baseline 中不把 UI tree 提供给模型。UI tree 只作为隐藏的事后审计证据。

### L2：协议解析与坐标映射

记录：完整原始输出、parser 结果、canonical action、0--999 坐标、归一化坐标、真实像素、解析错误。

可回答：模型本来答对了，但是否被我们的 parser 或坐标转换弄错？

### L3：动作执行

记录：发送给 AndroidWorld/ADB 的实际命令、执行状态、异常、开始与结束时间、是否重试。

可回答：动作本身正确时，系统有没有真的执行？有没有重复输入、重复点击或清除文本错误？

### L4：页面变化与任务进展

记录：动作前后截图、截图哈希、像素差异、activity/package、隐藏 UI tree 哈希、页面是否变化、是否进入预期页面、近期动作是否重复。

可回答：点击是否产生预期页面变化？模型有没有利用变化后的新状态继续行动？

### L5：完成声明与真实 evaluator

记录：模型完成声明、终止原因、step budget、AndroidWorld reward、任务底层 evaluator 输出、tear-down/reset 状态。

可回答：是任务真的完成、模型过早停止，还是表面完成但底层状态没有改变？

## 5. 8 小时时间线

时间是执行上限与切换依据，不是为了等满时间。前一阶段提前完成就立即进入下一阶段。

### T+00:00--00:20：GPU 资格与服务启动

1. 保存 `nvidia-smi`、驱动、CUDA、GPU 型号与显存。
2. 运行零生成 preflight，确认权重、prompt、commit 和采样配置未漂移。
3. 启动 stock vLLM，保存完整启动日志。
4. 检查 `/v1/models` 返回唯一的 32B 模型。
5. 记录模型加载时间和加载后显存。

异常处理：

- 缺包或命令参数错误：立即安装/修改并记录，不空等。
- CUDA/驱动不兼容：保留日志，查 vLLM/Qwen/NVIDIA 官方资料，选择与驱动匹配的固定版本。
- OOM：先确认没有残留进程；再调低不影响模型语义的服务容量参数。不得擅自量化或更换模型并仍称同一 baseline。
- 20 分钟内仍无法形成明确诊断时，先处理最接近根因的错误；不得反复执行同一失败命令。

### T+00:20--00:35：固定截图单步生成

1. 使用冻结手机截图发起一次请求。
2. 检查官方输出三段式、tool call JSON、坐标范围和终止符。
3. 检查请求内 text 在 image 之前，且没有多余 RAVEN-M 内容。
4. 记录首 token/总延迟与 tokens。

失败时修服务或客户端；不进入 AndroidWorld。

### T+00:35--01:00：最多 8 步的简单链路 smoke

运行一个简单任务，仅验证：初始化、截图、生成、动作、页面变化、evaluator、tear-down 和 reset。

通过标准：至少有一次正确页面变化；每步只执行一个动作；无旧截图、重复 transport 请求或解析漂移；evaluator 被调用。

smoke 结果不得计入 Hard 成功率。

### T+01:00--01:40：H01 资格性正式 baseline

运行冻结 H01 `BrowserMultiply`，从第 0 步开始保存 L0--L5。

结束后立即审计：

- 是否是有效 evaluator 结果；
- 是否存在我们的低级错误；
- 是否有数据缺层；
- 是否可以继续完整 Hard Pulse。

若发现代码/配置错误：保留本次为无效或旧实现结果，修复后重新建立新版本 baseline；不能覆盖原目录。

### T+01:40--04:30：完成完整 Hard Pulse

依次运行：

1. H06 `MarkorMergeNotes`
2. H09 `OsmAndTrack`
3. H17 `SportsTrackerActivitiesOnDate`

每个任务结束立即生成单任务摘要，但不根据结果修改后续 baseline 条件。

### T+04:30--05:30：完整分层审计

为四个任务分别标注最早失败层：

- L0 runtime
- L1 perception/grounding
- L2 parsing/mapping
- L3 execution
- L4 state/progress
- L5 completion/evaluator

同时统计：成功率、有效任务数、模型调用数、动作数、平均延迟、重复动作、无页面变化动作、解析失败、过早终止和 evaluator 分歧。

不得用“看起来像”代替证据；不确定项标为 `UNCERTAIN`。

### T+05:30--07:15：最小因果救援

根据最常见且最早的失败层，只选择一个最小干预：

- L1 失败：只替换/约束目标定位，其他层不动；
- L2 失败：只修 parser 或坐标映射；
- L3 失败：只修动作执行；
- L4 失败：只提供最小状态/历史救援；
- L5 失败：只修完成验证与继续策略。

先在一个已观察任务上做 diagnostic rescue，明确标注污染；若形成固定修改，再选择尚未用于调试的实例或额外 seed 做验证。若四个任务均已观察，只能声称因果诊断证据，不能声称 held-out 泛化。

### T+07:15--08:00：汇总与下一轮冻结

1. 冻结代码 commit、配置、环境 lock 和结果哈希。
2. 生成 baseline 表、分层失败表和 rescue 前后对照。
3. 区分：成功结果、科学失败、基础设施无效、探索性发现。
4. 更新正式实验报告，但不改写旧 frozen 结果。
5. 根据证据决定下一轮是 grounding、执行、状态记忆、完成验证还是更换模型/框架。

## 6. 绝不空等原则

GPU 开着时，如果主实验被环境问题阻塞，立即切换到能推动根因解决的工作：

- 读错误栈和服务日志；
- 查官方文档、issue 与兼容矩阵；
- 写最小复现；
- 在不加载模型的进程中修客户端/parser/logger；
- 检查 AndroidWorld、ADB、emulator 和 evaluator；
- 整理已产生的分层证据；
- 修复后从最近合法 gate 继续。

不得仅轮询、睡眠或等待用户。只有需要账号、付费选择、硬件重启或研究方向取舍时才请求用户。

## 7. 结果解释规则

### 官方 baseline 非零

说明 Qwen32B 和基础链路具有 Hard 非零能力；旧全零结果不能只归因于模型，必须根据分层证据检查旧 controller/config。此时进入正式科研比较与逐层干预。

### 官方 baseline 仍为零

不能直接说模型不行。必须证明 L0--L3 正常，并展示失败集中在 L1/L4/L5 的具体证据。随后通过最小救援判断模型是否在某一层可被挽救。

### 发现低级错误

如实记录错误、影响范围、首次出现版本、修复 commit 和修复前后结果；旧结果保留但降级为受该错误影响的证据，不能删除或覆盖。

## 8. 产物目录约定

建议根目录：

`05_project/outputs/official_qwen32b_hard_pulse_20260808/`

每个 run 至少包含：

- `run_manifest.json`
- `environment.json`
- `model_health.json`
- `events.jsonl`
- `episode.json`
- `screenshots/step_*_before.png`
- `screenshots/step_*_after.png`
- `ui_tree_hashes.jsonl`
- `layered_diagnosis.json`
- `evaluator_result.json`
- `artifact_manifest.json`

全局至少包含：

- `aggregate.json`
- `failure_layer_matrix.json`
- `baseline_vs_existing.csv`
- `rescue_comparison.json`
- `EXECUTION_LOG.md`

## 9. 开卡执行入口

H01 一键资格入口：

```powershell
& 05_project/scripts/run_official_qwen_h01.ps1
```

执行前必须再次读本文件，并逐项核对第 2 节；不得跳过资格门直接批量运行。

## 10. 执行事实追加（不改写原计划）

> 本节只追加实际发生的事实；上文是开卡前冻结计划，时间估计没有事后重写。

- 实际开卡与资格检查从 2026-08-08 约 00:09（Asia/Hong_Kong）持续进行；截至 08:32 已超过 8 小时，工作未因时间达标而终止。
- RTX PRO 6000 Blackwell 96GB、固定模型 revision、权重哈希、官方代码 commit、官方提示词哈希与采样参数均通过零生成资格门。
- vLLM 首次失败定位为 FlashInfer sampler 对 SM 12.0 的兼容问题；只禁用 FlashInfer sampler 后恢复，模型、权重与官方采样数值不变。
- AndroidWorld 无障碍树故障在任何生成前暴露；隐藏审计后端改用原生 UIAutomator，模型仍只看当前截图。失效 accessibility 插件弹窗被清除后，single-step 与 8-step smoke 通过。
- 冻结 Hard Pulse 四任务均完成，H01/H06/H09/H17 均为 evaluator 0，但 L0--L3 大体正常并形成不同最早失败机制。
- H01 的自由文本瞬时观察提醒在生成前完成预注册；结果仍为 0，且按停止规则未在同一 pilot 上调参重跑。
- 因用户要求不只停留在四任务诊断，原始官方 baseline 扩展为 19 类 × 3 seed 的 57 个冻结实例；原生动作预算与任务参数不变。
- seed 20260806 的 19 条科学有效结果为 4 个完整成功、1 个 0.5 部分分、14 个零分；这确认官方 Qwen3-VL-32B 链路在 Hard 上具有非零能力。
- 原始套件进入 seed 20260807 后，本地到远端模型的 SSH 隧道被重置；后续 38 条记录均标为基础设施无效，不计科学结果，也未覆盖旧文件。
- 从原 manifest 精确筛出 seed 20260807/20260808 的 38 条恢复集合，逐项比对 task、seed、goal/params hash 与 max_steps，差异数为 0；新套件从 seed 20260807 第一条重新开始。
- 为防再次静默断连，加入只监测 runner PID 与 localhost 模型健康的隧道 watchdog；它不改变任务、模型提示、动作或 evaluator。
- 恢复套件前四类截至完成时结果为：BrowserMultiply 0、ExpenseAddMultipleFromGallery 0、ExpenseAddMultipleFromMarkor 0、ExpenseDeleteMultiple2 1；无基础设施无效记录。ExpenseDeleteMultiple2 已在两个独立 seed 中均成功。
- 新增合并器按 `(task_class, seed)` 唯一键合并有效结果；重复有效键会直接报错，38 条旧基础设施记录只作为审计项保留。运行结束前已冻结最终统计、失败标注与下一项救援资格门。
- 09:12 前恢复套件又完成 9 条科学有效记录，合并后为 28/57：5 条完整成功、2 条部分分、总 reward 6.0；当前套件无新增基础设施无效记录。OsmAndTrack 已在两个 task seed 中复现“普通地图定位被自然语言历史提交为 waypoint”的最早错误。
- 对跨 seed 复现增加方法学限定：固定解码 seed 下，如果 goal 与初始截图完全相同，早期轨迹属于确定性重放而非独立随机试验。`RecipeAddMultipleRecipesFromImage` 的两个 seed 与一个成功打开 Gallery 的对照任务共享完全相同的初始截图哈希，证明入口可见；差异指向任务条件下的目标别名绑定与策略稳定性，而非 OCR 缺失。
- 二次核对官方 notebook 的真实 extractor 后发现本地 parser 的 prose envelope 过严。现有四条 `official_output_invalid` 中三条仍含官方会执行的合法 tool JSON，需标为实现影响并在新 parser 下精确补跑；一条使用 schema 外 `paste`，仍是真实协议错误。修正只放宽 prose 提取，不改变模型、提示词、工具 schema、坐标、任务或 evaluator；23 项相关测试通过，旧记录保留不覆盖。
- 实际连续工作超过 16 小时后，所有受 parser、ADB 前台输入超时、Retro MediaStore 刷新与 SSH post-response stall 影响的键均完成独立替补；旧无效记录全部保留，未按 reward 挑选替代。
- 最终合并在 `--expected-eligible 57` 门下通过：19 类任务 × 3 seed、57 个唯一科学有效键、无 in-progress；完整成功 7、正奖励 9、部分奖励 2、有效模型调用 1175。
- 最后一个 `RetroSavePlaylist/20260808` 在 50 次模型调用/50 个动作后因原生步数上限结束，reward 0；全程没有模型超时、SSH 重连、解析错误或 ADB 执行错误，因此计为干净策略失败。
- 57-key 自动审计得到 21 条虚假成功声明、39 条重复状态、14 条连续停滞。下一项最小救援资格收敛到 L4“无转移不得提交语义效果”，先做 matched diagnostic，不直接宣称 held-out 泛化，也不提前实现更宽的目标绑定规则。
- L4 matched diagnostic 已按生成前预注册完成。Expense pilot 仍为 0/34 步、最长停滞 23，未过 50% 门；OsmAnd confirmation 为 0/49 步并更早虚假声明成功，虽将最长停滞降为 2，仍因预注册禁止“用早停换短轨迹”而判失败。两条均无 L0/L2/L3 污染，干预不扩大。
- 负结果把下一步断点前移：仅纠正“无变化”事实不足以给出恢复策略，也抓不到会产生真实页面变化的错误入口；OsmAnd 最早错误是把普通地点搜索的结果角色错误提交为 waypoint，而不是最后的 Done 循环本身。
