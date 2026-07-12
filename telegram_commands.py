"""Turn approved Telegram commands into custom market reports."""
import json
import os
import subprocess
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

STATE = Path("state/telegram_offset.txt")
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = str(os.environ["TELEGRAM_CHAT_ID"])


def api(method, data=None):
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    body = urlencode(data).encode() if data else None
    request = Request(url, body, {"Content-Type": "application/x-www-form-urlencoded"})
    return json.load(urlopen(request, timeout=45))


def main():
    offset = int(STATE.read_text() or "0") if STATE.exists() else 0
    updates = api("getUpdates", {"offset": offset, "timeout": 0}).get("result", [])
    latest = offset
    for update in updates:
        latest = max(latest, update["update_id"] + 1)
        message = update.get("message", {})
        if str(message.get("chat", {}).get("id")) != CHAT_ID:
            continue
        text = (message.get("text") or "").strip()
        command, _, request = text.partition(" ")
        if not command.split("@")[0] in {"/分析", "/analysis"} or not request.strip():
            continue
        api("sendMessage", {"chat_id": CHAT_ID, "text": "已收到，正在產生分析報告。"})
        subprocess.run(
            ["python", "app.py", "custom", "--title", "Telegram 自訂分析", "--request", request.strip()],
            check=True,
        )
    if latest != offset:
        STATE.parent.mkdir(exist_ok=True)
        STATE.write_text(str(latest), encoding="utf-8")


if __name__ == "__main__":
    main()
