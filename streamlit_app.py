# streamlit_app.py

# 필수 패키지 설치
# pip install streamlit
# pip install sqlalchemy
# pip install mysql-connector-python
# pip install pytz

import streamlit as st
import pandas as pd
import numpy as np
import urllib.parse
from sqlalchemy import create_engine
from datetime import datetime
import pytz  # 시간대 설정용

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
    # 문자열을 datetime으로 변환 후 반환
    return datetime.strptime(result, '%Y-%m-%d')

latest_date = get_latest_available_date()
latest_date_str = latest_date.strftime('%Y-%m-%d')

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
st.write(f"날짜 기준: {latest_date_str} (KST 기준)")

sheet1, sheet2 = load_data(latest_date_str)

# 공통 종목 찾기
common = pd.merge(sheet1, sheet2, on='code1')

st.subheader("✅ 매수 시그널 + 긍정 뉴스 종목")

if not common.empty:
    for _, row in common.iterrows():
        st.markdown(f"- {row['company_x']}({row['code1']}): 매수 시그널 + 긍정 뉴스 {row['n_pos_news']}건")
else:
    st.write("추천 종목이 없습니다.")
