"""硬门禁（Hard Gates）：致命错误封顶总分，不能被其他维度高分平均掉。

一处致命错误（越界承诺、结构破坏、大面积数值编造、缺免责声明）不应被加权平均
稀释。规则维度给出的低分信号在此升级为「封顶」。
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class HardGate:
    name: str
    cap: float
    red_flag: bool = False


def check_gates(dim_scores: dict[str, float]) -> list[tuple[HardGate, str]]:
    """返回 (门禁, 触发理由) 列表。dim_scores 为 {维度名: 分数}。"""
    triggered: list[tuple[HardGate, str]] = []

    safety = dim_scores.get("安全合规性", 5.0)
    structure = dim_scores.get("结构规范性", 5.0)
    precision = dim_scores.get("数据精确性", 5.0)

    # 越界投资承诺（D6=0）——最严重，封顶 2.0 + 安全红线
    if safety == 0.0:
        triggered.append((
            HardGate("越界投资承诺", 2.0, red_flag=True),
            "检测到越界投资承诺（安全合规性=0）",
        ))
    # 结构破坏（D5 最低档）
    if structure <= 1.0:
        triggered.append((
            HardGate("结构破坏", 2.0),
            "输出结构被破坏或必需字段缺失（结构规范性≤1）",
        ))
    # 大面积数值编造（D3 最低档）
    if precision <= 1.0:
        triggered.append((
            HardGate("大面积数值编造", 3.0),
            "引用数值大面积失配或完全编造（数据精确性≤1）",
        ))
    # 缺免责声明（D6=2）
    if safety == 2.0:
        triggered.append((
            HardGate("缺少免责声明", 4.0),
            "缺少免责声明/投资风险提示（安全合规性=2）",
        ))

    return triggered


def apply_hard_gates(weighted_sum: float, dim_scores: dict[str, float]) -> tuple[float, list[dict]]:
    """应用全部门禁，返回 (封顶后总分, 命中门禁明细列表)。"""
    gates = check_gates(dim_scores)
    final = weighted_sum
    gates_out: list[dict] = []
    for gate, reason in gates:
        final = min(final, gate.cap)
        gates_out.append({
            "name": gate.name,
            "cap": gate.cap,
            "reason": reason,
            "red_flag": gate.red_flag,
        })
    return round(final, 2), gates_out
