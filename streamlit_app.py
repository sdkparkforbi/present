# streamlit_app.py

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
user = urllib.parse.quote_plus('user2')
password = urllib.parse.quote_plus('user2!!')
host = '59.9.20.28'
db = 'investar'
engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{db}')

# 한국 시간 기준 날짜 설정
kst = pytz.timezone('Asia/Seoul')
today_kst = datetime.now(kst).strftime('%Y-%m-%d')

def get_latest_available_date():
    sql = "SELECT MAX(date) as latest_date FROM trend_following"
    result = pd.read_sql(sql, engine).iloc[0]['latest_date']
    return result

latest_date_str = get_latest_available_date()

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

    df['MFR'] = df.PMF.rolling(window=10).sum() / df.NMF.rolling(window=10).sum()
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
        if df.PB.values[i] > 0.6 and df.MFI10.values[i] > 60:
            ax1.plot(df.index[i], df.close.values[i], 'r^')
        elif df.PB.values[i] < 0.2 and df.MFI10.values[i] < 20:
            ax1.plot(df.index[i], df.close.values[i], 'bv')
    ax1.legend(loc='best')

    ax2.plot(df.index, df['PB'] * 100, 'b', label='%B x 100')
    ax2.plot(df.index, df['MFI10'], 'g--', label='MFI(10 day)')
    ax2.set_yticks([-20, 0, 20, 40, 60, 80, 100, 120])
    for i in range(len(df.close)):
        if df.PB.values[i] > 0.6 and df.MFI10.values[i] > 60:
            ax2.plot(df.index[i], 0, 'r^')
        elif df.PB.values[i] < 0.2 and df.MFI10.values[i] < 20:
            ax2.plot(df.index[i], 0, 'bv')
    ax2.grid(True)
    ax2.legend(loc='best')
    plt.tight_layout()
    return fig

def get_positive_news(code):
    sql = f"""
    SELECT title, url, rating2_reason
    FROM corp_news
    WHERE code = '{code}' AND date = '{latest_date_str}'
      AND rating1_score = 1 AND rating2_score = 1
    LIMIT 5
    """
    return pd.read_sql(sql, engine)

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

    sql3 = f"""
    SELECT code, predicted_return
    FROM predicted_returns
    WHERE date = '{date_str}' AND predicted_return > 0
    """
    sheet3 = pd.read_sql(sql3, engine)

    sheet1['code1'] = sheet1['code'].astype(str).str.zfill(6)
    sheet2['code1'] = sheet2['code'].astype(str).str.zfill(6)
    sheet3['code1'] = sheet3['code'].astype(str).str.zfill(6)

    return sheet1, sheet2, sheet3

st.title("🔎 오늘의 추천 종목")
st.write(f"날짜 기준: {latest_date_str} (KST 기준)")

sheet1, sheet2, sheet3 = load_data(latest_date_str)
common = pd.merge(sheet1, sheet2, on='code1')

# sheet3에서 code1 기준으로 중복 제거 (첫 번째 값 유지)
sheet3_dedup = sheet3[['code1', 'predicted_return']].drop_duplicates(subset=['code1'], keep='first')
common = pd.merge(common, sheet3_dedup, on='code1', how='left')

# 예측 수익률 0.00 이상 필터 + 상위 10개 종목만
common = common[common['predicted_return'] > 0.00]
common = common.sort_values(by='predicted_return', ascending=False).head(10)

st.subheader("✅ 매수 시그널 + 긍정 뉴스 종목")

if not common.empty:
    for _, row in common.iterrows():
        st.markdown(f"### {row['company_x']} ({row['code1']})")
        st.markdown(f"- 매수 시그널 발생 (날짜: {latest_date_str})")
        st.markdown(f"- 긍정 뉴스 개수: {row['n_pos_news']}")
        if not pd.isna(row.get('predicted_return')):
            st.markdown(f"- 📈 인공지능 예측 수익률: {row['predicted_return']:.2%}")

        news_df = get_positive_news(row['code_x'])
        if not news_df.empty:
            st.markdown("**📌 긍정 뉴스 목록:**")
            for _, news in news_df.iterrows():
                st.markdown(f"- [{news['title']}]({news['url']})")
                st.caption(f"→ 이유: {news['rating2_reason']}")

        chart = plot_trend_following_chart(row['code_x'])
        if chart:
            st.pyplot(chart)
        st.markdown("---")
else:
    st.write("추천 종목이 없습니다.")

