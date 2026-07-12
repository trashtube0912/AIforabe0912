"""Cloud-only market reporting jobs, designed for GitHub Actions."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import feedparser
import yfinance as yf

TZ = ZoneInfo("Asia/Taipei")
ROOT = Path(__file__).parent
REPORTS = ROOT / "docs" / "reports"

TICKERS = {
    "台灣加權指數": "^TWII", "S&P 500": "^GSPC", "NASDAQ": "^IXIC",
    "費城半導體": "^SOX", "VIX": "^VIX", "美元／台幣": "TWD=X",
}

def fmt_change(value: float) -> str:
    return f"{value:+.2f}%" if value == value else "資料不足"

def market_snapshot() -> list[dict]:
    result = []
    for name, ticker in TICKERS.items():
        try:
            h = yf.Ticker(ticker).history(period="7d", interval="1d", auto_adjust=False)
            close, previous = float(h["Close"].iloc[-1]), float(h["Close"].iloc[-2])
            result.append({"name": name, "close": close, "change": (close / previous - 1) * 100})
        except Exception as exc:
            result.append({"name": name, "close": None, "change": float("nan"), "error": str(exc)})
    return result

def news_items() -> list[dict]:
    seen, output = set(), []
    for q in ("台股", "台灣 股市"):
        feed = feedparser.parse(f"https://news.google.com/rss/search?q={q}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant")
        for entry in feed.entries:
            title = re.sub(r"\s+-\s+[^-]+$", "", entry.get("title", ""))
            if title and title not in seen:
                seen.add(title)
                output.append({"title": title, "link": entry.get("link", ""), "source": entry.get("source", {}).get("title", "")})
            if len(output) >= 8:
                return output
    return output

def ai_summary(prompt: str) -> str | None:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    from openai import OpenAI
    response = OpenAI(api_key=key).responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"), input=prompt,
    )
    return response.output_text.strip()

def render_market(kind: str) -> str:
    now = datetime.now(TZ)
    snapshot, news = market_snapshot(), news_items()
    lines = [f"# {'開盤前市場情緒分析' if kind == 'premarket' else '台股大盤盤後分析'}", "", f"> 產生時間：{now:%Y-%m-%d %H:%M}（台北時間）", "", "## 市場快照", "", "| 指標 | 最新收盤 | 變動 |", "|---|---:|---:|"]
    for x in snapshot:
        close = f"{x['close']:,.2f}" if x["close"] is not None else "資料不足"
        lines.append(f"| {x['name']} | {close} | {fmt_change(x['change'])} |")
    lines += ["", "## 相關新聞", ""]
    lines += [f"- [{x['title']}]({x['link']})（{x['source']}）" for x in news] or ["- 暫無可用新聞來源。"]
    raw = "\n".join(lines)
    instruction = ("你是台灣市場研究助理。根據以下數字和新聞，以繁體中文寫 3 至 5 點客觀市場觀察，區分事實和推論，"
                   "不可提供買賣指令，最後提醒『非投資建議』。\n\n" + raw)
    analysis = ai_summary(instruction)
    if analysis:
        lines += ["", "## AI 觀察", "", analysis]
    else:
        lines += ["", "## AI 觀察", "", "尚未設定 OPENAI_API_KEY；此報告僅列出原始資料與新聞。"]
    lines += ["", "---", "*本報告僅供資訊整理，非投資建議。市場資料可能延遲或有誤。*"]
    return "\n".join(lines)

def latest_podcast() -> tuple[dict | None, str | None]:
    rss = os.getenv("PODCAST_RSS_URL", "").strip()
    if not rss:
        return None, "尚未設定 PODCAST_RSS_URL。"
    feed = feedparser.parse(rss)
    if not feed.entries:
        return None, "RSS 沒有可用節目。"
    e = feed.entries[0]
    return {"title": e.get("title", "未命名節目"), "link": e.get("link", ""), "description": re.sub("<[^>]+>", "", e.get("summary", e.get("description", "")))}, None

def render_podcast() -> str | None:
    episode, error = latest_podcast()
    if error:
        print(error)
        return None
    prompt = ("請以繁體中文將以下 Podcast 節目資訊整理為：主題、重點（3-6 點）、提到的股票或產業（若無則明說）、"
              "以及一段風險提示。不得補寫節目未提供的內容。\n\n" + json.dumps(episode, ensure_ascii=False))
    summary = ai_summary(prompt) or "尚未設定 OPENAI_API_KEY，因此僅保留節目說明。\n\n" + episode["description"]
    return f"# 股癌 Podcast 摘要\n\n> 產生時間：{datetime.now(TZ):%Y-%m-%d %H:%M}（台北時間）\n\n## [{episode['title']}]({episode['link']})\n\n{summary}\n\n---\n*本摘要根據節目 RSS 說明產生，非投資建議。*"

def save_report(category: str, content: str) -> None:
    now = datetime.now(TZ)
    folder = REPORTS / category
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{now:%Y-%m-%d}-{category}.md"
    path = folder / filename
    path.write_text(content, encoding="utf-8")
    index_path = REPORTS / "index.json"
    items = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else []
    item = {"title": content.splitlines()[0].lstrip("# ") + f"｜{now:%Y-%m-%d}", "path": str(path.relative_to(ROOT / "docs")).replace("\\", "/"), "created_at": now.isoformat()}
    items = [x for x in items if x["path"] != item["path"]]
    items.insert(0, item)
    index_path.write_text(json.dumps(items[:100], ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {path}")

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("job", choices=["premarket", "close", "podcast"])
    job = parser.parse_args().job
    if job == "podcast":
        content = render_podcast()
        if content is None:
            return 0
    else:
        content = render_market(job)
    save_report(job, content)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
