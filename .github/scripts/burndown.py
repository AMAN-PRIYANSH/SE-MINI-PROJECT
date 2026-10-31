"""Sprint metrics from the GitHub issues of this repository: burndown charts,
a velocity chart, and per-sprint retrospective reports.

Story points come from the "SP: n" label of each backlog issue, the sprint from its
milestone ("Sprint 1 (19-23 Oct)", "Sprint 2 (26-30 Oct)",
"Phase 3 - Testing and Sprint 3 (2-6 Nov)"). An item counts as done on the day its
issue was closed (the PR that "Closes #n" was merged).

usage: python .github/scripts/burndown.py <out_dir>
Needs GITHUB_TOKEN and GITHUB_REPOSITORY (both set inside GitHub Actions).
Writes burndown_<sprint>.png, velocity.png, retrospective_<sprint>.md and
burndown.md (Markdown index with a table per sprint).
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

SPRINTS = {  # sprint name -> (first day, last day); dates from the milestone titles
    "Sprint 1": (dt.date(2026, 10, 19), dt.date(2026, 10, 23)),
    "Sprint 2": (dt.date(2026, 10, 26), dt.date(2026, 10, 30)),
    "Sprint 3": (dt.date(2026, 11, 2), dt.date(2026, 11, 6)),
}

MILESTONE_TO_SPRINT = {
    "Sprint 1": "Sprint 1",
    "Sprint 2": "Sprint 2",
    "Phase 3 - Testing and Sprint 3": "Sprint 3",
}

SP_LABEL = re.compile(r"SP: (\d+)")


def get(path):
    req = urllib.request.Request(f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}/{path}",
                                 headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
                                          "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def in_window(day, sprint):
    first, last = SPRINTS[sprint]
    return first <= day <= last


def backlog():
    """Returns (items, untracked, goals).

    items: backlog issues with a sprint milestone.
    untracked: issues with no milestone created inside a sprint window
        (work merged outside the sprint backlog).
    goals: sprint -> milestone description (the sprint goal).
    """
    items, untracked, goals = [], [], {}
    page = 1
    while True:
        batch = get(f"issues?state=all&per_page=100&page={page}")
        if not batch:
            break
        for it in batch:
            if "pull_request" in it:
                continue
            sp = [int(m.group(1)) for lb in it["labels"] if (m := SP_LABEL.fullmatch(lb["name"]))]
            created = dt.date.fromisoformat(it["created_at"][:10])
            closed = it["closed_at"] and dt.date.fromisoformat(it["closed_at"][:10])
            entry = {"n": it["number"], "title": it["title"], "sp": sp[0] if sp else None,
                     "created": created, "closed": closed, "state": it["state"]}
            ms = it.get("milestone")
            if not ms:
                if any(in_window(created, s) for s in SPRINTS):
                    untracked.append(entry)
                continue
            sprint = MILESTONE_TO_SPRINT.get(ms["title"].split(" (")[0])
            if not sprint:
                continue
            entry["sprint"] = sprint
            goals.setdefault(sprint, ms.get("description") or "")
            items.append(entry)
        page += 1
    return items, untracked, goals


def sprint_status(sprint, today):
    first, last = SPRINTS[sprint]
    if today > last:
        return "done"
    if today < first:
        return "upcoming"
    return "active"


def points(items):
    return sum(i["sp"] or 0 for i in items)


def burndown_data(items, sprint, today):
    first, last = SPRINTS[sprint]
    days = [first + dt.timedelta(d) for d in range((last - first).days + 1)]
    total = points(items)
    ideal = [total - total * k / (len(days) - 1) for k in range(len(days))]
    actual = []
    for d in days:
        if d > today:
            break
        actual.append(total - sum(i["sp"] or 0 for i in items if i["closed"] and i["closed"] <= d))
    return days, total, ideal, actual


def draw_burndown(out_dir, sprint, items, today):
    days, total, ideal, actual = burndown_data(items, sprint, today)
    labels = [d.strftime("%a %d %b") for d in days]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(labels, ideal, "--", color="grey", label="Ideal")
    ax.plot(labels[:len(actual)], actual, "o-", color="tab:blue", label="Actual (remaining)")
    ax.set_title(f"{sprint} burndown ({total} story points, {len(items)} items)")
    ax.set_xlabel("Day of the sprint")
    ax.set_ylabel("Story points remaining")
    ax.set_ylim(0, max(total * 1.05, 1))
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    name = f"burndown_{sprint.lower().replace(' ', '')}.png"
    fig.savefig(os.path.join(out_dir, name), dpi=120)
    plt.close(fig)
    return name, labels, ideal, actual


def draw_velocity(out_dir, items, today):
    sprints = list(SPRINTS)
    committed, completed, labels = [], [], []
    for s in sprints:
        sel = [i for i in items if i["sprint"] == s]
        committed.append(points(sel))
        completed.append(points([i for i in sel if i["closed"]]))
        st = sprint_status(s, today)
        labels.append(s + (" (in progress)" if st == "active" else ""))
    x = list(range(len(sprints)))
    w = 0.35
    fig, ax = plt.subplots(figsize=(8, 4.5))
    b1 = ax.bar([p - w / 2 for p in x], committed, w, color="lightgrey", label="Committed")
    b2 = ax.bar([p + w / 2 for p in x], completed, w, color="tab:blue", label="Completed")
    for bars in (b1, b2):
        for b in bars:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.5, f"{b.get_height():.0f}",
                    ha="center", va="bottom", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_title("Sprint velocity (story points)")
    ax.set_ylabel("Story points")
    ax.set_ylim(0, max(committed + completed + [1]) * 1.15)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "velocity.png"), dpi=120)
    plt.close(fig)
    return list(zip(sprints, committed, completed))


def retrospective(sprint, items, untracked, goals, today):
    """Data-driven retrospective. The qualitative part is a template the team
    fills in during the retro meeting."""
    first, _ = SPRINTS[sprint]
    done = [i for i in items if i["closed"]]
    open_ = [i for i in items if not i["closed"]]
    committed, completed = points(items), points(done)
    pct = f"{100 * completed / committed:.0f}%" if committed else "-"
    added = [i for i in items if i["created"] > first]
    unestimated = [i for i in items if i["sp"] is None]
    window_untracked = [u for u in untracked if in_window(u["created"], sprint)]
    prev = {"Sprint 2": "Sprint 1", "Sprint 3": "Sprint 2"}.get(sprint)

    def fmt(i):
        sp = f"{i['sp']} SP" if i["sp"] is not None else "no estimate"
        extra = f", closed {i['closed']}" if i["closed"] else ""
        return f"- #{i['n']} {i['title']} ({sp}{extra})"

    def n_items(items):
        return f"{len(items)} item" + ("" if len(items) == 1 else "s")

    L = [f"# {sprint} retrospective", "",
         f"_Generated {today} from the GitHub issues. The numbers below are automatic; "
         "the team notes at the end are filled in during the retrospective meeting._", "",
         "## Sprint goal", "", goals.get(sprint, "-"), "",
         "## Numbers", "",
         f"- Committed: {n_items(items)}, {committed} SP",
         f"- Completed: {n_items(done)}, {completed} SP ({pct})",
         f"- Carryover: {n_items(open_)}, {points(open_)} SP",
         f"- Velocity: {completed} SP" + (f" (previous sprint: {prev})" if prev else ""), ""]
    L += ["## Carryover (not finished in this sprint)", ""]
    L += [fmt(i) for i in open_] or ["- None — everything committed was finished."]
    L += ["", "## Added after the sprint started", ""]
    L += [fmt(i) for i in added] or ["- None."]
    L += ["", "## Unestimated items (no `SP: n` label)", ""]
    L += [fmt(i) for i in unestimated] or ["- None — every item was estimated."]
    L += ["", "## Work merged outside the sprint backlog", ""]
    L += [fmt(u) for u in window_untracked] or ["- None."]
    L += ["", "## Team notes (fill in during the retro)", "",
          "### What went well", "", "- ", "",
          "### What to improve", "", "- ", "",
          "### Action items", "", "- [ ] ", ""]
    L += ["---",
          "_Note: \"committed\" is the milestone's current scope. The API does not reveal "
          "scope at sprint-planning time, so items added or removed mid-sprint before "
          "this report ran are counted in \"added after the sprint started\" only if their "
          "issue was created after day one._", ""]
    return "\n".join(L)


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    today = dt.date.today()
    items, untracked, goals = backlog()
    velocity = draw_velocity(out_dir, items, today)

    md = ["# Sprint metrics", "",
          f"Generated {today} from the GitHub issues (story points from the `SP: n` labels).", "",
          "## Velocity", "", "![Sprint velocity](velocity.png)", "",
          "| Sprint | Committed (SP) | Completed (SP) | Completion |",
          "|---|---|---|---|"]
    for s, comm, comp in velocity:
        pct = f"{100 * comp / comm:.0f}%" if comm else "-"
        md.append(f"| {s} | {comm} | {comp} | {pct} |")
    md.append("")

    for sprint in SPRINTS:
        if sprint_status(sprint, today) == "upcoming":
            continue
        sel = [i for i in items if i["sprint"] == sprint]
        name, labels, ideal, actual = draw_burndown(out_dir, sprint, sel, today)
        retro_name = f"retrospective_{sprint.lower().replace(' ', '')}.md"
        with open(os.path.join(out_dir, retro_name), "w", encoding="utf-8") as f:
            f.write(retrospective(sprint, sel, untracked, goals, today))
        first = SPRINTS[sprint][0]
        md += [f"## {sprint}", "", f"![{sprint} burndown]({name})", "",
               f"[Retrospective]({retro_name})", "",
               "| Day | Ideal | Remaining |", "|---|---|---|"]
        for k, lab in enumerate(labels):
            rem = actual[k] if k < len(actual) else "-"
            md.append(f"| {lab} | {ideal[k]:.1f} | {rem} |")
        md.append("")

    with open(os.path.join(out_dir, "burndown.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "burndown")
