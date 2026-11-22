"""Build the vertical 9:16 video with FFmpeg from poses, background, voice and captions.

Usage: python scripts/render_video.py [--episode YYYY-MM-DD]
Output: build/<episode>/final.mp4
"""
import argparse
import hashlib
import random
import subprocess
import textwrap
from pathlib import Path

from common import ASSETS, BUILD, EPISODES, load_config, read_json, today_id


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def pick(folder: Path, exts: tuple[str, ...], seed: str) -> Path | None:
    files = sorted(p for p in folder.glob("*") if p.suffix.lower() in exts) if folder.exists() else []
    if not files:
        return None
    return random.Random(seed).choice(files)


def pose_image(name: str) -> Path:
    p = ASSETS / "poses" / f"{name}.png"
    return p if p.exists() else ASSETS / "poses" / "happy.png"


def segment(cfg: dict, bg: Path, pose: Path, audio: Path, caption_file: Path,
            title_file: Path, dur: float, out: Path) -> None:
    v = cfg["video"]
    W, H, font = v["width"], v["height"], v["font"]
    filters = (
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1[bg];"
        f"[1:v]scale=-1:950[p];"
        # character gently bobs up and down so it feels alive
        f"[bg][p]overlay=x=(W-w)/2:y=H-h-70+14*sin(2*PI*t*1.6):shortest=0[v1];"
        f"[v1]drawtext=fontfile={font}:textfile={title_file}:fontsize={v['title_size']}:"
        f"fontcolor=white:box=1:boxcolor=0xFF7A00@0.95:boxborderw=24:x=(w-text_w)/2:y=140[v2];"
        f"[v2]drawtext=fontfile={font}:textfile={caption_file}:fontsize={v['caption_size']}:"
        f"fontcolor=0x222222:line_spacing=14:box=1:boxcolor=white@0.92:boxborderw=34:"
        f"x=(w-text_w)/2:y=360[v]"
    )
    run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-i", str(bg),
        "-loop", "1", "-i", str(pose),
        "-i", str(audio),
        "-filter_complex", filters,
        "-map", "[v]", "-map", "2:a",
        "-t", f"{dur:.3f}", "-r", str(v["fps"]),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
        str(out),
    ])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", default=today_id())
    args = ap.parse_args()

    cfg = load_config()
    script = read_json(EPISODES / args.episode / "script.json")
    work = BUILD / args.episode
    timing = read_json(work / "timing.json")
    if not script or not timing:
        raise SystemExit("Missing script.json or timing.json — run the earlier steps first.")

    seed = hashlib.md5(args.episode.encode()).hexdigest()
    bg = pick(ASSETS / "backgrounds", (".png", ".jpg", ".jpeg"), seed)
    if not bg:
        raise SystemExit("No backgrounds in assets/backgrounds — run scripts/make_placeholders.py")

    title_file = work / "title.txt"
    title_file.write_text(textwrap.fill(script["title"], 26), encoding="utf-8")

    parts = []
    for i, t in enumerate(timing):
        cap = work / f"cap_{i:02d}.txt"
        cap.write_text(textwrap.fill(t["text"], 20), encoding="utf-8")
        seg = work / f"seg_{i:02d}.mp4"
        segment(cfg, bg, pose_image(t["pose"]), work / t["file"], cap, title_file, t["duration"], seg)
        parts.append(seg)

    listing = work / "parts.txt"
    listing.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
    joined = work / "joined.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(listing), "-c", "copy", str(joined)])

    final = work / "final.mp4"
    music = pick(ASSETS / "music", (".mp3", ".wav", ".m4a", ".ogg"), seed)
    vol = float(cfg["video"].get("music_volume", 0))
    if music and vol > 0:
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(joined),
             "-stream_loop", "-1", "-i", str(music),
             "-filter_complex",
             f"[1:a]volume={vol}[m];[0:a][m]amix=inputs=2:duration=first:normalize=0[a]",
             "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
             "-movflags", "+faststart", str(final)])
    else:
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(joined), "-c", "copy",
             "-movflags", "+faststart", str(final)])
    print("Video ready:", final)


if __name__ == "__main__":
    main()
