#!/usr/bin/env python3
"""Show a focused Todoist task in Waybar, with a Rofi task picker."""

import html
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request


def save_selection(path, task_id):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    # Atomic replacement keeps polling readers from seeing a partial write.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump({"task_id": task_id}, stream)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    selecting = "--select" in sys.argv[1:]
    token_path = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "todoist" / "token"
    state_path = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state") / "waybar" / "todoist.json"
    try:
        token = os.environ.get("TODOIST_API_TOKEN", "").strip()
        if not token and token_path.exists():
            token = token_path.read_text().strip()
        if not token:
            result = {
                "text": "Todoist: setup needed",
                "tooltip": html.escape(f"Put your API token in {token_path} (chmod 600)."),
                "class": "missing-token",
            }
        else:
            tasks = []
            params = {"query": "(today | overdue) & !assigned to: others", "limit": 200}
            while True:
                request = urllib.request.Request(
                    "https://api.todoist.com/api/v1/tasks/filter?" + urllib.parse.urlencode(params),
                    headers={"Authorization": f"Bearer {token}"},
                )
                with urllib.request.urlopen(request, timeout=15) as response:
                    page = json.load(response)
                tasks.extend(page["results"])
                if not page.get("next_cursor"):
                    break
                params["cursor"] = page["next_cursor"]

            tasks.sort(key=lambda task: ((task.get("due") or {}).get("date", ""), task.get("day_order") or 0))
            try:
                selected_id = json.loads(state_path.read_text()).get("task_id")
            except (FileNotFoundError, ValueError, AttributeError):
                selected_id = None
            selected = next((task for task in tasks if task["id"] == selected_id), None)

            if selecting and tasks:
                labels = ["Clear selection"]
                for task in tasks:
                    # Rofi reserves newlines and NULs for rows and metadata.
                    title = " ".join(task["content"].replace("\0", " ").split())
                    due = (task.get("due") or {}).get("date", "")
                    labels.append(f"{title} ({due})" if due else title)
                current_row = tasks.index(selected) + 1 if selected else 0
                choice = subprocess.run(
                    ["rofi", "-dmenu", "-i", "-p", "Today", "-no-custom", "-no-markup-rows",
                     "-format", "i", "-selected-row", str(current_row)],
                    input="\n".join(labels) + "\n", text=True, capture_output=True,
                )
                if choice.returncode == 0:
                    index = int(choice.stdout.strip())
                    if not 0 <= index <= len(tasks):
                        raise ValueError("Invalid picker index")
                    selected = tasks[index - 1] if index else None
                    save_selection(state_path, selected["id"] if selected else None)
                elif choice.returncode != 1:
                    raise ValueError("Could not open task picker")

            title = html.escape(" ".join(selected["content"].split())) if selected else None
            lines = [f"<b>{title}</b>" if selected else "<b>No task selected</b>"]
            lines.append(f"{len(tasks)} tasks in Today (including overdue).")
            if selected:
                due = (selected.get("due") or {}).get("date", "")
                if due:
                    lines.append("Due: " + html.escape(due))
            lines.extend(["Click to select or clear a task.", "Right-click to open Todoist."])
            result = {
                "text": title if selected else ("Select a task" if tasks else "No tasks today"),
                "tooltip": "\n".join(lines),
                "class": "selected" if selected else ("unselected" if tasks else "empty"),
            }
    except urllib.error.HTTPError as error:
        message = "Check your Todoist API token." if error.code in (401, 403) else "Try again shortly."
        result = {"text": "Todoist: unavailable", "tooltip": f"HTTP {error.code}. {message}", "class": "error"}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        # Do not expose request headers, the token, or response bodies in logs/tooltips.
        result = {
            "text": "Todoist: unavailable",
            "tooltip": "Check your connection, token/state files, and Rofi installation. Saved selection is unchanged.",
            "class": "error",
        }
    print(json.dumps(result))
    if selecting:
        try:
            if result["class"] in ("error", "missing-token", "empty"):
                message = "No tasks in Today (including overdue)." if result["class"] == "empty" else html.unescape(result["tooltip"])
                subprocess.run(["rofi", "-e", message], check=False)
        except OSError:
            print("Could not open Rofi. Check that it is installed and on Waybar's PATH.", file=sys.stderr)
        finally:
            try:
                subprocess.run(["pkill", "-RTMIN+8", "-x", "waybar"], check=False)
            except OSError:
                print("Could not refresh Waybar; waiting for the next poll.", file=sys.stderr)


if __name__ == "__main__":
    main()
