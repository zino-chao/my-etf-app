import os
import requests
import pandas as pd
from datetime import datetime, timedelta

# 1. 讀取 Secrets
FINMIND_TOKEN = os.getenv("FINMIND_TOKEN", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# 追蹤標的
TARGET_ETFS = ["0050", "0056", "00878", "00961"]

def get_etf_data(stock_id):
    """帶入 Token 抓取最新股價與對應日期"""
    url = "https://api.finmindtrade.com/api/v4/data"
    start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
    
    params = {
        "dataset": "TaiwanStockPrice",
        "data_id": stock_id,
        "start_date": start_date,
        "token": FINMIND_TOKEN  # 確保帶入 Token 避免抓到舊數據
    }
    
    try:
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        if data.get("msg") == "success" and len(data.get("data", [])) > 0:
            df = pd.DataFrame(data["data"])
            latest = df.iloc[-1]
            return {
                "price": float(latest["close"]),
                "date": latest["date"]
            }
    except Exception as e:
        print(f"[{stock_id}] 抓取失敗: {e}")
    return None

def calculate_signal(price, stock_id):
    """
    戰術燈號邏輯（可依你的策略條件自行調整比例/均線）
    回傳: (燈號圖示, 燈號文字, 建議動作/金額)
    """
    # 這裡為預設示範邏輯：可依你的 1000 萬控管策略調整
    # 🟢 低點加碼 / 🟡 正常定期定額 / 🔴 偏高觀望
    if stock_id == "0050":
        if price < 175:
            return "🟢", "低點加碼燈", "動用備用金加碼 10 萬 TWD"
        elif price > 195:
            return "🔴", "高估觀望燈", "暫停加碼，維持現金儲備"
        else:
            return "🟡", "正常扣款燈", "執行每週定期定額 (~10.7 萬 TWD)"
    else:
        # 高股息 ETF 邏輯 (0056, 00878, 00961)
        return "🟡", "正常扣款燈", "執行每週定期定額 (平分剩餘額度)"

def send_telegram_msg(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
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
    msg_lines = [
        f"🚨 *1000萬資產 每日戰術提醒*",
        f"📅 觸發時間：`{now_str}`",
        "----------------------------------"
    ]
    
    for etf in TARGET_ETFS:
        info = get_etf_data(etf)
        if info:
            price = info['price']
            date = info['date']
            icon, signal_name, action = calculate_signal(price, etf)
            
            msg_lines.append(f"{icon} *{etf}*：`{price}` 元 _(日期: {date})_")
            msg_lines.append(f"   └ 狀態：*{signal_name}* ➔ {action}")
        else:
            msg_lines.append(f"⚠️ *{etf}*：無法取得最新價格")
            
    msg_lines.append("----------------------------------")
    msg_lines.append("📱 完整持倉與試算請至 Streamlit Dashboard 檢視")
    
    full_message = "\n".join(msg_lines)
    print(full_message)
    send_telegram_msg(full_message)

if __name__ == "__main__":
    main()
