import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="1000萬資產儀表板", page_icon="📈", layout="centered")

st.markdown("""
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .block-container {padding-top: 1.5rem; padding-bottom: 3rem;}
    </style>
""", unsafe_allow_html=True)

FINMIND_TOKEN = st.secrets.get("FINMIND_TOKEN", "")

@st.cache_data(ttl=3600*6)
def fetch_finmind_data(stock_id: str) -> pd.DataFrame:
    url = "https://api.finmindtrade.com/api/v4/data"
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    params = {
        "dataset": "TaiwanStockPrice",
        "data_id": stock_id,
        "start_date": start_date,
        "token": FINMIND_TOKEN
    }
    try:
        resp = requests.get(url, params=params, timeout=10).json()
        if resp.get("status") == 200 and len(resp.get("data", [])) > 0:
            df = pd.DataFrame(resp["data"])
            if "close" in df.columns:
                df["close"] = pd.to_numeric(df["close"], errors='coerce')
                df = df.dropna(subset=["close"])
                return df
    except Exception as e:
        print(f"抓取 {stock_id} 失敗: {e}")
    return pd.DataFrame()

DEFAULT_HOLDINGS = {
    "0050": {"name": "元大台灣50", "shares": 35000, "type": "市值型 (70%)"},
    "00878": {"name": "國泰永續高股息", "shares": 45000, "type": "高股息 (10%)"},
    "0056": {"name": "元大高股息", "shares": 26000, "type": "高股息 (10%)"},
    "00961": {"name": "FT臺灣永續高息", "shares": 100000, "type": "高股息 (10%)"}
}

st.title("📱 1,000 萬資產與全標的檢核")

market_data = {}
with st.spinner('同步最新股市數據中...'):
    for sid in DEFAULT_HOLDINGS.keys():
        df_stock = fetch_finmind_data(sid)
        if not df_stock.empty:
            market_data[sid] = df_stock

if market_data:
    portfolio_rows = []
    total_market_value = 0.0

    for sid, info in DEFAULT_HOLDINGS.items():
        if sid in market_data and not market_data[sid].empty:
            latest_price = float(market_data[sid]["close"].iloc[-1])
            m_val = latest_price * info["shares"]
            total_market_value += m_val
            portfolio_rows.append({
                "代號": sid, 
                "名稱": info["name"], 
                "最新價": latest_price,
                "持有張數": info["shares"] / 1000, 
                "當前市值": m_val, 
                "類別": info["type"]
            })

    if portfolio_rows:
        df_pf = pd.DataFrame(portfolio_rows)
        df_pf["攻守分類"] = df_pf["類別"].apply(lambda x: "市值型 (目標70%)" if "市值型" in x else "高股息 (目標30%)")
        type_summary = df_pf.groupby("攻守分類")["當前市值"].sum().reset_index()

        st.metric(label="💰 當前投資組合總市值", value=f"${total_market_value:,.0f} 元")

        fig_ratio = px.pie(
            type_summary, 
            values='當前市值', 
            names='攻守分類', 
            hole=0.5, 
            color_discrete_sequence=["#00D1B2", "#FF3860"], 
            height=240
        )
        fig_ratio.update_layout(margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig_ratio, use_container_width=True)

        st.divider()

        # 修改後：包含 0050 在內的全標的估值卡片區
        st.subheader("🔔 全標的位階與加碼檢核區")
        tab1, tab2, tab3, tab4 = st.tabs(["0050 (市值)", "00961 (月配)", "00878 (季配)", "0056 (季配)"])

        # 0050 專用檢核邏輯 (看拉回 MDD)
        def render_0050_card():
            if "0050" in market_data and not market_data["0050"].empty:
                df = market_data["0050"]
                price = float(df["close"].iloc[-1])
                h_180d = float(df["close"].tail(120).max())
                mdd_180d = ((price - h_180d) / h_180d) * 100

                st.write(f"**元大台灣50 (0050)** 最新股價：**{price:.2f} 元**")
                st.caption(f"近半年最高價：{h_180d:.2f} 元 ｜ 高點拉回幅度：{mdd_180d:.1f}%")

                if mdd_180d <= -15:
                    st.error("🟢 **【大幅修正】** 盤勢拉回超過 15%，建議動用預備金單筆大舉加碼！")
                elif mdd_180d <= -10:
                    st.warning("🟢 **【技術修正】** 盤勢拉回超過 10%，建議當月定期定額扣款翻倍。")
                else:
                    st.success("⚪ **【常態扣款】** 盤勢高檔維持，保持原計畫定期定額即可。")

        # 高股息通用檢核邏輯
        def render_etf_card(stock_id, stock_name):
            if stock_id in market_data and not market_data[stock_id].empty:
                df = market_data[stock_id]
                price = float(df["close"].iloc[-1])
                h_52w = float(df["close"].max())
                l_52w = float(df["close"].min())
                
                df["MA60"] = df["close"].rolling(60).mean()
                ma60 = float(df["MA60"].iloc[-1]) if len(df) >= 60 else price
                bias_60 = ((price - ma60) / ma60) * 100 if ma60 > 0 else 0
                rank_52w = ((price - l_52w) / (h_52w - l_52w)) * 100 if h_52w != l_52w else 50

                st.write(f"**{stock_name}** 最新股價：**{price:.2f} 元**")
                st.caption(f"52 週位階：{rank_52w:.1f}% ｜ 季線乖離率：{bias_60:+.1f}%")

                if rank_52w < 25 and bias_60 < -3:
                    st.error("🟢 **【低點加碼】** 處於歷史相對低區，建議配息 100% 回買並加碼。")
                elif rank_52w > 80 and bias_60 > 5:
                    st.warning("🔴 **【高估值觀望】** 處於高點區，建議配息暫存現金池。")
                else:
                    st.success("🟡 **【常態回買】** 價格合理，按計畫進行配息再投資。")

        with tab1:
            render_0050_card()
        with tab2:
            render_etf_card("00961", "FT臺灣永續高息")
        with tab3:
            render_etf_card("00878", "國泰永續高股息")
        with tab4:
            render_etf_card("0056", "元大高股息")

        st.divider()

        with st.expander("📊 查看完整 4 檔持股明細"):
            st.dataframe(
                df_pf[["代號", "名稱", "類別", "最新價", "持有張數", "當前市值"]].style.format({
                    "最新價": "${:.2f}",
                    "持有張數": "{:.0f} 張",
                    "當前市值": "${:,.0f}"
                }),
                use_container_width=True
            )
else:
    st.error("⚠️ 無法取得台股歷史數據，請確認網路連線或稍後重新整理。")
