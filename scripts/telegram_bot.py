"""Telegram approval bot.

  python scripts/telegram_bot.py send  --episode YYYY-MM-DD   # send preview with Approve / Redo buttons
  python scripts/telegram_bot.py check                        # read your button taps and replies

Secrets: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (the bot tells you your chat id if this is empty).
`check` prints redo jobs to $GITHUB_OUTPUT so the workflow can remake those episodes.
"""
import argparse
import json
import os

import requests

from common import BUILD, EPISODES, STATE, episode_status, load_config, read_json, set_episode_status, today_id, write_json, env


def api(method: str, files=None, **params):
    url = f"https://api.telegram.org/bot{env('TELEGRAM_BOT_TOKEN')}/{method}"
    if files:
        r = requests.post(url, data=params, files=files, timeout=300)
    else:
        r = requests.post(url, json=params, timeout=60)
    data = r.json()
    if not data.get("ok"):
        raise SystemExit(f"Telegram {method} failed: {data}")
    return data["result"]


def owner_id() -> str:
    return os.environ.get("TELEGRAM_CHAT_ID", "").strip()


def post_text(script: dict, cfg: dict) -> str:
    tags = script.get("hashtags", []) + cfg["posting"].get("hashtags_default", [])
    seen, uniq = set(), []
    for t in tags:
        t = t if t.startswith("#") else "#" + t
        if t.lower() not in seen:
            seen.add(t.lower())
            uniq.append(t)
    return f"{script['title']}\n\n{script.get('description', '')}\n\n{' '.join(uniq[:8])}"


# ------------------------------------------------------------------ send
def send(ep: str) -> None:
    chat = owner_id() or None
    if not chat:
        raise SystemExit("TELEGRAM_CHAT_ID is empty. Message your bot /start, wait for the approvals "
                         "workflow to reply with your chat id, then add it as a GitHub secret.")
    script = read_json(EPISODES / ep / "script.json")
    video = BUILD / ep / "final.mp4"
    st = episode_status(ep)
    attempt = int(st.get("attempt", 0)) + 1
    lines = "\n".join(f"• {l['text']}" for l in script["lines"])
    caption = (f"🎬 New episode ({ep}, version {attempt})\n<b>{script['title']}</b>\n\n{lines}")[:1000]
    keyboard = {"inline_keyboard": [[
        {"text": "✅ Approve", "callback_data": f"approve:{ep}"},
        {"text": "🔁 Redo", "callback_data": f"redo:{ep}"},
    ]]}
    with open(video, "rb") as f:
        msg = api("sendVideo", files={"video": f}, chat_id=chat, caption=caption, parse_mode="HTML",
                  supports_streaming="true", reply_markup=json.dumps(keyboard))
    set_episode_status(ep, status="pending", attempt=attempt, message_id=msg["message_id"],
                       file_id=msg["video"]["file_id"])
    print("Preview sent to Telegram")


# ------------------------------------------------------------------ check
def approve(ep: str, chat: str, cfg: dict) -> None:
    st = episode_status(ep)
    if st.get("status") == "approved":
        return
    script = read_json(EPISODES / ep / "script.json")
    set_episode_status(ep, status="approved")
    api("sendVideo", chat_id=chat, video=st["file_id"], supports_streaming=True,
        caption="✅ Approved! Save this video and post it.\nCaption to copy is below 👇")
    api("sendMessage", chat_id=chat, text=post_text(script, cfg))
    # Phase 2: auto-post to Instagram / YouTube here.


def ask_feedback(ep: str, chat: str) -> None:
    set_episode_status(ep, status="awaiting_feedback")
    api("sendMessage", chat_id=chat,
        text=f"🔁 What should I change for {ep}? Reply with a short note "
             "(e.g. 'slower', 'different topic', 'simpler words'), or reply 'skip' to just try again.")


def check() -> None:
    cfg = load_config()
    offset_file = STATE / "telegram_offset.json"
    offset = read_json(offset_file, {"offset": 0})["offset"]
    updates = api("getUpdates", offset=offset, timeout=0,
                  allowed_updates=["message", "callback_query"])
    me = owner_id()
    redo_jobs = []

    for u in updates:
        offset = u["update_id"] + 1
        if "callback_query" in u:
            cq = u["callback_query"]
            chat = str(cq["message"]["chat"]["id"])
            if chat != me:
                continue
            action, _, ep = cq.get("data", "").partition(":")
            api("answerCallbackQuery", callback_query_id=cq["id"])
            try:  # remove buttons so they can't be tapped twice
                api("editMessageReplyMarkup", chat_id=chat, message_id=cq["message"]["message_id"],
                    reply_markup={"inline_keyboard": []})
            except SystemExit:
                pass
            if action == "approve":
                approve(ep, chat, cfg)
            elif action == "redo":
                ask_feedback(ep, chat)
        elif "message" in u:
            m = u["message"]
            chat = str(m["chat"]["id"])
            text = (m.get("text") or "").strip()
            if not me:
                if text.startswith("/start"):
                    api("sendMessage", chat_id=chat,
                        text=f"👋 Your chat id is {chat}\nAdd it in GitHub → Settings → Secrets → Actions "
                             "as TELEGRAM_CHAT_ID.")
                continue
            if chat != me or not text:
                continue
            waiting = [d.name for d in sorted(EPISODES.iterdir())
                       if episode_status(d.name).get("status") == "awaiting_feedback"] if EPISODES.exists() else []
            if waiting:
                ep = waiting[-1]
                note = "" if text.lower() == "skip" else text
                set_episode_status(ep, status="redo_requested", feedback=note)
                api("sendMessage", chat_id=chat, text=f"👍 Got it — remaking {ep}. New version in a few minutes.")
                redo_jobs.append({"episode": ep, "feedback": note})
            elif text.startswith("/status"):
                rows = []
                if EPISODES.exists():
                    for d in sorted(EPISODES.iterdir())[-7:]:
                        rows.append(f"{d.name}: {episode_status(d.name).get('status', '?')}")
                api("sendMessage", chat_id=chat, text="\n".join(rows) or "No episodes yet.")

    write_json(offset_file, {"offset": offset})
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"redo={json.dumps(redo_jobs)}\n")
    print(f"Processed {len(updates)} updates, {len(redo_jobs)} redo jobs")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["send", "check"])
    ap.add_argument("--episode", default=today_id())
    args = ap.parse_args()
    send(args.episode) if args.command == "send" else check()


if __name__ == "__main__":
    main()
