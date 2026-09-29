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
    """取得台股個股/ETF 近一年日線資料"""
    url = "https://api.finmindtrade.com/api/v4/data"
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    params = {
        "dataset": "TaiwanStockPrice",
        "data_id": stock_id,
        "start_date": start_date,
        "token": FINMIND_TOKEN
    }
    try:
        resp = requests.get(url, params=params).json()
        if resp.get("status") == 200 and len(resp.get("data", [])) > 0:
            df = pd.DataFrame(resp["data"])
            df["close"] = df["close"].astype(float)
            return df
    except Exception as e:
        print(f"抓取 {stock_id} 失敗: {e}")
    return pd.DataFrame()

def check_high_dividend_etf(stock_id: str, stock_name: str, df: pd.DataFrame):
    """通用高股息 ETF 估值與買進檢核邏輯"""
    p = df["close"].iloc[-1]
    
    # 修正後正確的 52 週最高價與最低價取得方式
    h_52w = df["close"].max()
    l_52w = df["close"].min()
    rank_52w = ((p - l_52w) / (h_52w - l_52w)) * 100 if h_52w != l_52w else 50
    
    df["MA60"] = df["close"].rolling(60).mean()
    ma60 = df["MA60"].iloc[-1]
    bias_60 = ((p - ma60) / ma60) * 100

    lines = [f"🔔 *【{stock_id} {stock_name} 估值檢核】*"]
    lines.append(f"• 當前股價：`{p:.2f} 元`")
    lines.append(f"• 52 週位階：`{rank_52w:.1f}%` (季線乖離 `{bias_60:+.1f}%`)")

    if rank_52w < 25 and bias_60 < -3:
        lines.append("👉 *建議：🟢 股價處於歷史低位！領到股息建議 100% 回買並額外加碼。*\n")
    elif rank_52w > 80 and bias_60 > 5:
        lines.append("👉 *建議：🔴 股價位於高點區！建議配息暫存現金池等待拉回。*\n")
    else:
        lines.append("👉 *建議：🟡 價格處於合理區間，按原計劃常態回買。*\n")
    return lines

def run_monthly_check():
    notifier = TelegramNotifier(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
    now_str = datetime.now().strftime("%Y-%m-%d")
    msg_lines = [f"📅 *【1,000萬 ETF 跨標的智慧檢核】* ({now_str})\n"]

    # 1. 市值型 0050 檢核
    df_0050 = get_finmind_price("0050")
    if not df_0050.empty:
        p_50 = df_0050["close"].iloc[-1]
        h_180d = df_0050["close"].tail(120).max()
        mdd_180d = ((p_50 - h_180d) / h_180d) * 100

        msg_lines.append("🛡️ *【0050 元大台灣50 (市值型)】*")
        msg_lines.append(f"• 當前股價：`{p_50:.2f} 元`")
        msg_lines.append(f"• 近半年高點拉回：`{mdd_180d:.1f}%`")
        if mdd_180d <= -15:
            msg_lines.append("👉 *建議：🟢 大幅拉回！建議動用預備金單筆大舉加碼！*\n")
        elif mdd_180d <= -10:
            msg_lines.append("👉 *建議：🟢 正常修正，建議當月定期定額扣款翻倍！*\n")
        else:
            msg_lines.append("👉 *建議：⚪ 盤勢維持，保持 regular 定期定額進場。*\n")

    # 2. 三檔高股息 ETF 檢核 (0056, 00878, 00961)
    etf_list = [
        ("00961", "FT臺灣永續高息 (月配)"),
        ("00878", "國泰永續高股息 (季配:2/5/8/11)"),
        ("0056", "元大高股息 (季配:1/4/7/10)")
    ]

    for sid, sname in etf_list:
        df_etf = get_finmind_price(sid)
        if not df_etf.empty:
            msg_lines.extend(check_high_dividend_etf(sid, sname, df_etf))

    notifier.send_message("\n".join(msg_lines), web_app_url=STREAMLIT_URL)

if __name__ == "__main__":
    run_monthly_check()
