import json
import os
import re
import sys
import urllib.request
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WATCHLIST = ROOT / "watchlist.json"
OUTPUT = ROOT / "plugins.json"

OFFICIAL_PLUGINS_URL = (
    "https://raw.githubusercontent.com/"
    "AstrBotDevs/AstrBot_Plugins_Collection/main/plugins.json"
)

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()

OFFICIAL_FIELDS = [
    "display_name",
    "desc",
    "author",
    "repo",
    "tags",
    "social_link",
]


def request_text(url: str) -> str:
    headers = {
        "User-Agent": "astrbot-personal-plugin-source",
    }
    if "api.github.com" in url and GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def safe_str(value, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def normalize_repo_url(repo: str) -> str:
    return safe_str(repo).removesuffix(".git")


def parse_github_repo(repo: str) -> tuple[str, str]:
    repo = normalize_repo_url(repo)
    match = re.match(r"^https://github\.com/([^/]+)/([^/]+)$", repo)
    if not match:
        raise ValueError(f"Only GitHub repo URLs are supported: {repo}")
    return match.group(1), match.group(2)


def default_social_link(repo: str) -> str:
    try:
        owner, _ = parse_github_repo(repo)
        return f"https://github.com/{owner}"
    except Exception:
        return ""


def normalize_tags(value) -> list:
    if isinstance(value, list):
        return value
    return []


def normalize_market_entry(entry: dict) -> dict:
    repo = normalize_repo_url(entry.get("repo", ""))

    normalized = {
        "display_name": safe_str(entry.get("display_name")),
        "desc": safe_str(entry.get("desc")),
        "author": safe_str(entry.get("author")),
        "repo": repo,
        "tags": normalize_tags(entry.get("tags")),
        "social_link": safe_str(entry.get("social_link")) or default_social_link(repo),
    }

    return normalized


def load_official_plugins() -> dict:
    text = request_text(OFFICIAL_PLUGINS_URL)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("official plugins.json is not a JSON object")
    return data


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


def build_from_metadata(plugin_id: str, item: dict) -> dict:
    repo = normalize_repo_url(item.get("repo", ""))
    if not repo:
        raise ValueError(f"{plugin_id}: missing repo")

    owner, repo_name = parse_github_repo(repo)
    branch = safe_str(item.get("branch"))

    if not branch:
        branch = get_default_branch(owner, repo_name)

    metadata = fetch_metadata(owner, repo_name, branch)

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

    return {
        "display_name": display_name,
        "desc": desc,
        "author": author,
        "repo": repo,
        "tags": normalize_tags(tags),
        "social_link": safe_str(metadata.get("social_link")) or default_social_link(repo),
    }


def load_watchlist() -> list[dict]:
    data = json.loads(WATCHLIST.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError("watchlist.json must be a JSON object")

    plugins = data.get("plugins")
    if not isinstance(plugins, list):
        raise ValueError("watchlist.json must contain a plugins array")

    return plugins


def build_plugins_json() -> dict:
    official_plugins = load_official_plugins()
    watchlist = load_watchlist()

    result = {}

    for item in watchlist:
        if not isinstance(item, dict):
            raise ValueError("Each watchlist plugin must be an object")

        plugin_id = safe_str(item.get("id"))
        if not plugin_id:
            raise ValueError("Each watchlist plugin must contain id")

        official_entry = official_plugins.get(plugin_id)

        if isinstance(official_entry, dict):
            result[plugin_id] = normalize_market_entry(official_entry)
            print(f"OK official: {plugin_id}")
            continue

        result[plugin_id] = build_from_metadata(plugin_id, item)
        print(f"OK metadata: {plugin_id}")

    if not result:
        raise ValueError("No plugins generated. Check watchlist.json.")

    return result


def main() -> int:
    result = build_plugins_json()

    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Generated {len(result)} plugin(s) into plugins.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
