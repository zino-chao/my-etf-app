import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from telegram_notifier import TelegramNotifier

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
FINMIND_TOKEN = os.getenv("FINMIND_TOKEN")
STREAMLIT_URL = os.getenv("STREAMLIT_URL", "")

def get_finmind_price(stock_id: str):
    url = "https://api.finmindtrade.com/api/v4/data"
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    params = {
        "dataset": "TaiwanStockPrice",
        "data_id": stock_id,
        "start_date": start_date,
        "token": FINMIND_TOKEN
    }
    resp = requests.get(url, params=params).json()
    if resp.get("status") == 200 and len(resp.get("data", [])) > 0:
        df = pd.DataFrame(resp["data"])
        df["close"] = df["close"].astype(float)
        return df
    return pd.DataFrame()

def run_monthly_check():
    notifier = TelegramNotifier(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
    now_str = datetime.now().strftime("%Y-%m-%d")
    msg_lines = [f"📅 *【1,000萬 ETF 每月智慧檢核】* ({now_str})\n"]
    
    # 00961 檢核
    df_961 = get_finmind_price("00961")
    if not df_961.empty:
        p_961 = df_961["close"].iloc[-1]
        h_52w, l_52w = df_961["close"].max(), df_961["close"].min()
        rank_52w = ((p_961 - l_52w) / (h_52w - l_52w)) * 100 if h_52w != l_52w else 50
        df_961["MA60"] = df_961["close"].rolling(60).mean()
        ma60 = df_961["MA60"].iloc[-1]
        bias_60 = ((p_961 - ma60) / ma60) * 100

        msg_lines.append("🔔 *【00961 月配息加碼檢核】*")
        msg_lines.append(f"• 當前股價：`{p_961:.2f} 元`")
        msg_lines.append(f"• 52 週位階：`{rank_52w:.1f}%` (季線乖離 `{bias_60:+.1f}%`)")

        if rank_52w < 25 and bias_60 < -3:
            msg_lines.append("👉 *建議：🟢 股價處於低點！本月配息 100% 回買，並可加碼。*\n")
        elif rank_52w > 80 and bias_60 > 5:
            msg_lines.append("👉 *建議：🔴 股價位於高點！配息建議暫存現金池。*\n")
        else:
            msg_lines.append("👉 *建議：🟡 價格合理，將配息按原比例常態回買。*\n")

    # 0050 檢核
    df_0050 = get_finmind_price("0050")
    if not df_0050.empty:
        p_50 = df_0050["close"].iloc[-1]
        h_180d = df_0050["close"].tail(120).max()
        mdd_180d = ((p_50 - h_180d) / h_180d) * 100

        msg_lines.append("🛡️ *【0050 市值型位階檢核】*")
        msg_lines.append(f"• 當前股價：`{p_50:.2f} 元`")
        msg_lines.append(f"• 近半年高點拉回：`{mdd_180d:.1f}%`")

        if mdd_180d <= -15:
            msg_lines.append("👉 *建議：🟢 市場大幅拉回！啟動預備金單筆大舉加碼！*\n")
        elif mdd_180d <= -10:
            msg_lines.append("👉 *建議：🟢 市場修正，當月定期定額扣款翻倍！*\n")
        else:
            msg_lines.append("👉 *建議：⚪ 盤勢維持，保持原計畫定期定額進場。*\n")

    notifier.send_message("\n".join(msg_lines), web_app_url=STREAMLIT_URL)

if __name__ == "__main__":
    run_monthly_check()
