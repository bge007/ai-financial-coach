"""Server-side chart rendering for PDF reports (matplotlib)."""

from __future__ import annotations

from io import BytesIO
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

PRIMARY = "#0A2E5C"
GOLD = "#D4AF37"
INCOME = "#2E7D4F"
EXPENSE = "#C0392B"
MUTED = "#6B7280"
PALETTE = ["#0A2E5C", "#D4AF37", "#2E7D4F", "#5B7FA6", "#C0392B", "#8B5CF6"]


def _save_fig(fig: plt.Figure) -> bytes:
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return buf.getvalue()


def _style_axes(ax: plt.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.title.set_color(PRIMARY)


def chart_income_expense_trend(
    labels: list[str],
    income: list[float],
    expenses: list[float],
    *,
    title: str = "Income vs expenses",
) -> bytes:
    x = np.arange(len(labels))
    width = 0.38
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    ax.bar(x - width / 2, income, width, label="Income", color=INCOME, alpha=0.9)
    ax.bar(x + width / 2, expenses, width, label="Expenses", color=EXPENSE, alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
    ax.set_ylabel("Amount (Rs.)", fontsize=8, color=MUTED)
    ax.set_title(title, fontsize=10, fontweight="bold", pad=10)
    ax.legend(fontsize=7, frameon=False)
    _style_axes(ax)
    fig.tight_layout()
    return _save_fig(fig)


def chart_grouped_bar(
    categories: list[str],
    series: dict[str, list[float]],
    *,
    title: str,
    ylabel: str = "Amount (Rs.)",
) -> bytes:
    x = np.arange(len(categories))
    n = max(len(series), 1)
    width = 0.8 / n
    fig, ax = plt.subplots(figsize=(5.5, 3.2))
    for i, (name, values) in enumerate(series.items()):
        offset = (i - (n - 1) / 2) * width
        color = PALETTE[i % len(PALETTE)]
        ax.bar(x + offset, values, width, label=name, color=color, alpha=0.9)
    ax.set_xticks(x)
    ax.set_xticklabels([c.title() for c in categories], fontsize=8)
    ax.set_ylabel(ylabel, fontsize=8, color=MUTED)
    ax.set_title(title, fontsize=10, fontweight="bold", pad=10)
    ax.legend(fontsize=7, frameon=False)
    _style_axes(ax)
    fig.tight_layout()
    return _save_fig(fig)


def chart_horizontal_bar(
    labels: list[str],
    values: list[float],
    *,
    title: str,
) -> bytes:
    fig, ax = plt.subplots(figsize=(7.2, max(2.8, 0.35 * len(labels) + 1.2)))
    y = np.arange(len(labels))
    colors = [PALETTE[i % len(PALETTE)] for i in range(len(labels))]
    ax.barh(y, values, color=colors, alpha=0.88)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("Amount (Rs.)", fontsize=8, color=MUTED)
    ax.set_title(title, fontsize=10, fontweight="bold", pad=10)
    _style_axes(ax)
    fig.tight_layout()
    return _save_fig(fig)


def chart_pie(
    labels: list[str],
    values: list[float],
    *,
    title: str,
) -> bytes:
    fig, ax = plt.subplots(figsize=(4.8, 3.6))
    total = sum(values) or 1.0
    pct = [v / total * 100 for v in values]
    colors = [PALETTE[i % len(PALETTE)] for i in range(len(labels))]
    wedges, texts, autotexts = ax.pie(
        values,
        labels=[f"{lbl.title()}" for lbl in labels],
        autopct=lambda p: f"{p:.0f}%" if p >= 4 else "",
        colors=colors,
        startangle=90,
        textprops={"fontsize": 7},
    )
    for t in autotexts:
        t.set_fontsize(7)
        t.set_color("white")
        t.set_fontweight("bold")
    ax.set_title(title, fontsize=10, fontweight="bold", color=PRIMARY, pad=10)
    fig.tight_layout()
    return _save_fig(fig)


def chart_line(
    x_labels: list[Any],
    series: dict[str, list[float]],
    *,
    title: str,
    xlabel: str = "",
    ylabel: str = "Amount (Rs.)",
) -> bytes:
    fig, ax = plt.subplots(figsize=(6.8, 3.4))
    for i, (name, ys) in enumerate(series.items()):
        ax.plot(
            range(len(x_labels)),
            ys,
            marker="o",
            markersize=3,
            linewidth=1.8,
            label=name,
            color=PALETTE[i % len(PALETTE)],
        )
    ax.set_xticks(range(len(x_labels)))
    ax.set_xticklabels([str(x) for x in x_labels], fontsize=7)
    ax.set_xlabel(xlabel, fontsize=8, color=MUTED)
    ax.set_ylabel(ylabel, fontsize=8, color=MUTED)
    ax.set_title(title, fontsize=10, fontweight="bold", pad=10)
    if len(series) > 1:
        ax.legend(fontsize=7, frameon=False)
    _style_axes(ax)
    fig.tight_layout()
    return _save_fig(fig)


def chart_scatter_line(
    volatility: list[float],
    returns: list[float],
    *,
    title: str,
    highlight: tuple[float, float] | None = None,
) -> bytes:
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    vol_pct = [v * 100 for v in volatility]
    ret_pct = [r * 100 for r in returns]
    ax.plot(vol_pct, ret_pct, "o-", color=PRIMARY, markersize=5, linewidth=1.5, label="Frontier")
    if highlight:
        ax.scatter(
            [highlight[0] * 100],
            [highlight[1] * 100],
            s=80,
            color=GOLD,
            edgecolors=PRIMARY,
            linewidths=1.2,
            zorder=5,
            label="Max Sharpe",
        )
    ax.set_xlabel("Volatility (%)", fontsize=8, color=MUTED)
    ax.set_ylabel("Expected return (%)", fontsize=8, color=MUTED)
    ax.set_title(title, fontsize=10, fontweight="bold", pad=10)
    ax.legend(fontsize=7, frameon=False)
    _style_axes(ax)
    fig.tight_layout()
    return _save_fig(fig)


def chart_tax_comparison(old_tax: float, new_tax: float, *, title: str) -> bytes:
    return chart_grouped_bar(
        ["Old regime", "New regime"],
        {"Total tax": [old_tax, new_tax]},
        title=title,
        ylabel="Tax (Rs.)",
    )
