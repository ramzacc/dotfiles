#!/usr/bin/env python3
"""Read-only Todoist wallpaper. Sway starts one polling process per session."""

import argparse
from datetime import date, datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import threading
import unicodedata
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw, ImageFont


CONFIG = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
CACHE = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "todoist-wallpaper"
API = "https://api.todoist.com/api/v1/"
TODAY_QUERY = "(today | overdue) & !assigned to: others"
BG, PANEL, TEXT, MUTED = "#18181b", "#202024", "#e4e4e7", "#a1a1aa"
BLUE, GOLD, RED = "#93c5fd", "#fbbf24", "#fca5a5"


def request(token, endpoint, params=None, sync=False):
    encoded = urllib.parse.urlencode(params or {})
    # Sync POST only reads the filters resource: no mutation commands are sent.
    req = urllib.request.Request(
        API + endpoint + ("?" + encoded if encoded and not sync else ""),
        data=encoded.encode() if sync else None,
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.load(response)


def tasks(token, query):
    result = []
    params = {"query": query, "limit": 200}
    while True:
        page = request(token, "tasks/filter", params)
        result.extend(page["results"])
        if not page.get("next_cursor"):
            return result
        params["cursor"] = page["next_cursor"]


def normalize(text):
    return "".join(c for c in unicodedata.normalize("NFKD", text.casefold())
                   if not unicodedata.combining(c))


def fetch():
    token = os.environ.get("TODOIST_API_TOKEN", "").strip()
    if not token:
        token = (CONFIG / "todoist/token").read_text().strip()
    if not token:
        raise ValueError("Missing token")
    filters = request(token, "sync", {"sync_token": "*", "resource_types": '["filters"]'}, sync=True)["filters"]
    saved = next(f for f in filters if not f.get("is_deleted")
                 and normalize(f["name"]) == "proximas deadlines")
    today = tasks(token, TODAY_QUERY)
    deadlines = tasks(token, saved["query"])
    today.sort(key=lambda t: ((t.get("due") or {}).get("date", ""), t.get("day_order") or 0))
    deadlines.sort(key=lambda t: ((t.get("deadline") or {}).get("date", "9999"), -t.get("priority", 1)))
    return {"today": today, "deadlines": deadlines, "filter": saved["name"],
            "updated": datetime.now().isoformat(timespec="minutes")}


def save_json(path, data):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data))
    temporary.replace(path)


def font(size):
    return ImageFont.truetype(FONT_PATH, size)


def fit_lines(draw, text, face, width, maximum=None):
    """Wrap by measured glyph width, including titles with no spaces."""
    text = " ".join(text.split())
    lines = []
    while text and (maximum is None or len(lines) < maximum):
        length = len(text)
        while length > 1 and draw.textlength(text[:length], font=face) > width:
            length -= 1
        if length < len(text) and " " in text[:length]:
            length = text.rfind(" ", 0, length) or length
        lines.append(text[:length].rstrip())
        text = text[length:].lstrip()
    if text:
        last = lines[-1]
        while last and draw.textlength(last + "…", font=face) > width:
            last = last[:-1]
        lines[-1] = last.rstrip() + "…"
    return lines


def readable_text(text):
    """Show common Todoist Markdown as readable text on a non-interactive image."""
    text = re.sub(r"!?\[([^\]]+)\]\((?:[^()]+|\([^()]*\))*\)", r"\1", text)
    text = re.sub(r"<((?:https?://|mailto:)[^>]+)>", r"\1", text)
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s+", "", text)
    text = re.sub(r"(?m)^\s*[-*+]\s+", "• ", text)
    text = re.sub(r"(?m)^\s*>\s?", "", text)
    for marker in ("**", "__", "~~", "`", "*", "_"):
        text = re.sub(re.escape(marker) + r"(\S(?:.*?\S)?)" + re.escape(marker), r"\1", text)
    return text


def task_date(value):
    if "T" in value:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone() if parsed.tzinfo else parsed
    return date.fromisoformat(value)


def relative_date(value, deadline=False, today=None):
    parsed = task_date(value)
    day = parsed.date() if isinstance(parsed, datetime) else parsed
    days = (day - (today or date.today())).days
    if deadline:
        if days < 0:
            count = -days
            label = f"Venció hace {count} {'día' if count == 1 else 'días'}"
        elif days == 0:
            label = "Vence hoy"
        else:
            label = "Falta 1 día" if days == 1 else f"Faltan {days} días"
    elif days == 0:
        label = "hoy"
    elif days == 1:
        label = "mañana"
    elif days == -1:
        label = "ayer"
    elif days < 0:
        label = f"hace {-days} días"
    else:
        label = f"dentro de {days} días"
    if isinstance(parsed, datetime):
        label += parsed.strftime(" a las %H:%M")
    return label, days


def render(data, stale, width, height, tick, destination):
    # Logical output dimensions keep text consistent on HiDPI screens.
    scale = min(width / 1920, height / 1080)
    unit = lambda n: max(1, round(n * scale))
    image = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(image)
    heading, body, description, small = (font(unit(n)) for n in (27, 23, 20, 18))
    margin, gap = unit(80), unit(32)
    top, bottom = unit(100), height - unit(70)
    column_width = (width - 2 * margin - gap) // 2
    text_width = column_width - unit(80)
    available_height = bottom - top - unit(116)
    sections = [("Hoy", data.get("today", []), BLUE),
                (data.get("filter", "Próximas deadlines"), data.get("deadlines", []), GOLD)]
    for column, (name, entries, accent) in enumerate(sections):
        x = margin + column * (column_width + gap)
        draw.rounded_rectangle((x, top, x + column_width, bottom), radius=unit(18), fill=PANEL)
        draw.text((x + unit(28), top + unit(24)), name, font=heading, fill=accent)
        # Measure each task instead of reserving empty rows or clipping descriptions.
        pages, used = [[]], 0
        for task in entries:
            lines = [(line, body, TEXT, unit(31)) for line in
                     fit_lines(draw, readable_text(task["content"]), body, text_width)]
            due = (task.get("due") or {}).get("date", "")
            deadline = (task.get("deadline") or {}).get("date", "")
            if deadline:
                label, days = relative_date(deadline, deadline=True)
                if column == 0:
                    label = "Deadline · " + label.lower()
                lines.append((label, small, RED if days <= 0 else GOLD, unit(29)))
            if due:
                label, days = relative_date(due)
                # Today's heading already supplies the date for today's tasks.
                if column == 1 or days != 0 or "T" in due:
                    if days < 0:
                        label = "Pendiente desde " + label
                    elif column == 1:
                        label = "Programada para " + label
                    else:
                        label = label[0].upper() + label[1:]
                    lines.append((label, small, RED if days < 0 else MUTED, unit(29)))
            details = readable_text(task.get("description") or "")
            if details.strip():
                lines.append(("", description, MUTED, unit(8)))
                for paragraph in details.splitlines():
                    wrapped = fit_lines(draw, paragraph, description, text_width)
                    lines.extend((line, description, MUTED, unit(28)) for line in wrapped)
                    if not wrapped:
                        lines.append(("", description, MUTED, unit(12)))
            # Long descriptions continue on the next page instead of disappearing.
            row_height = sum(line[3] for line in lines) + unit(30)
            if pages[-1] and used + row_height > available_height:
                pages.append([])
                used = 0
            while lines:
                chunk, chunk_height = [], 0
                while lines and chunk_height + lines[0][3] + unit(30) <= available_height - used:
                    line = lines.pop(0)
                    chunk.append(line)
                    chunk_height += line[3]
                pages[-1].append((task.get("priority"), chunk))
                used += chunk_height + unit(30)
                if lines:
                    pages.append([])
                    used = 0
        page = tick % len(pages)
        if len(pages) > 1:
            draw.text((x + column_width - unit(85), top + unit(30)),
                      f"{page + 1}/{len(pages)}", font=small, fill=MUTED)
        if not entries:
            message = "Sin tareas" if data.get("updated") else "Esperando a Todoist…"
            draw.text((x + unit(28), top + unit(92)), message, font=body, fill=MUTED)
        y = top + unit(92)
        for priority, lines in pages[page]:
            priority_color = {4: RED, 3: GOLD, 2: BLUE}.get(priority, MUTED)
            draw.ellipse((x + unit(28), y + unit(9), x + unit(36), y + unit(17)), fill=priority_color)
            text_x = x + unit(52)
            for line, face, color, line_height in lines:
                draw.text((text_x, y), line, font=face, fill=color)
                y += line_height
            y += unit(30)
    if stale:
        draw.text((margin, height - unit(43)), "Sin sincronizar", font=small, fill=MUTED)
    temporary = destination.with_suffix(".tmp")
    image.save(temporary, format="PNG")
    temporary.replace(destination)


def outputs():
    result = subprocess.run(["swaymsg", "-t", "get_outputs", "-r"], check=True, capture_output=True, text=True)
    return [o for o in json.loads(result.stdout) if o.get("active")]


def update(data, stale, tick, apply):
    for output in outputs():
        destination = CACHE / (hashlib.sha256(output["name"].encode()).hexdigest()[:16] + ".png")
        render(data, stale, output["rect"]["width"], output["rect"]["height"], tick, destination)
        if apply:
            command = f'output {json.dumps(output["name"])} bg {json.dumps(str(destination))} fill'
            result = subprocess.run(["swaymsg", "-r", command], check=True, capture_output=True, text=True)
            if not all(reply.get("success") for reply in json.loads(result.stdout)):
                raise RuntimeError("Could not set wallpaper")
        else:
            print(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", action="store_true", help="Fetch and render without setting the wallpaper")
    args = parser.parse_args()
    os.umask(0o077)
    CACHE.mkdir(parents=True, exist_ok=True, mode=0o700)
    wake = threading.Event()
    stopped = threading.Event()
    if not args.preview:
        # A reload wakes the existing worker rather than creating another poller.
        lock = (CACHE / "worker.lock").open("a+")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lock.seek(0)
            try:
                os.kill(int(lock.read()), signal.SIGUSR1)
            except (ValueError, ProcessLookupError):
                pass
            return
        signal.signal(signal.SIGUSR1, lambda *_: wake.set())
        def stop(*_):
            stopped.set()
            wake.set()
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        lock.seek(0)
        lock.truncate()
        lock.write(str(os.getpid()))
        lock.flush()
    global FONT_PATH
    FONT_PATH = subprocess.check_output(["fc-match", "-f", "%{file}", "sans-serif"], text=True)
    state = CACHE / "tasks.json"
    try:
        data = json.loads(state.read_text())
    except (OSError, ValueError):
        data = {}
    tick = 0
    while not stopped.is_set():
        wake.clear()
        stale = False
        try:
            data = fetch()
            save_json(state, data)
        except (OSError, ValueError, KeyError, TypeError, StopIteration):
            # Keep the last successful snapshot; never log tokens or API responses.
            stale = True
        try:
            update(data, stale, tick, apply=not args.preview)
        except (OSError, subprocess.SubprocessError):
            # The Sway session has ended; do not leave a polling process behind.
            return
        if args.preview:
            if stale:
                raise SystemExit("Todoist refresh failed; rendered the cached/empty view.")
            return
        tick += 1
        wake.wait(60)


if __name__ == "__main__":
    main()
