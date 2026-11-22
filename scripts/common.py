"""Shared helpers: config, paths and episode state."""
import json
import os
import datetime as dt
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
EPISODES = ROOT / "episodes"
ASSETS = ROOT / "assets"
STATE = ROOT / "state"
BUILD = ROOT / "build"  # temporary files, never committed


def load_config() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def today_id() -> str:
    """Episode id = date in Malaysia time (UTC+8)."""
    now = dt.datetime.utcnow() + dt.timedelta(hours=8)
    return now.strftime("%Y-%m-%d")


def episode_dir(ep_id: str) -> Path:
    d = EPISODES / ep_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def episode_status(ep_id: str) -> dict:
    return read_json(EPISODES / ep_id / "status.json", {})


def set_episode_status(ep_id: str, **fields) -> dict:
    st = episode_status(ep_id)
    st.update(fields)
    st["updated_at"] = dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    write_json(episode_dir(ep_id) / "status.json", st)
    return st


def past_titles(limit: int = 60) -> list[str]:
    titles = []
    if EPISODES.exists():
        for d in sorted(EPISODES.iterdir(), reverse=True):
            s = read_json(d / "script.json")
            if s and s.get("title"):
                titles.append(s["title"])
            if len(titles) >= limit:
                break
    return titles


def env(name: str, required: bool = True) -> str:
    val = os.environ.get(name, "")
    if required and not val:
        raise SystemExit(f"Missing environment variable / GitHub secret: {name}")
    return val
