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

# 与官方 plugins.json 保持兼容，同时保留 metadata.yaml 中常见的可选展示字段。
OPTIONAL_METADATA_FIELDS = [
    "short_desc",
    "version",
    "astrbot_version",
    "support_platforms",
    "category",
    "updated_at",
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
    return value if isinstance(value, list) else []


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


def fetch_metadata(repo: str, branch: str | None = None) -> dict:
    owner, repo_name = parse_github_repo(repo)
    if not branch:
        branch = get_default_branch(owner, repo_name)

    raw_url = (
        f"https://raw.githubusercontent.com/"
        f"{owner}/{repo_name}/{branch}/metadata.yaml"
    )
    text = request_text(raw_url)
    data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise ValueError("metadata.yaml is not a mapping")
    return data


def normalize_entry(plugin_id: str, base: dict, metadata: dict, fallback_repo: str) -> dict:
    repo = normalize_repo_url(
        fallback_repo
        or base.get("repo")
        or metadata.get("repo")
    )

    entry = {
        "display_name": (
            safe_str(base.get("display_name"))
            or safe_str(metadata.get("display_name"))
            or safe_str(metadata.get("name"))
            or plugin_id
        ),
        "desc": (
            safe_str(base.get("desc"))
            or safe_str(metadata.get("desc"))
            or safe_str(metadata.get("description"))
            or ""
        ),
        "author": (
            safe_str(base.get("author"))
            or safe_str(metadata.get("author"))
            or ""
        ),
        "repo": repo,
        "tags": normalize_tags(base.get("tags") or metadata.get("tags")),
        "social_link": (
            safe_str(base.get("social_link"))
            or safe_str(metadata.get("author_url"))
            or safe_str(metadata.get("social_link"))
            or default_social_link(repo)
        ),
    }

    # 保留官方条目已有的额外字段。
    for key, value in base.items():
        if key not in entry and value not in (None, "", []):
            entry[key] = value

    # 从 metadata.yaml 补充版本、兼容版本、平台等字段。
    for key in OPTIONAL_METADATA_FIELDS:
        value = metadata.get(key)
        if value not in (None, "", []):
            entry[key] = value

    return entry


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
        repo = normalize_repo_url(item.get("repo"))

        if not plugin_id:
            raise ValueError("Each watchlist plugin must contain id")
        if not repo:
            raise ValueError(f"{plugin_id}: missing repo")

        official_entry = official_plugins.get(plugin_id)
        if not isinstance(official_entry, dict):
            official_entry = {}

        try:
            metadata = fetch_metadata(repo, item.get("branch"))
        except Exception as exc:
            metadata = {}
            print(f"WARN metadata failed: {plugin_id}: {exc}", file=sys.stderr)

        result[plugin_id] = normalize_entry(
            plugin_id=plugin_id,
            base=official_entry,
            metadata=metadata,
            fallback_repo=repo,
        )

        source = "official+metadata" if official_entry else "metadata"
        print(f"OK {source}: {plugin_id}")

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
