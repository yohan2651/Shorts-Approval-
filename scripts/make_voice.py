"""Turn each script line into speech with Piper (free, open-source, runs on the GitHub runner).

Usage: python scripts/make_voice.py [--episode YYYY-MM-DD]
Output: build/<episode>/line_XX.wav and build/<episode>/timing.json
"""
import argparse
import subprocess
import wave
from pathlib import Path

import requests

from common import BUILD, EPISODES, load_config, read_json, today_id, write_json

VOICE_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"


def voice_files(name: str) -> Path:
    """Download the Piper voice once (cached by the workflow)."""
    lang_region, speaker, quality = name.split("-")
    lang = lang_region.split("_")[0]
    folder = BUILD / "voices"
    folder.mkdir(parents=True, exist_ok=True)
    model = folder / f"{name}.onnx"
    for suffix in (".onnx", ".onnx.json"):
        target = folder / f"{name}{suffix}"
        if not target.exists():
            url = f"{VOICE_BASE}/{lang}/{lang_region}/{speaker}/{quality}/{name}{suffix}"
            print("Downloading", url)
            r = requests.get(url, timeout=300)
            r.raise_for_status()
            target.write_bytes(r.content)
    return model


def synth(voice, text: str, out: Path) -> None:
    with wave.open(str(out), "wb") as wf:
        if hasattr(voice, "synthesize_wav"):
            voice.synthesize_wav(text, wf)
        else:  # older piper-tts
            voice.synthesize(text, wf)


def duration(path: Path) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)]
    )
    return float(out.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", default=today_id())
    args = ap.parse_args()

    from piper import PiperVoice

    cfg = load_config()
    script = read_json(EPISODES / args.episode / "script.json")
    if not script:
        raise SystemExit("No script.json for this episode — run write_script.py first.")

    voice = PiperVoice.load(str(voice_files(cfg["voice"]["piper_voice"])))
    out_dir = BUILD / args.episode
    out_dir.mkdir(parents=True, exist_ok=True)
    speed = float(cfg["voice"].get("speed", 1.0))
    pause = float(cfg["voice"].get("pause_after_line", 0.35))

    timing = []
    for i, line in enumerate(script["lines"]):
        raw = out_dir / f"raw_{i:02d}.wav"
        final = out_dir / f"line_{i:02d}.wav"
        synth(voice, line["text"], raw)
        # slow down slightly + add a short pause at the end
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw),
             "-af", f"atempo={speed},apad=pad_dur={pause}", "-ar", "44100", "-ac", "2", str(final)],
            check=True,
        )
        timing.append({"file": final.name, "pose": line["pose"], "text": line["text"],
                       "duration": duration(final)})

    write_json(out_dir / "timing.json", timing)
    print(f"Voice ready: {len(timing)} lines, {sum(t['duration'] for t in timing):.1f}s")


if __name__ == "__main__":
    main()
