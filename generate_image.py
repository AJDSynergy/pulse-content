#!/usr/bin/env python3
"""
The Pulse — Daily Image Generator
Synergy Fundraising

Reads content.json, finds today's tip, generates a 480x272 JPEG
ready for the ESP32 display to download and show.

Runs via GitHub Actions daily at midnight AEST.
Output: display.jpg (saved to repo root)
"""

import json
import sys
import os
import textwrap
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont

# ── SETTINGS ─────────────────────────────────────────────────────
W, H       = 480, 272
MARGIN     = 24
LINE_H     = 26
MAX_CHARS  = 232
CONTENT    = "content.json"
OUTPUT     = "display.jpg"

# ── COLOURS ──────────────────────────────────────────────────────
WHITE  = (255, 255, 255)
NAVY   = (0,   51,  102)
RED    = (232,  53,  42)
BLUE   = (74,  144, 217)
YELLOW = (245, 194,   0)
DARK   = (20,   20,  20)
BG     = (248, 249, 250)
MUTED  = (160, 160, 160)

# ── FONTS ────────────────────────────────────────────────────────
# These fonts ship with Ubuntu (used in GitHub Actions ubuntu-latest)
FONT_DIR_FREE  = "/usr/share/fonts/truetype/freefont"
FONT_DIR_DEJAVU = "/usr/share/fonts/truetype/dejavu"

def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception as e:
        print(f"Warning: could not load {path}: {e}")
        return ImageFont.load_default()

font_bold_22 = load_font(f"{FONT_DIR_FREE}/FreeSansBold.ttf",   22)
font_bold_16 = load_font(f"{FONT_DIR_FREE}/FreeSansBold.ttf",   16)
font_bold_14 = load_font(f"{FONT_DIR_FREE}/FreeSansBold.ttf",   14)
font_reg_16  = load_font(f"{FONT_DIR_FREE}/FreeSans.ttf",       16)
font_dv_13   = load_font(f"{FONT_DIR_DEJAVU}/DejaVuSans.ttf",   13)

# ── HELPERS ───────────────────────────────────────────────────────
def wrap_text(draw, text, font, max_w):
    """Word-wrap text to fit max_w pixels, return list of lines."""
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_w:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines

def today_aest():
    """Return today's date string in AEST (UTC+10), handling DST via offset."""
    aest = timezone(timedelta(hours=10))
    return datetime.now(aest).strftime("%Y-%m-%d")

def get_day_and_date():
    """Return (day_name, long_date) strings for today in AEST."""
    aest = timezone(timedelta(hours=10))
    now  = datetime.now(aest)
    day  = now.strftime("%A")          # e.g. Wednesday
    date = now.strftime("%-d %B %Y")   # e.g. 25 March 2026
    return day, date

# ── LOAD CONTENT ─────────────────────────────────────────────────
def load_tip():
    today = today_aest()
    print(f"Looking for tip for: {today}")

    with open(CONTENT, "r") as f:
        data = json.load(f)

    entries = data.get("content", [])
    tip = None

    # Find today's entry
    for entry in entries:
        if entry.get("date") == today:
            tip = entry.get("tip", "")
            print(f"Found tip for {today}")
            break

    # Fallback to most recent past entry
    if not tip:
        print(f"No tip for {today} — using most recent entry")
        past = [e for e in entries if e.get("date", "") <= today]
        if past:
            tip = sorted(past, key=lambda e: e["date"])[-1].get("tip", "")

    if not tip:
        tip = "Check back tomorrow for a new fundraising tip!"

    # Truncate if over max chars
    if len(tip) > MAX_CHARS:
        print(f"Warning: tip is {len(tip)} chars, truncating to {MAX_CHARS}")
        tip = tip[:MAX_CHARS].rsplit(" ", 1)[0] + "…"

    return tip

# ── DRAW IMAGE ───────────────────────────────────────────────────
def generate(tip, day_name, long_date):
    TEXT_W = W - MARGIN * 2

    img  = Image.new("RGB", (W, H), WHITE)
    draw = ImageDraw.Draw(img)

    # ── Logo ──────────────────────────────────────────────────────
    logo_path = "Synergy_Logo_RGB.jpg"
    if os.path.exists(logo_path):
        logo = Image.open(logo_path)
        logo_h = 64
        logo_w = int(logo.size[0] * (logo_h / logo.size[1]))
        logo = logo.resize((logo_w, logo_h), Image.LANCZOS)
        img.paste(logo, (MARGIN - 4, 6))
    else:
        # Text fallback if logo file missing
        draw.text((MARGIN, 18), "Synergy Fundraising", font=font_bold_22, fill=NAVY)

    # ── Date (right-aligned) ──────────────────────────────────────
    bbox = draw.textbbox((0, 0), day_name, font=font_bold_22)
    draw.text((W - bbox[2] - MARGIN, 14), day_name, font=font_bold_22, fill=NAVY)

    bbox2 = draw.textbbox((0, 0), long_date, font=font_bold_16)
    draw.text((W - bbox2[2] - MARGIN, 44), long_date, font=font_bold_16, fill=DARK)

    # ── Top separator stripe ──────────────────────────────────────
    sep_y = 76
    draw.rectangle([0,       sep_y, W//3,   sep_y+4], fill=RED)
    draw.rectangle([W//3,    sep_y, W//3*2, sep_y+4], fill=YELLOW)
    draw.rectangle([W//3*2,  sep_y, W,      sep_y+4], fill=BLUE)

    # ── Tip section ───────────────────────────────────────────────
    tip_top = sep_y + 20
    draw.text((MARGIN, tip_top), "TIP OF THE DAY", font=font_bold_16, fill=BLUE)
    tip_top += 24

    lines = wrap_text(draw, tip, font_bold_16, TEXT_W)
    for line in lines:
        draw.text((MARGIN, tip_top), line, font=font_bold_16, fill=DARK)
        tip_top += LINE_H

    # ── Bottom separator — thin black line ────────────────────────
    bot_y = 235
    draw.rectangle([0, bot_y, W, bot_y+1], fill=DARK)

    # ── Footer ────────────────────────────────────────────────────
    draw.rectangle([0, bot_y+1, W, H], fill=BG)

    website = "synergyfundraising.com.au"
    email   = "hello@synergyfundraising.com.au"
    pipe    = "|"

    footer_y = bot_y - 8
    wb = draw.textbbox((0, 0), website, font=font_dv_13)
    pb = draw.textbbox((0, 0), pipe,    font=font_dv_13)
    eb = draw.textbbox((0, 0), email,   font=font_dv_13)
    gap     = 10
    total_w = wb[2] + gap + pb[2] + gap + eb[2]
    start_x = (W - total_w) // 2

    draw.text((start_x,                             footer_y), website, font=font_dv_13, fill=DARK)
    draw.text((start_x + wb[2] + gap,               footer_y), pipe,    font=font_dv_13, fill=MUTED)
    draw.text((start_x + wb[2] + gap + pb[2] + gap, footer_y), email,   font=font_dv_13, fill=DARK)

    return img

# ── MAIN ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Pulse image generator starting...")
    tip              = load_tip()
    day_name, long_date = get_day_and_date()
    print(f"Day: {day_name}  Date: {long_date}")
    print(f"Tip ({len(tip)} chars): {tip}")
    img = generate(tip, day_name, long_date)
    img.save(OUTPUT, "JPEG", quality=95)
    print(f"Saved: {OUTPUT} ({W}x{H}px)")
