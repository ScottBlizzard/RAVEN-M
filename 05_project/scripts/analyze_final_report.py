"""Assemble the complete Markdown submission from frozen generated evidence."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def csv_markdown(path: Path) -> str:
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.reader(stream))
    if not rows:
        return "_No rows._"
    header = "| " + " | ".join(rows[0]) + " |"
    divider = "|" + "|".join("---" for _ in rows[0]) + "|"
    body = [
        "| " + " | ".join(value.replace("|", "/") for value in row) + " |"
        for row in rows[1:]
    ]
    return "\n".join([header, divider, *body])


def strip_title(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    return "\n".join(lines).lstrip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--generated-dir",
        type=Path,
        default=REPOSITORY_ROOT / "reports/generated",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPOSITORY_ROOT
        / "reports/RAVEN-M_final_experiment_report.md",
    )
    args = parser.parse_args()
    generated = args.generated_dir
    stats = json.loads(
        (generated / "statistics.json").read_text(encoding="utf-8")
    )
    primary = stats["primary_and_secondary_comparisons"][0]
    delta = primary["absolute_tsr_difference"]
    direction = "提升" if delta > 0 else ("下降" if delta < 0 else "持平")
    literature = strip_title(
        (REPOSITORY_ROOT / "reports/literature_review.md").read_text(
            encoding="utf-8"
        )
    )
    method = strip_title(
        (REPOSITORY_ROOT / "reports/method_and_system.md").read_text(
            encoding="utf-8"
        )
    )
    result_text = strip_title(
        (generated / "results_report.md").read_text(encoding="utf-8")
    )
    case_text = strip_title(
        (generated / "case_studies.md").read_text(encoding="utf-8")
    )
    if (
        "pending blinded review" in case_text.lower()
        or "pending_single_reviewer" in case_text
    ):
        raise SystemExit(
            "Case mechanism review is incomplete; final report is blocked."
        )
    report = f"""# RAVEN-M：面向长程 Mobile-use Agent 的可审计记忆管理

## 摘要

本项目基于精确冻结的 Qwen3-VL-32B-Instruct 和 AndroidWorld，构建四类端到端
历史 baseline 与一个 episode-local 多角色记忆原型。方法为每条记忆提供截图/
动作 provenance、验证与失效状态，并以 reliability-aware route 限制陈旧或
矛盾信息。协议在任何 Hard episode 前固定 19 个任务类、三组 task-instance
seed、原生动作预算、8192 context cap、无效重试和 364 个 blocked-order
实验单元。主比较中，M0 相对 B3 的绝对 TSR {direction}
{abs(delta):.4f}，task-clustered 95% bootstrap 区间为
[{primary['cluster_bootstrap95_low']:.4f},
{primary['cluster_bootstrap95_high']:.4f}]。本文同时报告成功率、调用/Token
成本、组件消融、memory harm 与预注册成功/失败案例；不将低功效或零结果包装
成普遍性结论。

## 1. 研究背景与调研

{literature}

## 2. 方法与系统

{method}

## 3. 实验设置

正式实验完全遵循 `04_protocols/experiment_protocol.md` 与
`05_project/metadata/preregistration_v1.json`。Hard 集定义为官方冻结
task-list 中 difficulty=hard 的全部 19 个 task class。B0/B1/B2/B3/M0
完成一组 breadth seed；B0/B3/M0 完成三 seed 确认；S0、六个方法消融以及
B3_CTX/B3_CALL 在预选子集上形成机制与预算控制。所有 agent failure 留在
分母中，evaluator 只在终止后调用。

## 4. 主要结果

{result_text}

### 4.1 成功率与区间

{csv_markdown(generated / 'table_main.csv')}

### 4.2 效率

{csv_markdown(generated / 'table_efficiency.csv')}

## 5. 消融与预算控制

{csv_markdown(generated / 'table_ablation.csv')}

## 6. 错误分布

{csv_markdown(generated / 'table_failure_codes.csv')}

## 7. 预注册案例分析

{case_text}

## 8. 局限与未来工作

本结果只支持冻结模型、AndroidWorld commit 与 task-instance 协议下的结论。
RAVEN-M 不含跨 episode 程序经验、latent memory encoder 或全局 Page Graph；
因此不能代表所有 GUI memory 设计。单次夏令营规模的 19 个 task clusters
统计功效有限，人工 memory audit 也应在条件允许时增加独立第二标注者。
未来可在完全隔离的 Medium development/test 划分上研究跨任务程序经验，
并比较 UI 版本变化下的失效检测，但不能把本轮 Hard 轨迹反向用于调参。

## 9. 复现与提交清单

完整命令见 `reports/reproduction_guide.md`。代码、配置、schema、协议、
preregistration、原始 episode 日志、统计 replicate、表格、图和案例选择规则
均保留；任何无法获取的文献或基础设施失败均显式登记。
"""
    args.output.write_text(report, encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
