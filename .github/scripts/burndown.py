"""Sprint burndown charts from the GitHub issues of this repository.

Story points come from the "SP: n" label of each backlog issue, the sprint from its
milestone ("Sprint 1 (19-23 Oct)", "Sprint 2 (26-30 Oct)"). An item counts as done on
the day its issue was closed (the PR that "Closes #n" was merged).

usage: python .github/scripts/burndown.py <out_dir>
Needs GITHUB_TOKEN and GITHUB_REPOSITORY (both set inside GitHub Actions).
Writes burndown_<sprint>.png and burndown.md (Markdown with a table per sprint).
"""
import datetime as dt
import json
import os
import re
import sys
import urllib.request

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SPRINTS = {  # sprint name -> (first day, last day) from docs/SPRINT_PLAN.md
    "Sprint 1": (dt.date(2026, 10, 19), dt.date(2026, 10, 23)),
    "Sprint 2": (dt.date(2026, 10, 26), dt.date(2026, 10, 30)),
}


def get(path):
    req = urllib.request.Request(f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}/{path}",
                                 headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
                                          "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def backlog():
    items, page = [], 1
    while True:
        batch = get(f"issues?state=all&per_page=100&page={page}")
        if not batch:
            return items
        for it in batch:
            if "pull_request" in it or not it.get("milestone"):
                continue
            sp = [int(m.group(1)) for lb in it["labels"] if (m := re.fullmatch(r"SP: (\d+)", lb["name"]))]
            sprint = it["milestone"]["title"].split(" (")[0]
            if sp and sprint in SPRINTS:
                closed = it["closed_at"] and dt.date.fromisoformat(it["closed_at"][:10])
                items.append({"n": it["number"], "sprint": sprint, "sp": sp[0], "closed": closed})
        page += 1


def burndown(items, sprint):
    first, last = SPRINTS[sprint]
    days = [first + dt.timedelta(d) for d in range((last - first).days + 1)]
    total = sum(i["sp"] for i in items)
    today = dt.date.today()
    ideal = [total - total * k / (len(days) - 1) for k in range(len(days))]
    actual = []
    for d in days:
        if d > today:
            break
        actual.append(total - sum(i["sp"] for i in items if i["closed"] and i["closed"] <= d))
    return days, total, ideal, actual


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    items = backlog()
    md = ["# Sprint burndown", "",
          f"Generated {dt.date.today()} from the GitHub issues (story points from the `SP: n` labels).", ""]
    for sprint in SPRINTS:
        sel = [i for i in items if i["sprint"] == sprint]
        days, total, ideal, actual = burndown(sel, sprint)
        labels = [d.strftime("%a %d %b") for d in days]
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.plot(labels, ideal, "--", color="grey", label="Ideal")
        ax.plot(labels[:len(actual)], actual, "o-", color="tab:blue", label="Actual (remaining)")
        ax.set_title(f"{sprint} burndown ({total} story points, {len(sel)} items)")
        ax.set_xlabel("Day of the sprint")
        ax.set_ylabel("Story points remaining")
        ax.set_ylim(0, total * 1.05)
        ax.grid(alpha=0.3)
        ax.legend()
        fig.tight_layout()
        name = f"burndown_{sprint.lower().replace(' ', '')}.png"
        fig.savefig(os.path.join(out_dir, name), dpi=120)
        plt.close(fig)
        md += [f"## {sprint}", "", f"![{sprint} burndown]({name})", "", "| Day | Ideal | Remaining |", "|---|---|---|"]
        for k, d in enumerate(days):
            rem = actual[k] if k < len(actual) else "-"
            md.append(f"| {labels[k]} | {ideal[k]:.1f} | {rem} |")
        md.append("")
    with open(os.path.join(out_dir, "burndown.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "burndown")
