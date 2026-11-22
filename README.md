# Kids Shorts Factory 🎬

Makes one kids' educational short every day and sends it to you on Telegram.
You tap **✅ Approve** or **🔁 Redo**, and approved videos come back ready to post.

**Daily flow**
1. 06:07 Malaysia time: GitHub writes a script (free GitHub Models), fact-checks it,
   records the voice (Piper, free) and builds a 9:16 video (FFmpeg).
2. The video arrives in Telegram with Approve / Redo buttons.
3. **Approve** → the bot sends the final file + caption to copy.
   **Redo** → reply with a note ("slower", "new topic") and a new version arrives.

Cost: $0 (public repo + free tiers).

---

## One-time setup (about 10 minutes)

### 1. Add your bot token
GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**
- Name: `TELEGRAM_BOT_TOKEN`
- Value: your token from @BotFather (use a fresh one — `/revoke` gives you a new token)

### 2. Get your chat id
1. In Telegram, open your bot and send `/start`.
2. In GitHub, open **Actions → Check Telegram approvals → Run workflow**.
3. The bot replies with your chat id. Add it as a second secret named `TELEGRAM_CHAT_ID`.

### 3. Make your first episode
**Actions → Make daily episode → Run workflow**. In ~5 minutes the video arrives in Telegram.
After that it runs by itself every morning.

---

## Customising

| What | Where |
|---|---|
| Character name, genre, age, catchphrases | `config.yaml` → `show` |
| Voice and speaking speed | `config.yaml` → `voice` ([voices list](https://huggingface.co/rhasspy/piper-voices)) |
| Specific topics in order | `topics.txt` (one per line) |
| Character poses | `assets/poses/` — PNGs with transparent background, named `happy, wave, point, think, wow, cheer` |
| Backgrounds | `assets/backgrounds/` — any 1080×1920 PNG/JPG |
| Background music | `assets/music/` — royalty-free MP3s (optional) |

The current character is a **placeholder**. Export your Canva character poses with the same
file names into `assets/poses/` and every new episode uses them.

**Telegram commands:** `/status` shows the last 7 episodes.

---

## Folders
- `scripts/` — the pipeline (write → voice → render → Telegram)
- `episodes/<date>/` — each day's script and approval status
- `state/` — bot bookkeeping
- `.github/workflows/` — the daily and approval schedules

## Phase 2 (planned)
- Auto-post approved videos to Instagram (free, own account)
- Auto-post to YouTube after the YouTube API review
- TikTok via a posting service
