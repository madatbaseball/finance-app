import streamlit as st
import requests
import os
import yfinance as yf
import pandas as pd
import time
from dotenv import load_dotenv

load_dotenv()
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
DART_API_KEY = os.getenv("DART_API_KEY")

st.set_page_config(page_title="Finance Dashboard", page_icon="📈", layout="wide")

if "page" not in st.session_state:
    st.session_state.page = "홈"
if "portfolio" not in st.session_state:
    st.session_state.portfolio = []
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

APP_PASSWORD = "030303"

if not st.session_state.authenticated:
    st.markdown("""
    <div style="
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 60vh;
    ">
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1.5, 1, 1.5])
    with col2:
        st.markdown("""
        <div style="
            background: white;
            border: 1px solid #e8eaed;
            border-radius: 12px;
            padding: 36px 32px;
            text-align: center;
        ">
            <div style="font-size:20px; font-weight:700; color:#1a1e2e; margin-bottom:6px;">Finance App</div>
            <div style="font-size:13px; color:#888; margin-bottom:24px;">접근 권한이 필요합니다</div>
        </div>
        """, unsafe_allow_html=True)

        pw = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요")
        if st.button("로그인", use_container_width=True):
            if pw == APP_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("비밀번호가 올바르지 않습니다.")
    st.stop()

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container {padding-top: 0rem; padding-left: 2rem; padding-right: 2rem;}

    /* 전체 배경 */
    .stApp {background-color: #f5f6f8;}

    /* 버튼 스타일 */
    div.stButton > button {
        background: transparent;
        border: none;
        color: #888888;
        font-size: 15px;
        font-weight: 500;
        padding: 6px 14px;
        border-radius: 4px;
        transition: all 0.15s ease;
        white-space: nowrap;
    }
    div.stButton > button:hover {
        background: rgba(255,255,255,0.12);
        color: #000000;
    }

    /* 섹션 카드 느낌 */
    .main-card {
        background: white;
        border-radius: 8px;
        padding: 28px 32px;
        border: 1px solid #e8eaed;
        margin-bottom: 16px;
    }

    /* 제목 스타일 */
    h1 {font-size: 24px !important; font-weight: 700 !important; color: #1a1e2e !important; margin-bottom: 8px !important;}
    h2 {font-size: 19px !important; font-weight: 600 !important; color: #1a1e2e !important;}
    h3 {font-size: 16px !important; font-weight: 600 !important; color: #1a1e2e !important;}
    p {font-size: 15px !important; line-height: 1.75 !important;}
    .stMarkdown p {font-size: 15px !important;}
    td, th {font-size: 14px !important;}

    /* expander 스타일 */
    .streamlit-expanderHeader {
        background: white !important;
        border: 1px solid #e8eaed !important;
        border-radius: 6px !important;
        font-size: 14px !important;
    }

    /* 구분선 */
    hr {border: none; border-top: 1px solid #e8eaed; margin: 16px 0;}

    /* metric 카드 */
    div[data-testid="metric-container"] {
        background: white;
        border: 1px solid #e8eaed;
        border-radius: 8px;
        padding: 16px 20px;
    }

    /* 데이터프레임 */
    .stDataFrame {border-radius: 8px; border: 1px solid #e8eaed;}

    /* 입력창 */
    .stTextInput > div > div > input {
        border: 1px solid #dde1e7;
        border-radius: 6px;
        background: white;
        font-size: 14px;
    }
    .stSelectbox > div > div {
        border: 1px solid #dde1e7;
        border-radius: 6px;
        background: white;
    }
    </style>
""", unsafe_allow_html=True)

# 헤더
st.markdown("""
<div style="
    background: linear-gradient(135deg, #0d1b3e 0%, #1a2f5e 100%);
    padding: 0px 32px;
    margin-bottom: 0px;
    display: flex;
    align-items: center;
    border-bottom: 1px solid rgba(255,255,255,0.08);
">
    <span style="color:white; font-size:17px; font-weight:700; letter-spacing:-0.3px; padding: 14px 0; margin-right: 40px;">
        Finance App
    </span>
</div>
""", unsafe_allow_html=True)

# 네비게이션 바
st.markdown("""
<div style="
    background: linear-gradient(135deg, #0d1b3e 0%, #1a2f5e 100%);
    padding: 0px 20px 4px 20px;
    border-bottom: 2px solid #2563eb;
">
""", unsafe_allow_html=True)

def clear_cache_except(keep_page):
    keys_to_clear = {
        "홈": ["news_data", "intl_data", "calendar_data", "fx_data"],
        "기업 분석": ["news_data", "intl_data", "calendar_data", "fx_data", "home_data", "home_summary"],
        "뉴스": ["intl_data", "calendar_data", "fx_data", "home_data", "home_summary"],
        "국제 금융": ["news_data", "calendar_data", "fx_data", "home_data", "home_summary"],
        "실시간 주가": ["news_data", "intl_data", "calendar_data", "fx_data", "home_data", "home_summary"],
        "포트폴리오": ["news_data", "intl_data", "calendar_data", "fx_data", "home_data", "home_summary"],
        "환율": ["news_data", "intl_data", "calendar_data", "home_data", "home_summary"],
        "경제 캘린더": ["news_data", "intl_data", "fx_data", "home_data", "home_summary"],
        "서비스 안내": ["news_data", "intl_data", "calendar_data", "fx_data", "home_data", "home_summary"],
    }
    for key in keys_to_clear.get(keep_page, []):
        st.session_state.pop(key, None)

cols = st.columns([1,1,1,1,1,1,1,1,1,1])
with cols[0]:
    if st.button("홈"):
        st.session_state.page = "홈"
        clear_cache_except("홈")
with cols[1]:
    if st.button("기업 분석"):
        st.session_state.page = "기업 분석"
        clear_cache_except("기업 분석")
with cols[2]:
    if st.button("뉴스"):
        st.session_state.page = "뉴스"
        clear_cache_except("뉴스")
with cols[3]:
    if st.button("국제 금융"):
        st.session_state.page = "국제 금융"
        clear_cache_except("국제 금융")
with cols[4]:
    if st.button("실시간 주가"):
        st.session_state.page = "실시간 주가"
        clear_cache_except("실시간 주가")
with cols[5]:
    if st.button("포트폴리오"):
        st.session_state.page = "포트폴리오"
        clear_cache_except("포트폴리오")
with cols[6]:
    if st.button("환율"):
        st.session_state.page = "환율"
        clear_cache_except("환율")
with cols[7]:
    if st.button("경제 캘린더"):
        st.session_state.page = "경제 캘린더"
        clear_cache_except("경제 캘린더")
with cols[8]:
    if st.button("서비스 안내"):
        st.session_state.page = "서비스 안내"
        clear_cache_except("서비스 안내")
with cols[8] if len(cols) > 8 else st.columns([1])[0]:
    pass

st.markdown("</div>", unsafe_allow_html=True)
st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

def ask_perplexity(prompt):
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "sonar",
        "messages": [{"role": "user", "content": prompt}]
    }
    response = requests.post("https://api.perplexity.ai/chat/completions", headers=headers, json=data)
    return response.json()["choices"][0]["message"]["content"]

KOSPI_TOP = [
    ("삼성전자", "005930.KS"),
    ("SK하이닉스", "000660.KS"),
    ("LG에너지솔루션", "373220.KS"),
    ("삼성바이오로직스", "207940.KS"),
    ("현대차", "005380.KS"),
    ("기아", "000270.KS"),
    ("셀트리온", "068270.KS"),
    ("POSCO홀딩스", "005490.KS"),
    ("삼성SDI", "006400.KS"),
    ("KB금융", "105560.KS"),
]

def get_stock_data(tickers):
    data_list = []
    for name, ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1d", interval="1m")
            if not hist.empty:
                current = hist["Close"].iloc[-1]
                open_price = hist["Open"].iloc[0]
                change = current - open_price
                change_pct = (change / open_price) * 100
                arrow = "▲" if change >= 0 else "▼"
                data_list.append({
                    "종목": name,
                    "현재가": f"{current:,.0f}원",
                    "등락": f"{arrow} {abs(change):,.0f}원",
                    "등락률": f"{change_pct:+.2f}%",
                })
        except:
            pass
    return data_list

@st.cache_data(ttl=3600)
def load_stock_list():
    import zipfile, io, xml.etree.ElementTree as ET
    url = "https://opendart.fss.or.kr/api/corpCode.xml"
    params = {"crtfc_key": DART_API_KEY}
    res = requests.get(url, params=params)
    z = zipfile.ZipFile(io.BytesIO(res.content))
    xml_data = z.read("CORPCODE.xml")
    root = ET.fromstring(xml_data)
    stocks = []
    for corp in root.findall("list"):
        name = corp.findtext("corp_name")
        stock_code = corp.findtext("stock_code")
        if stock_code and stock_code.strip():
            stocks.append({
                "name": name,
                "ticker": stock_code.strip() + ".KS"
            })
    return stocks

page = st.session_state.page

if page == "홈":
    # 핵심 지표
    if "home_data" not in st.session_state:
        with st.spinner("시장 데이터 불러오는 중..."):
            try:
                kospi = yf.Ticker("^KS11").history(period="2d")
                kosdaq = yf.Ticker("^KQ11").history(period="2d")
                usd = yf.Ticker("USDKRW=X").history(period="2d")
                oil = yf.Ticker("CL=F").history(period="2d")

                def get_change(hist):
                    if len(hist) >= 2:
                        cur = hist["Close"].iloc[-1]
                        prev = hist["Close"].iloc[-2]
                        chg = ((cur - prev) / prev) * 100
                        return cur, chg
                    return None, None

                k_cur, k_chg = get_change(kospi)
                kq_cur, kq_chg = get_change(kosdaq)
                u_cur, u_chg = get_change(usd)
                o_cur, o_chg = get_change(oil)

                st.session_state.home_data = {
                    "kospi": (k_cur, k_chg),
                    "kosdaq": (kq_cur, kq_chg),
                    "usd": (u_cur, u_chg),
                    "oil": (o_cur, o_chg),
                }
            except:
                st.session_state.home_data = {}

    home = st.session_state.get("home_data", {})

    def render_index_card(label, value, chg, unit="", decimals=2):
        if value is None:
            return f"""
            <div style="background:white; border:1px solid #e8eaed; border-radius:8px; padding:20px 24px;">
                <div style="font-size:14px; color:#888; font-weight:500; margin-bottom:10px;">{label}</div>
                <div style="font-size:28px; font-weight:700; color:#1a1e2e;">-</div>
            </div>"""
        chg_color = "#e03131" if chg and chg < 0 else "#2f9e44"
        arrow = "▼" if chg and chg < 0 else "▲"
        chg_str = f"{arrow} {abs(chg):.2f}%" if chg is not None else ""
        val_str = f"{value:,.{decimals}f}{unit}"
        return f"""
        <div style="background:white; border:1px solid #e8eaed; border-radius:8px; padding:20px 24px;">
            <div style="font-size:14px; color:#888; font-weight:500; margin-bottom:10px;">{label}</div>
            <div style="font-size:28px; font-weight:700; color:#1a1e2e;">{val_str}</div>
            <div style="font-size:14px; color:{chg_color}; font-weight:600; margin-top:6px;">{chg_str}</div>
        </div>"""

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(render_index_card("KOSPI", home.get("kospi", (None,None))[0], home.get("kospi", (None,None))[1]), unsafe_allow_html=True)
    c2.markdown(render_index_card("KOSDAQ", home.get("kosdaq", (None,None))[0], home.get("kosdaq", (None,None))[1]), unsafe_allow_html=True)
    c3.markdown(render_index_card("USD/KRW", home.get("usd", (None,None))[0], home.get("usd", (None,None))[1], "원", 0), unsafe_allow_html=True)
    c4.markdown(render_index_card("WTI 원유", home.get("oil", (None,None))[0], home.get("oil", (None,None))[1], "$"), unsafe_allow_html=True)

    st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

    # 오늘의 시장 요약
    if "home_summary" not in st.session_state:
        with st.spinner("오늘의 시장 요약 생성 중..."):
            summary = ask_perplexity("오늘 한국 주식시장과 글로벌 금융시장의 핵심 동향을 3문장으로 간결하게 요약해줘. 수치 포함. 반드시 지켜야 할 규칙: **별표** 같은 마크다운 기호 절대 사용 금지, 대괄호 안 숫자 각주 절대 사용 금지, 일반 텍스트로만 작성.")
            import re
            summary = re.sub(r'\*\*?(.*?)\*\*?', r'\1', summary)
            summary = re.sub(r'\[\d+\]', '', summary)
            summary = summary.strip()
            st.session_state.home_summary = summary

    st.markdown(f"""
    <div style="background:white; border:1px solid #e8eaed; border-left: 5px solid #2563eb; border-radius:8px; padding:28px 36px; margin-bottom:20px;">
        <div style="font-size:15px; color:#2563eb; font-weight:700; margin-bottom:14px; letter-spacing:-0.2px;">오늘의 시장 요약</div>
        <div style="font-size:17px; color:#1a1e2e; line-height:1.85; font-weight:400;">{st.session_state.home_summary}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)
    # 시총 상위 5 미니 테이블
    st.markdown("""
    <div style="font-size:15px; font-weight:700; color:#1a1e2e; margin-bottom:12px;">시총 상위 5 종목</div>
    """, unsafe_allow_html=True)

    top5 = KOSPI_TOP[:5]
    mini_data = get_stock_data(top5)
    if mini_data:
        df_mini = pd.DataFrame(mini_data)
        st.dataframe(df_mini, use_container_width=True, hide_index=True)

elif page == "서비스 안내":
    st.title("서비스 안내")
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    services = [
        ("기업 분석", "AI가 다트공시·뉴스·증권사 리포트를 통합 분석해 투자의견, 목표주가, 핵심 이슈를 제공합니다."),
        ("뉴스", "오늘의 주요 금융 뉴스를 AI가 요약해 제목만 보고 빠르게 파악하고, 클릭하면 전문을 확인할 수 있습니다."),
        ("국제 금융", "미국·중동·아시아 시장 동향, 환율 흐름, 주요 리스크 요인을 AI가 분석해 제공합니다."),
        ("실시간 주가", "코스피 시총 상위 100개 종목의 현재가와 등락률을 확인하고, 종목명으로 직접 검색할 수 있습니다."),
        ("포트폴리오", "보유 종목과 매수 평균가를 입력하면 현재가 기준 평가금액과 수익률을 자동으로 계산합니다."),
        ("환율", "주요 통화의 실시간 환율을 확인하고, 원하는 통화 간 환전 금액을 즉시 계산할 수 있습니다."),
        ("경제 캘린더", "이번 주 주요 글로벌 경제 지표 발표 일정을 중요도와 함께 확인할 수 있습니다."),
    ]
    for name, desc in services:
        st.markdown(f"""
        <div style="background:white; border:1px solid #e8eaed; border-radius:8px; padding:18px 24px; margin-bottom:10px; display:flex; align-items:flex-start; gap:16px;">
            <div style="min-width:90px; font-size:13px; font-weight:600; color:#2563eb;">{name}</div>
            <div style="font-size:14px; color:#444; line-height:1.6;">{desc}</div>
        </div>
        """, unsafe_allow_html=True)

elif page == "기업 분석":
    st.title("기업 분석")

    st.markdown("""
    <style>
    div[data-testid="stForm"] {border: none; padding: 0;}
    div[data-testid="stForm"] button {
        background: #1a2f5e !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 28px !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        cursor: pointer !important;
        transition: background 0.2s !important;
    }
    div[data-testid="stForm"] button:hover {
        background: #2563eb !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

    with st.form(key="company_form"):
        company = st.text_input("기업명을 입력하세요", placeholder="예: 삼성전자")
        submitted = st.form_submit_button("분석 시작")

    if submitted and company:
        with st.spinner(f"{company} 분석 중..."):
            import re
            prompt = f"""
{company}에 대해 다음 항목을 한국어로 분석해줘:
1. 투자의견 (매수/중립/매도)
2. 목표주가 컨센서스
3. 핵심 이슈
4. 최근 뉴스 요약
5. 산업 분위기

규칙: 문장 끝에 [1], [2] 같은 대괄호 각주 절대 포함하지 말 것. 마크다운 **별표** 사용 금지.
"""
            result = ask_perplexity(prompt)
            result = re.sub(r'\[\d+\]', '', result)
            result = re.sub(r'\*\*?(.*?)\*\*?', r'\1', result)
            st.markdown(result)

elif page == "뉴스":
    st.title("금융 뉴스")
    import re

    NEWS_CATEGORIES = {
        "종합 금융": "오늘의 주요 금융 및 경제",
        "바이오·제약": "바이오 및 제약 산업",
        "방산·우주": "방위산업 및 우주항공 산업",
        "반도체·IT": "반도체 및 IT 기술 산업",
        "2차전지·전기차": "2차전지 및 전기차 산업",
        "은행·금융": "은행 및 금융권",
        "건설·부동산": "건설 및 부동산 시장",
        "에너지·원자재": "에너지 및 원자재 시장",
        "자동차": "자동차 산업",
        "항공·여행": "항공 및 여행 산업",
        "유통·소비재": "유통 및 소비재 산업",
        "게임·엔터": "게임 및 엔터테인먼트 산업",
        "글로벌 증시": "미국·유럽·아시아 글로벌 증시",
        "환율·외환": "환율 및 외환 시장",
        "IPO·공모": "신규 상장 및 공모주",
        "정책·규제": "정부 정책 및 금융 규제",
        "AI·로봇": "인공지능 및 로봇 산업",
        "ESG·친환경": "ESG 및 친환경 산업",
        "물류·해운": "물류 및 해운 산업",
        "의료기기·헬스케어": "의료기기 및 헬스케어 산업",
    }

    selected_category = st.selectbox(
        "뉴스 분야 선택",
        list(NEWS_CATEGORIES.keys()),
        key="news_category"
    )

    cache_key = f"news_{selected_category}"

    if cache_key not in st.session_state:
        with st.spinner(f"{selected_category} 뉴스 불러오는 중..."):
            keyword = NEWS_CATEGORIES[selected_category]
            result = ask_perplexity(f"""
오늘 {keyword} 관련 주요 뉴스 5개를 아래 형식으로 한국어로 작성해줘.
각 뉴스마다 반드시 이 형식을 지켜줘.
규칙: 문장 끝 [1][2] 같은 대괄호 각주 절대 금지. ** 별표 마크다운 사용 금지.

제목: [뉴스 제목]
요약: [한 줄 핵심 요약]
전문: [5-6줄 상세 내용. 배경, 원인, 영향까지 포함]
---
""")
            result = re.sub(r'\[\d+\]', '', result)
            result = re.sub(r'\*\*?(.*?)\*\*?', r'\1', result)
            st.session_state[cache_key] = result

    news_items = st.session_state[cache_key].strip().split("---")
    for item in news_items:
        item = item.strip()
        if not item:
            continue
        lines = item.split("\n")
        title = summary = full = ""
        for line in lines:
            if line.startswith("제목:"):
                title = line.replace("제목:", "").strip()
            elif line.startswith("요약:"):
                summary = line.replace("요약:", "").strip()
            elif line.startswith("전문:"):
                full = line.replace("전문:", "").strip()
        if title:
            with st.expander(f"{title}"):
                st.markdown(f"**핵심:** {summary}")
                st.markdown("---")
                st.markdown(full)

elif page == "국제 금융":
    st.title("국제 금융")
    if "intl_data" not in st.session_state:
        with st.spinner("국제 금융 동향 분석 중..."):
            import re
        result = ask_perplexity("""
지금 이 시점 기준으로 국제 금융시장의 최신 동향을 한국어로 분석해줘.
데이터가 제한적이더라도 알고 있는 최신 정보를 바탕으로 반드시 아래 5개 항목을 각각 2~3문장으로 작성해줘.
데이터 부족을 이유로 거절하지 말고 현재 시점에서 가장 최신의 정보로 답변해줘.

1. 미국 시장 동향 (주요 지수 흐름, 섹터 강약)
2. 중동 및 유가 동향 (지정학적 리스크, 유가 수준)
3. 아시아 시장 동향 (한국, 일본, 중국 시장)
4. 환율 동향 (달러 강약, 원/달러 흐름)
5. 주요 리스크 요인 (글로벌 시장 위협 요소)

규칙: 문장 끝 [1][2] 대괄호 각주 절대 금지. ** 별표 마크다운 사용 금지. 분석 불가 안내 문구 절대 금지.
""")
        result = re.sub(r'\[\d+\]', '', result)
        result = re.sub(r'\*\*?(.*?)\*\*?', r'\1', result)
        st.session_state.intl_data = result
    st.markdown(st.session_state.intl_data)

elif page == "실시간 주가":
    st.title("실시간 주가")

    KOSPI_100 = [
        ("삼성전자", "005930.KS"), ("SK하이닉스", "000660.KS"), ("LG에너지솔루션", "373220.KS"),
        ("삼성바이오로직스", "207940.KS"), ("현대차", "005380.KS"), ("기아", "000270.KS"),
        ("셀트리온", "068270.KS"), ("POSCO홀딩스", "005490.KS"), ("삼성SDI", "006400.KS"),
        ("KB금융", "105560.KS"), ("신한지주", "055550.KS"), ("LG화학", "051910.KS"),
        ("하나금융지주", "086790.KS"), ("현대모비스", "012330.KS"), ("삼성물산", "028260.KS"),
        ("카카오", "035720.KS"), ("네이버", "035420.KS"), ("우리금융지주", "316140.KS"),
        ("LG전자", "066570.KS"), ("SK이노베이션", "096770.KS"), ("삼성생명", "032830.KS"),
        ("한국전력", "015760.KS"), ("두산에너빌리티", "034020.KS"), ("HMM", "011200.KS"),
        ("SK텔레콤", "017670.KS"), ("롯데케미칼", "011170.KS"), ("대한항공", "003490.KS"),
        ("고려아연", "010130.KS"), ("한화에어로스페이스", "012450.KS"), ("삼성전기", "009150.KS"),
        ("현대제철", "004020.KS"), ("SK바이오팜", "326030.KS"), ("크래프톤", "259960.KS"),
        ("카카오뱅크", "323410.KS"), ("한국가스공사", "036460.KS"), ("LG이노텍", "011070.KS"),
        ("SK", "034730.KS"), ("삼성화재", "000810.KS"), ("한온시스템", "018880.KS"),
        ("현대글로비스", "086280.KS"), ("코웨이", "021240.KS"), ("KT&G", "033780.KS"),
        ("아모레퍼시픽", "090430.KS"), ("오리온", "271560.KS"), ("엔씨소프트", "036570.KS"),
        ("현대중공업", "329180.KS"), ("하이브", "352820.KS"), ("카카오페이", "377300.KS"),
        ("KT", "030200.KS"), ("LG생활건강", "051900.KS"), ("S-Oil", "010950.KS"),
        ("금호석유", "011780.KS"), ("한미약품", "128940.KS"), ("롯데쇼핑", "023530.KS"),
        ("이마트", "139480.KS"), ("신세계", "004170.KS"), ("OCI", "010060.KS"),
        ("한진칼", "180640.KS"), ("두산밥캣", "241560.KS"), ("현대건설", "000720.KS"),
        ("GS건설", "006360.KS"), ("삼성엔지니어링", "028050.KS"), ("대우조선해양", "042660.KS"),
        ("한화솔루션", "009830.KS"), ("롯데지주", "004990.KS"), ("CJ제일제당", "097950.KS"),
        ("BGF리테일", "282330.KS"), ("GS리테일", "007070.KS"), ("현대백화점", "069960.KS"),
        ("농심", "004370.KS"), ("오뚜기", "007310.KS"), ("빙그레", "005180.KS"),
        ("하이트진로", "000080.KS"), ("CJ", "001040.KS"), ("한국콜마", "161890.KS"),
        ("LG유플러스", "032640.KS"), ("더존비즈온", "012510.KS"), ("위메이드", "112040.KS"),
        ("펄어비스", "263750.KS"), ("컴투스", "078340.KS"), ("제주항공", "089590.KS"),
        ("진에어", "272450.KS"), ("에스원", "012750.KS"), ("현대해상", "001450.KS"),
        ("DB손해보험", "005830.KS"), ("메리츠화재", "000060.KS"), ("한국금융지주", "071050.KS"),
        ("미래에셋증권", "006800.KS"), ("NH투자증권", "005940.KS"), ("삼성증권", "016360.KS"),
        ("키움증권", "039490.KS"), ("한국항공우주", "047810.KS"), ("현대위아", "011210.KS"),
        ("만도", "204320.KS"), ("LS일렉트릭", "010120.KS"), ("효성중공업", "298040.KS"),
        ("일진머티리얼즈", "020150.KS"), ("SK아이이테크놀로지", "361610.KS"),
    ]

    tab2, tab3, tab1 = st.tabs(["국내 주식 검색", "해외 주식 검색", "시총 상위 100"])

    with tab1:
        st.caption("코스피 시가총액 상위 100개 종목 / 30초마다 자동 업데이트")
        if st.button("주가 불러오기", key="load_top100"):
            st.session_state.top100_loaded = True
        if st.session_state.get("top100_loaded"):
            placeholder = st.empty()
            for _ in range(1):
                data_list = get_stock_data(KOSPI_100)
                with placeholder.container():
                    if data_list:
                        df = pd.DataFrame(data_list)
                        df.index = range(1, len(df) + 1)
                        st.dataframe(df, use_container_width=True)
                    st.caption(f"마지막 업데이트: {pd.Timestamp.now().strftime('%H:%M:%S')}")

    with tab3:
        st.caption("미국 나스닥·NYSE 등 해외 주식 티커를 직접 입력하세요. 예: AAPL, TSLA, QNCX")
        search_foreign = st.text_input("티커 입력", placeholder="예: AAPL", key="foreign_search")
        if search_foreign:
            ticker_upper = search_foreign.strip().upper()
            with st.spinner(f"{ticker_upper} 주가 불러오는 중..."):
                try:
                    stock = yf.Ticker(ticker_upper)
                    hist = stock.history(period="5d", interval="1d")
                    info = stock.info
                    if not hist.empty:
                        current = hist["Close"].iloc[-1]
                        prev = hist["Close"].iloc[-2] if len(hist) >= 2 else hist["Open"].iloc[-1]
                        change = current - prev
                        change_pct = (change / prev) * 100
                        arrow = "▲" if change >= 0 else "▼"
                        name = info.get("shortName", ticker_upper)
                        currency = info.get("currency", "USD")
                        exchange = info.get("exchange", "")

                        st.markdown(f"### {name} ({ticker_upper})")
                        st.caption(f"{exchange} · {currency}")

                        c1, c2, c3 = st.columns(3)
                        c1.metric("현재가", f"{current:,.2f} {currency}")
                        c2.metric("전일 대비", f"{arrow} {abs(change):,.2f}")
                        c3.metric("등락률", f"{change_pct:+.2f}%")

                        st.markdown("---")
                        st.markdown("**최근 5일 종가**")
                        chart_data = hist[["Close"]].copy()
                        chart_data.index = chart_data.index.strftime("%m/%d")
                        st.line_chart(chart_data)
                    else:
                        st.warning("해당 티커의 주가 정보를 불러올 수 없습니다.")
                except:
                    st.warning("해당 티커의 주가 정보를 불러올 수 없습니다.")

    with tab2:
        st.caption("종목명으로 직접 검색해 현재가와 차트를 확인하세요.")
        with st.spinner("종목 목록 불러오는 중..."):
            stock_list = load_stock_list()
        stock_names = [s["name"] for s in stock_list]
        stock_map = {s["name"]: s["ticker"] for s in stock_list}

        search_q = st.text_input("종목명 검색", placeholder="예: 삼성전자")
        if search_q:
            search_lower = search_q.lower()
            exact = [n for n in stock_names if n.lower() == search_lower]
            contains = [n for n in stock_names if search_lower in n.lower() and n.lower() != search_lower]
            matched = exact + contains
            if matched:
                matched_with_code = [
                    f"{n}  ({stock_map.get(n, '').replace('.KS', '')})"
                    for n in matched
                ]
                selected_display = st.selectbox("종목 선택", matched_with_code)
                selected_name = selected_display.split("  (")[0]
                selected_ticker = stock_map.get(selected_name, "")
                if selected_ticker:
                    import plotly.graph_objects as go

                    period_map = {
                        "1일": ("1d", "1m"),
                        "3일": ("5d", "5m"),
                        "1년": ("1y", "1d"),
                        "3년": ("3y", "1wk"),
                        "10년": ("10y", "1mo"),
                    }
                    selected_period = st.radio("기간 선택", list(period_map.keys()), horizontal=True, key="kr_period")
                    p, i = period_map[selected_period]

                    with st.spinner(f"{selected_name} 주가 불러오는 중..."):
                        try:
                            hist = pd.DataFrame()
                            for suffix in [".KS", ".KQ"]:
                                code = selected_ticker.replace(".KS","").replace(".KQ","")
                                t = yf.Ticker(code + suffix)
                                h = t.history(period=p, interval=i)
                                if not h.empty:
                                    hist = h
                                    selected_ticker = code + suffix
                                    break

                            if not hist.empty:
                                current = hist["Close"].iloc[-1]
                                prev = hist["Close"].iloc[-2] if len(hist) >= 2 else hist["Open"].iloc[-1]
                                change = current - prev
                                change_pct = (change / prev) * 100
                                arrow = "▲" if change >= 0 else "▼"

                                st.markdown(f"### {selected_name}")
                                c1, c2, c3 = st.columns(3)
                                c1.metric("현재가", f"{current:,.0f}원")
                                c2.metric("전일 대비", f"{arrow} {abs(change):,.0f}원")
                                c3.metric("등락률", f"{change_pct:+.2f}%")

                                st.markdown("---")

                                idx = pd.to_datetime(hist.index)
                                if selected_period in ["1일", "3일"]:
                                    tickformat = "%m/%d<br>%H:%M"
                                    dtick = 3600000 * 2 if selected_period == "1일" else 3600000 * 6
                                elif selected_period == "1년":
                                    tickformat = "%Y/%m"
                                    dtick = "M1"
                                elif selected_period == "3년":
                                    tickformat = "%Y/%m"
                                    dtick = "M3"
                                else:
                                    tickformat = "%Y"
                                    dtick = "M12"

                                fig = go.Figure()
                                fig.add_trace(go.Scatter(
                                    x=idx,
                                    y=hist["Close"],
                                    mode="lines",
                                    line=dict(color="#2563eb", width=2),
                                    hovertemplate="%{x|%Y/%m/%d %H:%M}<br>%{y:,.0f}원<extra></extra>"
                                ))
                                fig.update_layout(
                                    height=400,
                                    margin=dict(l=0, r=0, t=20, b=0),
                                    paper_bgcolor="white",
                                    plot_bgcolor="white",
                                    xaxis=dict(
                                        tickformat=tickformat,
                                        dtick=dtick,
                                        tickangle=0,
                                        showgrid=True,
                                        gridcolor="#f0f0f0",
                                        tickfont=dict(size=11),
                                    ),
                                    yaxis=dict(
                                        showgrid=True,
                                        gridcolor="#f0f0f0",
                                        tickformat=",",
                                        tickfont=dict(size=11),
                                    ),
                                    showlegend=False,
                                )
                                st.markdown(f"**{selected_period} 차트**")
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.warning("해당 기업의 주가 정보를 불러올 수 없습니다.")
                        except Exception as e:
                            st.warning("해당 기업의 주가 정보를 불러올 수 없습니다.")
            else:
                st.warning("검색 결과가 없습니다.")

elif page == "포트폴리오":
    st.title("포트폴리오 트래커")

    with st.spinner("종목 목록 불러오는 중..."):
        stock_list = load_stock_list()

    stock_names = [s["name"] for s in stock_list]
    stock_map = {s["name"]: s["ticker"] for s in stock_list}

    col_a, col_b = st.columns(2)
    with col_a:
        search = st.text_input("종목명 검색", placeholder="예: 삼성전자")
    with col_b:
        qty_input = st.number_input("보유 수량", min_value=1, value=1)

    selected_stock = None
    if search:
        search_lower = search.lower()
        exact = [n for n in stock_names if n.lower() == search_lower]
        contains = [n for n in stock_names if search_lower in n.lower() and n.lower() != search_lower]
        matched = exact + contains
        if matched:
            matched_with_code = [
                f"{n}  ({stock_map.get(n, '').replace('.KS', '')})"
                for n in matched
            ]
            selected_display = st.selectbox("종목 선택", matched_with_code)
            selected_stock = selected_display.split("  (")[0]
        else:
            st.warning("검색 결과가 없습니다.")

    buy_price = st.number_input(
        "매수 평균가 (원)",
        min_value=0,
        value=None,
        placeholder="예: 73000",
        step=100,
        format="%d"
    )

    if st.button("종목 추가", key="add_btn"):
        if selected_stock and buy_price and buy_price > 0:
            ticker_auto = stock_map.get(selected_stock, "")
            st.session_state.portfolio.append({
                "name": selected_stock,
                "ticker": ticker_auto,
                "qty": qty_input,
                "buy_price": buy_price
            })
            st.success(f"{selected_stock} 추가됨!")
        else:
            st.warning("종목과 매수 평균가를 입력해주세요.")

    if st.session_state.portfolio:
        st.markdown("---")
        total_invested = 0
        total_value = 0
        rows = []
        portfolio_data = []
        for item in st.session_state.portfolio:
            try:
                stock = yf.Ticker(item["ticker"])
                hist = stock.history(period="1d")
                current = hist["Close"].iloc[-1] if not hist.empty else 0
                invested = item["buy_price"] * item["qty"]
                value = current * item["qty"]
                profit = value - invested
                profit_pct = (profit / invested * 100) if invested > 0 else 0
                total_invested += invested
                total_value += value
                rows.append({
                    "종목": item["name"],
                    "보유수량": item["qty"],
                    "매수가": f"{item['buy_price']:,.0f}원",
                    "현재가": f"{current:,.0f}원",
                    "투자금액": f"{invested:,.0f}원",
                    "평가금액": f"{value:,.0f}원",
                    "수익금액": f"{profit:+,.0f}원",
                    "수익률": f"{profit_pct:+.2f}%",
                })
                portfolio_data.append(item)
            except:
                rows.append({
                    "종목": item["name"],
                    "보유수량": item["qty"],
                    "매수가": f"{item['buy_price']:,.0f}원",
                    "현재가": "-",
                    "투자금액": "-",
                    "평가금액": "-",
                    "수익금액": "-",
                    "수익률": "-",
                })
                portfolio_data.append(item)

        st.markdown("""
        <style>
        .row-header {color: #2d2d2d; font-size: 12px; padding: 4px 0px;}
        .row-item {font-size: 14px; padding: 6px 0px;}
        </style>
        """, unsafe_allow_html=True)

        header = st.columns([2, 1, 1.3, 1.3, 1.5, 1.5, 1.5, 1.3, 0.5])
        for h, col in zip(["종목", "보유수량", "매수가", "현재가", "투자금액", "평가금액", "수익금액", "수익률", ""], header):
            col.markdown(f"<span class='row-header'>{h}</span>", unsafe_allow_html=True)

        for i, row in enumerate(rows):
            cols = st.columns([2, 1, 1.3, 1.3, 1.5, 1.5, 1.5, 1.3, 0.5])
            cols[0].markdown(f"<span class='row-item'>{row['종목']}</span>", unsafe_allow_html=True)
            cols[1].markdown(f"<span class='row-item'>{row['보유수량']}</span>", unsafe_allow_html=True)
            cols[2].markdown(f"<span class='row-item'>{row['매수가']}</span>", unsafe_allow_html=True)
            cols[3].markdown(f"<span class='row-item'>{row['현재가']}</span>", unsafe_allow_html=True)
            cols[4].markdown(f"<span class='row-item'>{row['투자금액']}</span>", unsafe_allow_html=True)
            cols[5].markdown(f"<span class='row-item'>{row['평가금액']}</span>", unsafe_allow_html=True)
            cols[6].markdown(f"<span class='row-item'>{row['수익금액']}</span>", unsafe_allow_html=True)
            cols[7].markdown(f"<span class='row-item'>{row['수익률']}</span>", unsafe_allow_html=True)
            if cols[8].button("✕", key=f"del_{i}"):
                st.session_state.portfolio.pop(i)
                st.rerun()

        total_profit = total_value - total_invested
        total_pct = (total_profit / total_invested * 100) if total_invested > 0 else 0
        st.markdown("---")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("총 투자금액", f"{total_invested:,.0f}원")
        c2.metric("총 평가금액", f"{total_value:,.0f}원")
        c3.metric("총 수익금액", f"{total_profit:+,.0f}원")
        c4.metric("총 수익률", f"{total_pct:+.2f}%")

        if st.button("포트폴리오 초기화", key="reset_btn"):
            st.session_state.portfolio = []
            st.rerun()

elif page == "환율":
    st.title("환율")

    CURRENCIES = {
        "원 (KRW)": "KRW",
        "달러 (USD)": "USD",
        "엔 (JPY)": "JPY",
        "유로 (EUR)": "EUR",
        "위안 (CNY)": "CNY",
        "캐나다 달러 (CAD)": "CAD",
        "파운드 (GBP)": "GBP",
        "호주 달러 (AUD)": "AUD",
        "홍콩 달러 (HKD)": "HKD",
        "싱가포르 달러 (SGD)": "SGD",
    }

    CURRENCY_SYMBOLS = {
        "KRW": "₩", "USD": "$", "JPY": "¥",
        "EUR": "€", "CNY": "¥", "CAD": "CA$",
        "GBP": "£", "AUD": "A$", "HKD": "HK$", "SGD": "S$"
    }

    def get_rate(from_cur, to_cur):
        if from_cur == to_cur:
            return 1.0
        try:
            ticker = f"{from_cur}{to_cur}=X"
            t = yf.Ticker(ticker)
            hist = t.history(period="1d")
            if not hist.empty:
                return hist["Close"].iloc[-1]
            ticker2 = f"{to_cur}{from_cur}=X"
            t2 = yf.Ticker(ticker2)
            hist2 = t2.history(period="1d")
            if not hist2.empty:
                return 1 / hist2["Close"].iloc[-1]
        except:
            pass
        return None

    if "fx_data" not in st.session_state:
        with st.spinner("환율 불러오는 중..."):
            fx_pairs = {
                "USD/KRW": "USDKRW=X",
                "JPY/KRW": "JPYKRW=X",
                "EUR/KRW": "EURKRW=X",
                "CNY/KRW": "CNYKRW=X",
            }
            fx_data = {}
            for name, ticker in fx_pairs.items():
                try:
                    t = yf.Ticker(ticker)
                    hist = t.history(period="2d")
                    if not hist.empty:
                        current = hist["Close"].iloc[-1]
                        prev = hist["Close"].iloc[-2] if len(hist) > 1 else current
                        fx_data[name] = {"current": current, "prev": prev}
                except:
                    pass
            st.session_state.fx_data = fx_data

    fx_data = st.session_state.fx_data
    cols = st.columns(4)
    for i, (name, data) in enumerate(fx_data.items()):
        change = data["current"] - data["prev"]
        change_pct = (change / data["prev"]) * 100
        cols[i].metric(name, f"{data['current']:,.2f}원", f"{change_pct:+.2f}%")

    st.markdown("---")
    st.subheader("환전 계산기")

    c1, c2, c3 = st.columns([2, 1.5, 1.5])
    with c1:
        amount_raw = st.text_input("금액", value="1,000", placeholder="예: 1,000,000")
        try:
            amount = float(amount_raw.replace(",", "").replace(" ", ""))
        except:
            amount = 0.0
        if amount_raw and "," not in amount_raw and len(amount_raw.replace(".", "")) > 3:
            formatted = f"{int(amount):,}" if amount == int(amount) else f"{amount:,.2f}"
            st.caption(f"입력값: {formatted}")
    with c2:
        from_label = st.selectbox("환전 전 통화", list(CURRENCIES.keys()), index=1)
    with c3:
        to_label = st.selectbox("환전 후 통화", list(CURRENCIES.keys()), index=0)

    from_cur = CURRENCIES[from_label]
    to_cur = CURRENCIES[to_label]
    from_sym = CURRENCY_SYMBOLS[from_cur]
    to_sym = CURRENCY_SYMBOLS[to_cur]
    from_name = from_label.split(" ")[0]
    to_name = to_label.split(" ")[0]

    rate = get_rate(from_cur, to_cur)
    if rate:
        result = amount * rate
        if to_cur == "KRW":
            result_str = f"{result:,.0f}"
        elif to_cur == "JPY":
            result_str = f"{result:,.0f}"
        else:
            result_str = f"{result:,.2f}"

        if from_cur == "KRW":
            amount_str = f"{amount:,.0f}"
        else:
            amount_str = f"{amount:,.2f}"

        st.markdown(f"""
        <div style="background:#f0f7ff; border-radius:12px; padding:24px 32px; margin-top:16px; text-align:center;">
            <span style="font-size:28px; font-weight:600; color:#1a1a2e;">
                {from_sym}{amount_str} {from_name}
            </span>
            <span style="font-size:24px; color:#888888; margin:0 16px;">→</span>
            <span style="font-size:28px; font-weight:600; color:#1a3a6e;">
                {to_sym}{result_str} {to_name}
            </span>
            <div style="margin-top:10px; font-size:13px; color:#aaaaaa;">
                1 {from_cur} = {rate:,.4f} {to_cur}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("환율 정보를 불러올 수 없습니다.")

elif page == "경제 캘린더":
    st.title("경제 캘린더")
    st.caption("🔴 중요도 상  🟡 중요도 중  🟢 중요도 하  |  기준 시각: 대한민국 표준시 (KST)")
    if "calendar_data" not in st.session_state:
        with st.spinner("경제 일정 불러오는 중..."):
            result = ask_perplexity("""
오늘 날짜 기준으로 가장 가까운 미래의 주요 글로벌 경제 지표 발표 일정 10개를 가까운 순서대로 한국어로 알려줘.
아래 형식으로 반드시 작성해줘.

규칙:
- 날짜는 반드시 'M월 D일 (요일) HH:MM' 형식으로 작성. 시간은 한국 표준시(KST) 기준. 예: 4월 9일 (목요일) 21:30
- 대괄호([]) 안의 숫자나 각주 표시 절대 포함하지 말 것
- 예상치가 있으면 포함, 없으면 생략

날짜: [M월 D일 (요일) HH:MM]
지표: [지표명]
국가: [국가]
중요도: [상/중/하]
설명: [한 줄 설명]
예상치: [예상 수치] (있을 때만)
---
""")
            st.session_state.calendar_data = result

    items = st.session_state.calendar_data.strip().split("---")
    for item in items:
        item = item.strip()
        if not item:
            continue
        lines = item.split("\n")
        date = indicator = country = importance = desc = forecast = ""
        for line in lines:
            if line.startswith("날짜:"):
                date = line.replace("날짜:", "").strip()
            elif line.startswith("지표:"):
                indicator = line.replace("지표:", "").strip()
            elif line.startswith("국가:"):
                country = line.replace("국가:", "").strip()
            elif line.startswith("중요도:"):
                importance = line.replace("중요도:", "").strip()
            elif line.startswith("설명:"):
                desc = line.replace("설명:", "").strip()
            elif line.startswith("예상치:"):
                forecast = line.replace("예상치:", "").strip()
        if indicator:
            color = "🔴" if importance == "상" else "🟡" if importance == "중" else "🟢"
            with st.expander(f"{color} {date} | {country} | {indicator}"):
                st.markdown(f"**설명:** {desc}")
                if forecast and forecast.strip() and forecast.strip() not in ["미정", ""]:
                    st.markdown(f"**예상치:** {forecast}")
                else:
                    st.markdown("**예상치:** -")