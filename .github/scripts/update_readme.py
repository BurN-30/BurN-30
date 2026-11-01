"""Builds the self-updating parts of the profile: project cards, overview card and releases line.

Run daily by .github/workflows/readme.yml. Standard library only, GitHub REST API with GITHUB_TOKEN.
Writes generated/repo-<name>.svg and generated/overview.svg, then rewrites README.md between
<!-- projects:start --> / <!-- projects:end --> and <!-- releases:start --> / <!-- releases:end -->.
"""
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from html import escape
from pathlib import Path

USER = "BurN-30"
SKIP = {USER, "dashboard-ratio"}
CARDS = 4
TOKEN = os.environ.get("GITHUB_TOKEN", "")
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "generated"

# Tokyo Night, matching the rest of the profile
BG, TITLE, TEXT, MUTED, ICON = "#0d1117", "#70a5fd", "#38bdae", "#787c99", "#bf91f3"
FONT = "'Segoe UI', Ubuntu, 'Helvetica Neue', Sans-Serif"
LANG_COLORS = {"Python": "#3572A5", "JavaScript": "#f1e05a", "TypeScript": "#3178c6", "PHP": "#4F5D95",
               "HTML": "#e34c26", "CSS": "#663399", "Lua": "#000080", "C#": "#178600", "GDScript": "#355570",
               "Shell": "#89e051", "Vue": "#41b883", "Svelte": "#ff3e00", "Astro": "#ff5a03"}


def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}", headers={
        "Accept": "application/vnd.github+json", "User-Agent": USER,
        **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def ago(iso):
    days = (datetime.now(timezone.utc) - datetime.fromisoformat(iso.replace("Z", "+00:00"))).days
    if days == 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 30:
        return f"{days} days ago"
    if days < 365:
        return f"{days // 30} month{'s' if days >= 60 else ''} ago"
    return f"{days // 365} year{'s' if days >= 730 else ''} ago"


def wrap(text, width, lines):
    words, out, cur = (text or "No description yet.").split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    out.append(cur)
    if len(out) > lines:
        out = out[:lines]
        out[-1] = out[-1][: width - 1].rstrip() + "…"
    return out


ICON_REPO = ("M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 0 110-1.5h1.75v-2h-8a1 1 0 "
             "00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 012 11.5v-9zm10.5-1V9h-8c-.356 0-.694.074-1 .208V2.5a1 1 0 011-1h8z")
ICON_STAR = ("M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 "
             "01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z")


def repo_card(r):
    lang = r.get("language") or ""
    desc = "".join(f'<tspan x="25" dy="{0 if i == 0 else 18}">{escape(l)}</tspan>'
                   for i, l in enumerate(wrap(r.get("description"), 52, 2)))
    meta_x = 25
    meta = ""
    if lang:
        meta += (f'<circle cx="{meta_x + 6}" cy="96" r="6" fill="{LANG_COLORS.get(lang, MUTED)}"/>'
                 f'<text x="{meta_x + 17}" y="100" class="m">{escape(lang)}</text>')
        meta_x += 30 + 7 * len(lang)
    if r["stargazers_count"]:
        meta += (f'<svg x="{meta_x}" y="88" width="16" height="16" viewBox="0 0 16 16"><path fill="{MUTED}" d="{ICON_STAR}"/></svg>'
                 f'<text x="{meta_x + 21}" y="100" class="m">{r["stargazers_count"]}</text>')
    meta += f'<text x="375" y="100" class="m" text-anchor="end">updated {ago(r["pushed_at"])}</text>'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="120" viewBox="0 0 400 120">
<style>.t{{font:600 16px {FONT};fill:{TITLE}}}.d{{font:400 13px {FONT};fill:{TEXT}}}.m{{font:400 12px {FONT};fill:{MUTED}}}</style>
<rect width="400" height="120" rx="10" fill="{BG}"/>
<svg x="25" y="20" width="16" height="16" viewBox="0 0 16 16"><path fill="{ICON}" d="{ICON_REPO}"/></svg>
<text x="48" y="33" class="t">{escape(r["name"])}</text>
<text x="25" y="58" class="d">{desc}</text>
{meta}
</svg>
'''


def overview_card(rows):
    lines = "".join(
        f'<text x="25" y="{62 + i * 27}" class="l">{escape(k)}</text>'
        f'<text x="375" y="{62 + i * 27}" class="v" text-anchor="end">{escape(str(v))}</text>'
        for i, (k, v) in enumerate(rows))
    h = 50 + 27 * len(rows)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="{h}" viewBox="0 0 400 {h}">
<style>.h{{font:600 18px {FONT};fill:{TITLE}}}.l{{font:400 14px {FONT};fill:{TEXT}}}.v{{font:600 14px {FONT};fill:{ICON}}}</style>
<rect width="400" height="{h}" rx="10" fill="{BG}"/>
<text x="25" y="32" class="h">At a glance</text>
{lines}
</svg>
'''


def replace(text, key, block):
    pattern = re.compile(rf"(<!-- {key}:start -->).*?(<!-- {key}:end -->)", re.S)
    return pattern.sub(lambda m: m.group(1) + "\n" + block + "\n" + m.group(2), text)


def main():
    owned = [r for r in api(f"/users/{USER}/repos?type=owner&sort=pushed&per_page=100") if not r["private"]]
    shown = [r for r in owned if not r["fork"] and not r["archived"] and r["name"] not in SKIP]
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("repo-*.svg"):
        old.unlink()

    cells = []
    for r in shown[:CARDS]:
        (OUT / f"repo-{r['name']}.svg").write_text(repo_card(r), encoding="utf-8")
        cells.append(f'  <a href="{r["html_url"]}"><img src="./generated/repo-{r["name"]}.svg" width="49%" '
                     f'alt="{escape(r["name"])}" /></a>')
    projects = '<p align="center">\n' + "\n".join(cells) + "\n</p>"

    releases = []
    for r in shown:
        for rel in api(f"/repos/{USER}/{r['name']}/releases?per_page=5"):
            if not rel["draft"] and rel.get("published_at"):
                releases.append((rel["published_at"], r["name"], rel["tag_name"], rel["html_url"]))
                break
    releases.sort(reverse=True)
    rel_line = ("<p align=\"center\"><sub>📦 Latest releases: " +
                " · ".join(f'<a href="{u}">{n} {t}</a>' for _, n, t, u in releases[:4]) + "</sub></p>"
                if releases else "")

    user = api(f"/users/{USER}")
    year = datetime.now(timezone.utc).year
    langs = {r["language"] for r in shown if r.get("language")}
    rows = [("Public repositories", user["public_repos"]),
            (f"Side projects updated in {year}", sum(1 for r in shown if r["pushed_at"].startswith(str(year)))),
            ("Projects with a release", len(releases)),
            ("Languages in public code", len(langs)),
            ("Last public push", ago(owned[0]["pushed_at"]) if owned else "n/a")]
    (OUT / "overview.svg").write_text(overview_card(rows), encoding="utf-8")

    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    new = replace(replace(text, "projects", projects), "releases", rel_line)
    readme.write_text(new, encoding="utf-8")
    print("README", "updated" if new != text else "unchanged", "|", len(cells), "cards |", len(releases), "releases")


if __name__ == "__main__":
    main()
