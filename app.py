"""Cloud-only Taiwan market reports for GitHub Actions."""
import argparse,json,os
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from zoneinfo import ZoneInfo
import feedparser,yfinance as yf
TZ=ZoneInfo("Asia/Taipei"); OUT=Path("docs/reports")
T={"台灣加權":"^TWII","S&P 500":"^GSPC","NASDAQ":"^IXIC","費城半導體":"^SOX","VIX":"^VIX","美元／台幣":"TWD=X"}
def market():
 r=[]
 for n,c in T.items():
  try:
   x=yf.Ticker(c).history(period="7d")["Close"];r+=[f"{n} {x.iloc[-1]:,.2f} ({(x.iloc[-1]/x.iloc[-2]-1)*100:+.2f}%)"]
  except Exception as e:r+=[f"{n}: 資料失敗 ({e})"]
 return "\n".join(r)
def news():
 f=feedparser.parse("https://news.google.com/rss/search?"+urlencode({"q":"台股 OR 台灣股市 when:1d","hl":"zh-TW","gl":"TW","ceid":"TW:zh-Hant"}))
 return "\n".join("- "+x.title for x in f.entries[:12]) or "今日新聞資料不足"
def ask(p):
 k=os.getenv("OPENAI_API_KEY")
 if not k:return "尚未設定 OPENAI_API_KEY，以下為原始資料。"
 try:
  q=Request("https://api.openai.com/v1/responses",json.dumps({"model":"gpt-4.1-mini","input":p}).encode(),{"Authorization":"Bearer "+k,"Content-Type":"application/json"})
  return json.load(urlopen(q,timeout=60)).get("output_text") or "模型未回傳摘要。"
 except Exception as e:return "AI 摘要失敗："+str(e)
def send(title,text):
 k,c=os.getenv("TELEGRAM_BOT_TOKEN"),os.getenv("TELEGRAM_CHAT_ID")
 if not(k and c):return
 try:
  u=f"https://api.telegram.org/bot{k}/sendMessage";v={"chat_id":c,"text":title+"\n\n"+text[:3000]+"\n\n完整報告："+os.getenv("SITE_URL","https://trashtube0912.github.io/AIforabe0912/")};urlopen(Request(u,urlencode(v).encode(),{"Content-Type":"application/x-www-form-urlencoded"}),timeout=30)
 except Exception as e:print("Telegram failed:",e)
def save(kind,title,raw,summary):
 OUT.mkdir(parents=True,exist_ok=True);now=datetime.now(TZ);stamp=now.strftime("%F-%H%M" if kind=="custom" else "%F");text=f"{title}\n\n{summary}\n\n原始資料\n{raw}"
 (OUT/f"{kind}-{stamp}.html").write_text(f"<meta charset='utf-8'><main><h1>{title}</h1><p>{now:%F %R}（台北）</p><pre>{text}</pre></main>",encoding="utf8");send(title,text)
def main():
 p=argparse.ArgumentParser();p.add_argument("job",choices=["premarket","close","podcast","custom"]);p.add_argument("--title",default="自訂分析");p.add_argument("--request",default="");a=p.parse_args();m,n=market(),news()
 if a.job=="custom":title,raw,prompt=a.title,"市場\n"+m+"\n\n新聞\n"+n,"請以繁體中文完成此任務："+a.request+"\n\n資料：\n"+m+"\n"+n
 elif a.job=="podcast":title,raw,prompt="股癌 Podcast 摘要",n,"請根據以下公開新聞整理股癌 Podcast 市場脈絡；若缺本週逐字稿，請明確說明。\n"+n
 else:title="開盤前市場情緒分析" if a.job=="premarket" else "每日股市大盤盤後分析";raw="市場\n"+m+"\n\n新聞\n"+n;prompt=f"請用繁體中文寫{title}，含重點、情緒、風險與觀察，不構成投資建議。\n"+raw
 save(a.job,title,raw,ask(prompt))
if __name__=="__main__":main()
