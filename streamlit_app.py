# streamlit_app.py

# pip install matplotlib
# pip install streamlit
# pip install sqlalchemy
# pip install mysql-connector-python
# pip install pytz
# pip install koreanize-matplotlib

import streamlit as st
import pandas as pd
import numpy as np
import urllib.parse
from sqlalchemy import create_engine
from datetime import datetime
import pytz
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import koreanize_matplotlib

# DB 접속 설정
user = urllib.parse.quote_plus('user1')
password = urllib.parse.quote_plus('user1!!')
host = '59.9.20.28'
db = 'investar'
engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{db}')

# 한국 시간 기준 날짜 설정
kst = pytz.timezone('Asia/Seoul')
today_kst = datetime.now(kst).strftime('%Y-%m-%d')

# 최신 날짜 자동 감지
def get_latest_available_date():
    sql = "SELECT MAX(date) as latest_date FROM trend_following"
    result = pd.read_sql(sql, engine).iloc[0]['latest_date']
    return result  # 이미 문자열 형태로 들어옴

latest_date_str = get_latest_available_date()

# 주가 차트 그리기 함수
# def plot_stock_chart(code):
#     sql = f"""
#     SELECT date, close FROM daily_price
#     WHERE code = '{code}' AND date >= DATE_SUB('{latest_date_str}', INTERVAL 90 DAY)
#     ORDER BY date
#     """
#     df = pd.read_sql(sql, engine)
#     if df.empty:
#         return None
#     fig, ax = plt.subplots(figsize=(6, 3))
#     ax.plot(pd.to_datetime(df['date']), df['close'], marker='o', linestyle='-')
#     ax.set_title(f"최근 3개월 주가 흐름", fontsize=12)
#     ax.set_xlabel("날짜")
#     ax.set_ylabel("종가")
#     ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
#     ax.xaxis.set_major_formatter(mdates.DateFormatter('%y%m%d'))
#     plt.xticks(rotation=0)
#     plt.tight_layout()
#     return fig

# 주가 분석 및 차트 그리기 함수 (DB 활용)
def plot_trend_following_chart(code):
    sql = f"""
    SELECT date, open, high, low, close, volume
    FROM daily_price
    WHERE code = '{code}' AND date >= DATE_SUB('{latest_date_str}', INTERVAL 120 DAY)
    ORDER BY date
    """
    df = pd.read_sql(sql, engine)

    if df.empty:
        return None

    df.set_index('date', inplace=True)
    df['MA20'] = df['close'].rolling(window=20).mean()
    df['stddev'] = df['close'].rolling(window=20).std()
    df['upper'] = df['MA20'] + (df['stddev'] * 2)
    df['lower'] = df['MA20'] - (df['stddev'] * 2)
    df['PB'] = (df['close'] - df['lower']) / (df['upper'] - df['lower'])
    df['TP'] = (df['high'] + df['low'] + df['close']) / 3
    df['PMF'] = 0
    df['NMF'] = 0

    for i in range(len(df.close) - 1):
        if df.TP.values[i] < df.TP.values[i + 1]:
            df.PMF.values[i + 1] = df.TP.values[i + 1] * df.volume.values[i + 1]
            df.NMF.values[i + 1] = 0
        else:
            df.NMF.values[i + 1] = df.TP.values[i + 1] * df.volume.values[i + 1]
            df.PMF.values[i + 1] = 0

    df['MFR'] = (df.PMF.rolling(window=10).sum() / df.NMF.rolling(window=10).sum())
    df['MFI10'] = 100 - 100 / (1 + df['MFR'])
    df = df[19:]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 8))
    ax1.set_title(f'{code} Bollinger Band(20 day, 2 std) - Trend Following')
    ax1.plot(df.index, df['close'], color='#0000ff', label='Close')
    ax1.plot(df.index, df['upper'], 'r--', label='Upper band')
    ax1.plot(df.index, df['MA20'], 'k--', label='Moving average 20')
    ax1.plot(df.index, df['lower'], 'c--', label='Lower band')
    ax1.fill_between(df.index, df['upper'], df['lower'], color='0.9')
    for i in range(len(df.close)):
        if df.PB.values[i] > 0.8 and df.MFI10.values[i] > 80:
            ax1.plot(df.index[i], df.close.values[i], 'r^')
        elif df.PB.values[i] < 0.2 and df.MFI10.values[i] < 20:
            ax1.plot(df.index[i], df.close.values[i], 'bv')
    ax1.legend(loc='best')

    ax2.plot(df.index, df['PB'] * 100, 'b', label='%B x 100')
    ax2.plot(df.index, df['MFI10'], 'g--', label='MFI(10 day)')
    ax2.set_yticks([-20, 0, 20, 40, 60, 80, 100, 120])
    for i in range(len(df.close)):
        if df.PB.values[i] > 0.8 and df.MFI10.values[i] > 80:
            ax2.plot(df.index[i], 0, 'r^')
        elif df.PB.values[i] < 0.2 and df.MFI10.values[i] < 20:
            ax2.plot(df.index[i], 0, 'bv')
    ax2.grid(True)
    ax2.legend(loc='best')
    plt.tight_layout()
    return fig

# 뉴스 불러오기 함수
def get_positive_news(code):
    sql = f"""
    SELECT title, url, rating2_reason
    FROM corp_news
    WHERE code = '{code}' AND date = '{latest_date_str}'
      AND rating1_score = 1 AND rating2_score = 1
    LIMIT 5
    """
    return pd.read_sql(sql, engine)

# 데이터 불러오기
@st.cache_data(ttl=600)
def load_data(date_str):
    sql1 = f"""
    SELECT code, company, buy_signal
    FROM trend_following
    WHERE date = '{date_str}' AND buy_signal = 1
    """
    sheet1 = pd.read_sql(sql1, engine)

    sql2 = f"""
    SELECT code, company, n_pos_news
    FROM positive_news
    WHERE date = '{date_str}'
    """
    sheet2 = pd.read_sql(sql2, engine)

    sheet1['code1'] = sheet1['code'].astype(str).str.zfill(6)
    sheet2['code1'] = sheet2['code'].astype(str).str.zfill(6)

    return sheet1, sheet2

# Streamlit 앱 구성
st.title("🔎 오늘의 추천 종목")
st.write(f"날짜 기준: {latest_date_str} (KST 기준)")

sheet1, sheet2 = load_data(latest_date_str)
common = pd.merge(sheet1, sheet2, on='code1')

st.subheader("✅ 매수 시그널 + 긍정 뉴스 종목")

if not common.empty:
    for _, row in common.iterrows():
        st.markdown(f"### {row['company_x']} ({row['code1']})")
        st.markdown(f"- 매수 시그널 발생 (날짜: {latest_date_str})")
        st.markdown(f"- 긍정 뉴스 개수: {row['n_pos_news']}")

        news_df = get_positive_news(row['code_x'])
        if not news_df.empty:
            st.markdown("**📌 긍정 뉴스 목록:**")
            for _, news in news_df.iterrows():
                st.markdown(f"- [{news['title']}]({news['url']})  ")
                st.caption(f"→ 이유: {news['rating2_reason']}")

        chart = plot_trend_following_chart(row['code_x'])
        if chart:
            st.pyplot(chart)
        st.markdown("---")
else:
    st.write("추천 종목이 없습니다.")
