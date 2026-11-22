"""Write today's episode script with GitHub Models, then fact/safety-check it.

Usage: python scripts/write_script.py [--episode YYYY-MM-DD] [--feedback "text"]
Needs env GITHUB_TOKEN (the workflow's built-in token with `models: read`).
"""
import argparse
import json
import re
import time

import requests

from common import ROOT, episode_dir, load_config, past_titles, today_id, write_json, env, read_json

API = "https://models.github.ai/inference/chat/completions"


def chat(model: str, system: str, user: str, temperature: float = 0.8) -> dict:
    headers = {
        "Authorization": f"Bearer {env('GITHUB_TOKEN')}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    body = {
        "model": model,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    for attempt in range(4):
        r = requests.post(API, headers=headers, json=body, timeout=120)
        if r.status_code == 429:  # free-tier rate limit: wait and retry
            time.sleep(30 * (attempt + 1))
            continue
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"]
        text = re.sub(r"^```(json)?|```$", "", text.strip()).strip()
        return json.loads(text)
    raise SystemExit("GitHub Models rate limit hit repeatedly; try again later.")


def next_topic() -> str | None:
    """Take the first unused line from topics.txt (you can fill it with ideas)."""
    path = ROOT / "topics.txt"
    if not path.exists():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        t = line.strip()
        if t and not t.startswith("#"):
            lines[i] = "# done: " + t
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return t
    return None


def writer_prompt(cfg: dict, topic: str | None, feedback: str | None, issues: list[str]) -> tuple[str, str]:
    show, sc = cfg["show"], cfg["script"]
    system = (
        f"You write scripts for a children's YouTube Shorts / TikTok series for ages {show['audience_age']}. "
        f"The host is {show['character_name']}, {show['character_description']}. "
        "Scripts must be 100% factually correct, gentle, positive, simple words, no scary or unsafe content, "
        "no brand names, no real people, no requests for personal info, no calls to buy anything. "
        "Return ONLY JSON."
    )
    avoid = "; ".join(past_titles()) or "none yet"
    user = f"""Write one episode in {show['language']} about: {topic or 'a fresh topic in the genre: ' + show['genre']}.

Rules:
- {sc['min_lines']} to {sc['max_lines']} lines, each at most {sc['max_words_per_line']} words, about 35-50 seconds total spoken.
- First line must be exactly: "{show['catchphrase_open']}"
- Last line must be exactly: "{show['catchphrase_close']}"
- Line 2 is a hook question that makes kids curious.
- Include one surprising true fact and one tiny question kids can answer out loud.
- Each line gets a pose from: {', '.join(sc['poses'])}.
- Do not repeat these past episodes: {avoid}
{('- The producer rejected the last version. Fix this: ' + feedback) if feedback else ''}
{('- A reviewer found these problems, fix all of them: ' + '; '.join(issues)) if issues else ''}

JSON shape:
{{"title": "short catchy title (max 60 chars, no emoji)",
  "topic": "...",
  "lines": [{{"pose": "wave", "text": "..."}}],
  "description": "1-2 sentence description for the video",
  "hashtags": ["#..."]}}"""
    return system, user


def review(cfg: dict, script: dict) -> list[str]:
    system = (
        "You are a strict children's content reviewer and fact-checker. "
        "Return ONLY JSON: {\"ok\": true/false, \"issues\": [\"...\"]}."
    )
    user = (
        f"Audience age {cfg['show']['audience_age']}. Check this script for: factual errors, anything unsafe or "
        "scary, words too hard for young kids, lines longer than "
        f"{cfg['script']['max_words_per_line']} words, poses not in {cfg['script']['poses']}.\n\n"
        + json.dumps(script, ensure_ascii=False)
    )
    res = chat(cfg["script"]["model"], system, user, temperature=0)
    return [] if res.get("ok") else res.get("issues", ["unspecified problem"])


def validate(cfg: dict, script: dict) -> list[str]:
    problems = []
    poses = set(cfg["script"]["poses"])
    lines = script.get("lines", [])
    if not (cfg["script"]["min_lines"] <= len(lines) <= cfg["script"]["max_lines"] + 1):
        problems.append(f"needs {cfg['script']['min_lines']}-{cfg['script']['max_lines']} lines")
    for ln in lines:
        if ln.get("pose") not in poses:
            ln["pose"] = "happy"  # quietly fix unknown poses
        if not ln.get("text"):
            problems.append("empty line")
    if not script.get("title"):
        problems.append("missing title")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", default=today_id())
    ap.add_argument("--feedback", default="")
    args = ap.parse_args()

    cfg = load_config()
    ep = episode_dir(args.episode)
    old = read_json(ep / "script.json")
    # a remake keeps the same topic unless your note asks for a new one
    if old and "topic" not in args.feedback.lower():
        topic = old.get("topic")
    else:
        topic = next_topic()

    issues: list[str] = []
    for attempt in range(3):
        system, user = writer_prompt(cfg, topic, args.feedback, issues)
        script = chat(cfg["script"]["model"], system, user)
        issues = validate(cfg, script) or review(cfg, script)
        if not issues:
            break
        print(f"Attempt {attempt + 1} had issues: {issues}")
    else:
        raise SystemExit(f"Could not write a clean script: {issues}")

    write_json(ep / "script.json", script)
    print(f"Script ready: {script['title']}")


if __name__ == "__main__":
    main()
