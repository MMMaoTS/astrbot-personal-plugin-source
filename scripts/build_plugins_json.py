import json
import os
import re
import sys
import urllib.request
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WATCHLIST = ROOT / "watchlist.json"
SITE_DIR = ROOT / "site"
OUTPUT = SITE_DIR / "plugins.json"

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()


def request_text(url: str) -> str:
    headers = {
        "User-Agent": "astrbot-personal-plugin-source",
        "Accept": "application/vnd.github+json",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def normalize_repo_url(repo: str) -> str:
    return repo.strip().removesuffix(".git")


def parse_github_repo(repo: str) -> tuple[str, str]:
    repo = normalize_repo_url(repo)
    match = re.match(r"^https://github\.com/([^/]+)/([^/]+)$", repo)
    if not match:
        raise ValueError(f"Only GitHub repo URLs are supported: {repo}")
    return match.group(1), match.group(2)


def get_default_branch(owner: str, name: str) -> str:
    api_url = f"https://api.github.com/repos/{owner}/{name}"
    data = json.loads(request_text(api_url))
    return data.get("default_branch") or "main"


def fetch_metadata(owner: str, name: str, branch: str) -> dict:
    raw_url = (
        f"https://raw.githubusercontent.com/"
        f"{owner}/{name}/{branch}/metadata.yaml"
    )
    text = request_text(raw_url)
    data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise ValueError("metadata.yaml is not a mapping")
    return data


def safe_str(value, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def build_entry(item: dict) -> tuple[str, dict]:
    repo = normalize_repo_url(item["repo"])
    owner, repo_name = parse_github_repo(repo)
    branch = safe_str(item.get("branch")) or get_default_branch(owner, repo_name)

    metadata = fetch_metadata(owner, repo_name, branch)

    plugin_id = (
        safe_str(item.get("id"))
        or safe_str(metadata.get("name"))
        or repo_name
    )

    display_name = (
        safe_str(metadata.get("display_name"))
        or safe_str(metadata.get("name"))
        or plugin_id
    )

    desc = (
        safe_str(metadata.get("desc"))
        or safe_str(metadata.get("description"))
        or safe_str(metadata.get("short_desc"))
        or ""
    )

    author = safe_str(metadata.get("author")) or owner

    tags = item.get("tags", metadata.get("tags", []))
    if not isinstance(tags, list):
        tags = []

    social_link = (
        safe_str(item.get("social_link"))
        or safe_str(metadata.get("social_link"))
        or f"https://github.com/{owner}"
    )

    entry = {
        "display_name": display_name,
        "desc": desc,
        "author": author,
        "repo": repo,
        "tags": tags,
        "social_link": social_link,
    }

    return plugin_id, entry


def main() -> int:
    watch = json.loads(WATCHLIST.read_text(encoding="utf-8"))
    plugins = watch.get("plugins", [])

    if not isinstance(plugins, list):
        raise ValueError("watchlist.json: plugins must be a list")

    SITE_DIR.mkdir(parents=True, exist_ok=True)

    result = {}
    errors = []

    for item in plugins:
        try:
            plugin_id, entry = build_entry(item)
            result[plugin_id] = entry
            print(f"OK: {plugin_id}")
        except Exception as exc:
            repo = item.get("repo", "<unknown>")
            errors.append(f"{repo}: {exc}")
            print(f"ERROR: {repo}: {exc}", file=sys.stderr)

    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    index = SITE_DIR / "index.html"
    index.write_text(
        "<!doctype html><meta charset='utf-8'>"
        "<title>AstrBot Personal Plugin Source</title>"
        "<p>AstrBot personal plugin source is running.</p>"
        "<p>Use <a href='./plugins.json'>plugins.json</a>.</p>",
        encoding="utf-8",
    )

    if errors:
        print("\nSome plugins failed:", file=sys.stderr)
        for err in errors:
            print(f"- {err}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
