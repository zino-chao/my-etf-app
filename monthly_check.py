import os
import requests
import pandas as pd
from datetime import datetime, timedelta

# 1. 讀取環境變數 Secrets
FINMIND_TOKEN = os.getenv("FINMIND_TOKEN", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# 追蹤標的清單
TARGET_ETFS = ["0050", "0056", "00878", "00961"]

def get_etf_data(stock_id):
    """向 FinMind API 抓取最新股價與日期"""
    url = "https://api.finmindtrade.com/api/v4/data"
    start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
    
    params = {
        "dataset": "TaiwanStockPrice",
        "data_id": stock_id,
        "start_date": start_date,
        "token": FINMIND_TOKEN
    }
    
    try:
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        
        if data.get("msg") == "success" and len(data.get("data", [])) > 0:
            df = pd.DataFrame(data["data"])
            latest = df.iloc[-1]
            return {
                "price": latest["close"],
                "date": latest["date"]
            }
        else:
            print(f"[{stock_id}] API 回傳異常: {data.get('msg')}")
            return None
    except Exception as e:
        print(f"[{stock_id}] 抓取失敗: {e}")
        return None

def send_telegram_msg(message):
    """發送訊息至 Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("未設定 Telegram Token 或 Chat ID")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload)

def main():
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    msg_lines = [f"📊 *ETF 每日戰術提醒* ({now_str})", "----------------------------------"]
    
    for etf in TARGET_ETFS:
        info = get_etf_data(etf)
        if info:
            msg_lines.append(f"🔹 *{etf}*：`{info['price']}` 元 _(資料日期: {info['date']})_")
        else:
            msg_lines.append(f"⚠️ *{etf}*：無法取得價格")
            
    msg_lines.append("----------------------------------")
    msg_lines.append("🟢 燈號檢核結果：請至 Streamlit 儀表板確認戰術佈局。")
    
    full_message = "\n".join(msg_lines)
    print(full_message) # 用於 GitHub Actions Log 查閱
    send_telegram_msg(full_message)

if __name__ == "__main__":
    main()
