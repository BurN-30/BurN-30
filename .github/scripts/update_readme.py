"""Rewrites the auto-updated sections of README.md from BurN-30's public repositories.

Run by .github/workflows/readme.yml once a day. Standard library only.
Sections live between <!-- building:start --> / <!-- building:end --> and
<!-- releases:start --> / <!-- releases:end -->.
"""
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

USER = "BurN-30"
SKIP = {USER, "dashboard-ratio"}
TOKEN = os.environ.get("GITHUB_TOKEN", "")
README = Path(__file__).resolve().parents[2] / "README.md"


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
    return f"{days // 30} month{'s' if days >= 60 else ''} ago"


repos = [r for r in api(f"/users/{USER}/repos?type=owner&sort=pushed&per_page=100")
         if not r["fork"] and not r["archived"] and not r["private"] and r["name"] not in SKIP]

building = [f"- **[{r['name']}]({r['html_url']})**: {r['description'] or 'no description yet'} "
            f"<sub>(updated {ago(r['pushed_at'])})</sub>" for r in repos[:4]]

releases = []
for r in repos:
    for rel in api(f"/repos/{USER}/{r['name']}/releases?per_page=5"):
        if not rel["draft"] and rel.get("published_at"):
            releases.append((rel["published_at"], r["name"], rel["tag_name"], rel["html_url"]))
            break  # only the latest release of each repo
releases.sort(reverse=True)
release_lines = [f"- [{name} {tag}]({url}) <sub>({ago(date)})</sub>" for date, name, tag, url in releases[:5]]
if not release_lines:
    release_lines = ["- Nothing released yet."]


def replace(text, key, lines):
    pattern = re.compile(rf"(<!-- {key}:start -->).*?(<!-- {key}:end -->)", re.S)
    return pattern.sub(lambda m: m.group(1) + "\n" + "\n".join(lines) + "\n" + m.group(2), text)


text = README.read_text(encoding="utf-8")
new = replace(replace(text, "building", building), "releases", release_lines)
if new != text:
    README.write_text(new, encoding="utf-8")
    print("README updated")
else:
    print("README unchanged")
