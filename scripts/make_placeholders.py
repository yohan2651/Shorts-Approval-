"""Draw a simple placeholder mascot + backgrounds so the pipeline works before the
real Canva character exists. Replace files in assets/poses and assets/backgrounds
with your Canva exports (same file names) whenever you're ready.
"""
import math

from PIL import Image, ImageDraw

from common import ASSETS

BODY = (255, 196, 61)
OUTLINE = (60, 40, 20)
CHEEK = (255, 140, 120)


def arm(d, start, angle_deg, length=210, width=34):
    a = math.radians(angle_deg)
    end = (start[0] + length * math.cos(a), start[1] - length * math.sin(a))
    d.line([start, end], fill=OUTLINE, width=width + 12)
    d.line([start, end], fill=BODY, width=width)
    r = 34
    d.ellipse([end[0] - r, end[1] - r, end[0] + r, end[1] + r], fill=BODY, outline=OUTLINE, width=6)


def mascot(pose: str) -> Image.Image:
    img = Image.new("RGBA", (1000, 1100), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy, r = 500, 600, 320
    arms = {
        "happy": (200, -20), "wave": (200, 60), "point": (200, 10),
        "think": (200, 110), "wow": (150, 30), "cheer": (130, 50),
    }[pose]
    left_angle, right_angle = arms  # degrees: 0 = right, 90 = up, 180 = left
    # arms behind body
    arm(d, (cx - r + 40, cy + 40), left_angle)
    arm(d, (cx + r - 40, cy + 40), right_angle)
    # feet
    for fx in (cx - 140, cx + 140):
        d.ellipse([fx - 90, cy + r - 60, fx + 90, cy + r + 40], fill=BODY, outline=OUTLINE, width=8)
    # body
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BODY, outline=OUTLINE, width=10)
    # explorer hat
    d.polygon([(cx - 230, cy - 250), (cx + 230, cy - 250), (cx + 150, cy - 420), (cx - 150, cy - 420)],
              fill=(46, 139, 87), outline=OUTLINE)
    d.rectangle([cx - 290, cy - 270, cx + 290, cy - 230], fill=(46, 139, 87), outline=OUTLINE, width=6)
    # eyes
    ey = cy - 60
    big = pose in ("wow", "cheer")
    for ex in (cx - 110, cx + 110):
        er = 62 if big else 52
        d.ellipse([ex - er, ey - er, ex + er, ey + er], fill="white", outline=OUTLINE, width=6)
        look = 18 if pose == "point" else (-14 if pose == "think" else 0)
        pr = 28
        d.ellipse([ex - pr + look, ey - pr - (12 if pose == "think" else 0),
                   ex + pr + look, ey + pr - (12 if pose == "think" else 0)], fill=OUTLINE)
        d.ellipse([ex - 8 + look, ey - 18, ex + 6 + look, ey - 4], fill="white")
    # cheeks
    for chx in (cx - 190, cx + 190):
        d.ellipse([chx - 40, cy + 40, chx + 40, cy + 80], fill=CHEEK)
    # mouth
    my = cy + 90
    if pose == "wow":
        d.ellipse([cx - 45, my - 20, cx + 45, my + 70], fill=(150, 40, 40), outline=OUTLINE, width=6)
    elif pose == "think":
        d.line([cx - 50, my + 20, cx + 50, my + 10], fill=OUTLINE, width=12)
    else:
        d.chord([cx - 90, my - 50, cx + 90, my + 90], 0, 180, fill=(150, 40, 40), outline=OUTLINE, width=6)
    return img


def gradient(top, bottom, size=(1080, 1920)) -> Image.Image:
    img = Image.new("RGB", size)
    d = ImageDraw.Draw(img)
    for y in range(size[1]):
        t = y / size[1]
        d.line([(0, y), (size[0], y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
    return img


def backgrounds():
    out = ASSETS / "backgrounds"
    out.mkdir(parents=True, exist_ok=True)
    # sunny meadow
    img = gradient((120, 200, 255), (200, 240, 255))
    d = ImageDraw.Draw(img)
    d.ellipse([780, 620, 1000, 840], fill=(255, 225, 90))
    d.ellipse([-200, 1450, 1300, 2300], fill=(110, 200, 90))
    img.save(out / "meadow.png")
    # ocean
    img = gradient((90, 190, 240), (20, 90, 170))
    d = ImageDraw.Draw(img)
    for i in range(12):
        x = 80 + i * 85
        d.ellipse([x, 1700 - (i % 3) * 40, x + 30, 1730 - (i % 3) * 40], outline="white", width=4)
    d.rectangle([0, 1650, 1080, 1920], fill=(235, 210, 150))
    img.save(out / "ocean.png")
    # night sky
    img = gradient((20, 24, 70), (70, 50, 130))
    d = ImageDraw.Draw(img)
    import random
    rnd = random.Random(7)
    for _ in range(120):
        x, y, s = rnd.randint(0, 1080), rnd.randint(0, 1500), rnd.randint(2, 6)
        d.ellipse([x, y, x + s, y + s], fill="white")
    d.ellipse([-200, 1500, 1300, 2300], fill=(40, 90, 60))
    img.save(out / "night.png")


def main():
    poses = ASSETS / "poses"
    poses.mkdir(parents=True, exist_ok=True)
    for p in ["happy", "wave", "point", "think", "wow", "cheer"]:
        mascot(p).save(poses / f"{p}.png")
    backgrounds()
    print("Placeholder art saved in assets/")


if __name__ == "__main__":
    main()
