from __future__ import annotations

from datetime import datetime
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.patches import Patch


def d(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d")


TASKS = [
    ("All members", "Project setup + architecture baseline", "2026-03-08", "2026-03-15", "Completed"),
    ("Ibrahim", "TMDB ingestion + initial dataset", "2026-03-15", "2026-04-05", "In Progress"),
    ("Ibrahim", "MongoDB schema + indexing", "2026-03-15", "2026-03-29", "Completed"),
    ("Ibrahim", "Data cleaning + validation", "2026-03-29", "2026-04-12", "In Progress"),
    ("Ibrahim", "NLP preprocessing pipeline", "2026-03-22", "2026-04-05", "In Progress"),
    ("Ibrahim", "TF-IDF feature extraction + artifacts", "2026-03-29", "2026-04-12", "In Progress"),
    ("Ibrahim", "Similarity index generation", "2026-04-05", "2026-04-19", "In Progress"),
    ("Cenk", "Baseline recommendation", "2026-03-22", "2026-04-05", "Completed"),
    ("Cenk", "Content-based recommendation", "2026-04-05", "2026-04-26", "Completed"),
    ("Cenk", "Hybrid scoring", "2026-04-26", "2026-05-10", "In Progress"),
    ("Yunus", "Backend/API endpoints", "2026-04-05", "2026-04-26", "Completed"),
    ("Yunus", "Frontend/UI development", "2026-03-15", "2026-05-03", "In Progress"),
    ("Yunus", "System integration", "2026-05-03", "2026-05-17", "In Progress"),
    ("Cenk", "Testing + evaluation", "2026-05-03", "2026-05-24", "In Progress"),
    ("Yunus", "Deployment", "2026-05-17", "2026-05-31", "Planned"),
    ("All members", "Final report + presentation", "2026-05-24", "2026-06-14", "Planned"),
]


COLORS = {
    "Completed": "#2E7D32",
    "In Progress": "#F9A825",
    "Planned": "#1976D2",
    "Delayed": "#C62828",
}


def main() -> None:
    out = Path("artifacts/midterm_updated_gantt_with_owners.png")
    out.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(13, 8))

    y_positions = list(range(len(TASKS)))
    for y, (owner, name, start, end, status) in zip(y_positions, TASKS):
        start_dt = d(start)
        end_dt = d(end)
        ax.barh(
            y,
            (end_dt - start_dt).days,
            left=mdates.date2num(start_dt),
            height=0.56,
            color=COLORS[status],
            edgecolor="#263238",
            linewidth=0.8,
        )

    ax.set_yticks(y_positions)
    ax.set_yticklabels([f"{task[0]}: {task[1]}" for task in TASKS], fontsize=8.5)
    ax.invert_yaxis()

    ax.set_xlim(d("2026-03-08"), d("2026-06-14"))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=mdates.SU, interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.grid(axis="x", color="#B0BEC5", linewidth=0.7, alpha=0.8)
    ax.set_axisbelow(True)

    ax.set_title(
        "Updated Gantt Chart for Midterm Progress Report",
        fontsize=15,
        fontweight="bold",
        pad=18,
    )
    ax.set_xlabel("Spring 2026 Timeline", fontsize=10)

    legend_items = [
        Patch(facecolor=COLORS["Completed"], edgecolor="#263238", label="Completed"),
        Patch(facecolor=COLORS["In Progress"], edgecolor="#263238", label="In Progress"),
        Patch(facecolor=COLORS["Planned"], edgecolor="#263238", label="Planned"),
        Patch(facecolor=COLORS["Delayed"], edgecolor="#263238", label="Delayed"),
    ]
    ax.legend(
        handles=legend_items,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.16),
        ncol=4,
        frameon=False,
    )

    ax.text(
        0,
        -0.22,
        "Note: No task is currently marked as delayed. Remaining evaluation, UAT, deployment, and final reporting tasks are scheduled for the second half of the term.",
        transform=ax.transAxes,
        fontsize=9,
        color="#455A64",
    )

    plt.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(out, dpi=220, bbox_inches="tight")
    print(out.resolve())


if __name__ == "__main__":
    main()
