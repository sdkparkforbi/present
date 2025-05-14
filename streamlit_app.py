import streamlit as st
import pandas as pd
import numpy as np
import urllib.parse
from sqlalchemy import create_engine
from datetime import datetime

# DB 접속 설정
user = urllib.parse.quote_plus('user1')
password = urllib.parse.quote_plus('user1!!')
host = '59.9.20.28'
db = 'investar'
engine = create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{db}')

# 오늘 날짜
today_str = datetime.today().strftime('%Y-%m-%d')

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

    sheet1['code1'] = sheet1['code'].astype(np.int64).map('{:06d}'.format)
    sheet2['code1'] = sheet2['code'].astype(np.int64).map('{:06d}'.format)

    return sheet1, sheet2

# Streamlit 앱 구성
st.title("🔎 오늘의 추천 종목")
st.write(f"날짜 기준: {today_str}")

sheet1, sheet2 = load_data(today_str)

# 공통 종목 찾기
common = pd.merge(sheet1, sheet2, on='code1')

st.subheader("✅ 매수 시그널 + 긍정 뉴스 종목")

if not common.empty:
    for _, row in common.iterrows():
        st.markdown(f"- {row['company_x']}({row['code1']}): 매수 시그널 + 긍정 뉴스 {row['n_pos_news']}건")
else:
    st.write("추천 종목이 없습니다.")
