"""生成各维度得分箱线图（good/medium/bad 三档对比）。"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

# 配置 CJK 字体，避免中文显示为方块
from matplotlib import font_manager

_CJK_CANDIDATES = [
    "PingFang SC", "Hiragino Sans GB", "STHeiti", "Heiti SC",
    "Arial Unicode MS", "Songti SC", "Noto Sans CJK SC",
]
_available = {f.name for f in font_manager.fontManager.ttflist}
for _f in _CJK_CANDIDATES:
    if _f in _available:
        plt.rcParams["font.sans-serif"] = [_f, "DejaVu Sans"]
        plt.rcParams["axes.unicode_minus"] = False
        break

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"

DIMENSIONS = [
    "事实准确性", "证据可追溯性", "数据精确性",
    "信息完整性", "结构规范性", "安全合规性", "专业术语正确性", "总分",
]
LEVELS = ["good", "medium", "bad"]
LEVEL_LABELS = {"good": "好", "medium": "中", "bad": "差"}
COLORS = {"good": "#2e7d32", "medium": "#f9a825", "bad": "#c62828"}


def main():
    df = pd.read_csv(RESULTS_DIR / "eval_table.csv")
    sub = df[df["quality_level"].isin(LEVELS)]

    fig, axes = plt.subplots(2, 4, figsize=(16, 8))
    axes = axes.flatten()

    for i, dim in enumerate(DIMENSIONS):
        ax = axes[i]
        data = [sub[sub["quality_level"] == lv][dim].dropna() for lv in LEVELS]
        bp = ax.boxplot(
            data,
            labels=[LEVEL_LABELS[lv] for lv in LEVELS],
            patch_artist=True,
            showmeans=True,
        )
        for patch, lv in zip(bp["boxes"], LEVELS):
            patch.set_facecolor(COLORS[lv])
            patch.set_alpha(0.7)
        for median in bp["medians"]:
            median.set_color("black")
            median.set_linewidth(1.5)
        ax.set_title(dim, fontsize=12)
        ax.set_ylim(-0.3, 5.3)
        ax.grid(axis="y", alpha=0.3)

    # 隐藏多余的第 8 个子图（2x4 恰好 8 个维度，无需隐藏）
    fig.suptitle("七维度评测得分箱线图（好 / 中 / 差）", fontsize=16, y=1.02)
    fig.tight_layout()

    out = RESULTS_DIR / "boxplot.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"箱线图已保存至: {out}")


if __name__ == "__main__":
    main()
