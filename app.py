import streamlit as st
import requests
import os
import yfinance as yf
import pandas as pd
import time
import hashlib
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
DART_API_KEY = os.getenv("DART_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GMAIL_USER   = os.getenv("GMAIL_USER", "")
GMAIL_APP_PW = os.getenv("GMAIL_APP_PW", "")

def send_alert_email(to_email, stock_name, target_price, direction, current_price):
    """목표가 도달 시 이메일 발송"""
    if not GMAIL_USER or not GMAIL_APP_PW or not to_email:
        return False
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        subject = f"[Finance App] {stock_name} 목표가 도달 알림"
        body = f"""
        <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px 24px;
            background:#f8f9fa;border-radius:12px;">
            <div style="font-size:20px;font-weight:800;color:#1a1e2e;margin-bottom:8px;">
                목표가 도달 알림
            </div>
            <div style="font-size:14px;color:#888;margin-bottom:24px;">Finance App</div>

            <div style="background:white;border-radius:10px;padding:20px 24px;
                border-left:4px solid #3182f6;margin-bottom:16px;">
                <div style="font-size:16px;font-weight:700;color:#1a1e2e;margin-bottom:12px;">
                    {stock_name}
                </div>
                <table style="width:100%;font-size:14px;color:#444;">
                    <tr>
                        <td style="padding:4px 0;color:#888;">현재가</td>
                        <td style="text-align:right;font-weight:700;color:#1a1e2e;">
                            {current_price:,.0f}원
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:4px 0;color:#888;">목표가</td>
                        <td style="text-align:right;font-weight:700;color:#3182f6;">
                            {target_price:,.0f}원 {direction}
                        </td>
                    </tr>
                </table>
            </div>

            <div style="font-size:13px;color:#aaa;text-align:center;margin-top:16px;">
                본 알림은 Finance App에서 자동 발송되었습니다.<br>
                투자 판단과 책임은 본인에게 있습니다.
            </div>
        </div>
        """

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = GMAIL_USER
        msg["To"]      = to_email
        msg.attach(MIMEText(body, "html", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PW)
            server.sendmail(GMAIL_USER, to_email, msg.as_string())
        return True
    except Exception as e:
        return False

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Finance Dashboard", page_icon="📈", layout="wide")

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def db_signup(username, password, email=""):
    try:
        existing = supabase.table("users").select("id").eq("username", username).execute()
        if existing.data:
            return False, "이미 사용 중인 아이디입니다."
        supabase.table("users").insert({
            "username": username,
            "password_hash": hash_pw(password),
            "email": email,
        }).execute()
        return True, "회원가입 완료!"
    except Exception as e:
        return False, str(e)

def db_login(username, password):
    try:
        res = supabase.table("users").select("*").eq("username", username).eq("password_hash", hash_pw(password)).execute()
        if res.data:
            return True, res.data[0]
        return False, None
    except Exception as e:
        return False, None

def db_load_portfolio(user_id):
    try:
        res = supabase.table("portfolio").select("*").eq("user_id", user_id).execute()
        return res.data or []
    except:
        return []

def db_save_portfolio_item(user_id, item):
    try:
        supabase.table("portfolio").insert({
            "user_id": user_id,
            "name": item["name"],
            "ticker": item["ticker"],
            "qty": item["qty"],
            "buy_price": item["buy_price"],
        }).execute()
        return True
    except:
        return False

def db_delete_portfolio_item(item_id):
    try:
        supabase.table("portfolio").delete().eq("id", item_id).execute()
        return True
    except:
        return False

def db_clear_portfolio(user_id):
    try:
        supabase.table("portfolio").delete().eq("user_id", user_id).execute()
        return True
    except:
        return False

# 세션 초기화
if "page" not in st.session_state:
    st.session_state.page = "홈"
if "portfolio" not in st.session_state:
    st.session_state.portfolio = []
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "login"
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

# ── 로그인 / 회원가입 화면 ─────────────────────────────────
if not st.session_state.authenticated:
    col1, col2, col3 = st.columns([1.2, 1, 1.2])
    with col2:
        st.markdown("""
        <div style="margin-top:80px; background:white; border:1px solid #e8eaed;
            border-radius:12px; padding:36px 32px; text-align:center;">
            <div style="font-size:20px; font-weight:700; color:#1a1e2e; margin-bottom:4px;">Finance App</div>
            <div style="font-size:13px; color:#888; margin-bottom:24px;">투자 정보 플랫폼</div>
        </div>
        """, unsafe_allow_html=True)

        tab_login, tab_signup = st.tabs(["로그인", "회원가입"])

        with tab_login:
            with st.form("login_form"):
                username = st.text_input("아이디", placeholder="아이디 입력")
                password = st.text_input("비밀번호", type="password", placeholder="비밀번호 입력")
                submitted = st.form_submit_button("로그인", use_container_width=True)
            if submitted:
                if username and password:
                    ok, user_data = db_login(username, password)
                    if ok:
                        st.session_state.authenticated = True
                        st.session_state.user = user_data
                        # DB에서 포트폴리오 로드
                        raw = db_load_portfolio(user_data["id"])
                        st.session_state.portfolio = [{
                            "id": r["id"],
                            "name": r["name"],
                            "ticker": r["ticker"],
                            "qty": r["qty"],
                            "buy_price": float(r["buy_price"]),
                        } for r in raw]
                        st.rerun()
                    else:
                        st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
                else:
                    st.warning("아이디와 비밀번호를 입력해주세요.")

        with tab_signup:
            with st.form("signup_form"):
                new_id   = st.text_input("아이디", placeholder="4자 이상")
                new_pw   = st.text_input("비밀번호", type="password", placeholder="6자 이상")
                new_pw2  = st.text_input("비밀번호 확인", type="password", placeholder="비밀번호 재입력")
                new_email = st.text_input("이메일 (알림용, 선택)", placeholder="example@email.com")
                signup_btn = st.form_submit_button("회원가입", use_container_width=True)
            if signup_btn:
                if not new_id or len(new_id) < 4:
                    st.error("아이디는 4자 이상이어야 합니다.")
                elif not new_pw or len(new_pw) < 6:
                    st.error("비밀번호는 6자 이상이어야 합니다.")
                elif new_pw != new_pw2:
                    st.error("비밀번호가 일치하지 않습니다.")
                else:
                    ok, msg = db_signup(new_id, new_pw, new_email)
                    if ok:
                        st.success(f"{msg} 로그인 탭에서 로그인해주세요.")
                    else:
                        st.error(msg)
    st.stop()


st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800&display=swap');

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container {padding-top: 0rem; padding-left: 2rem; padding-right: 2rem;}

    /* 전체 배경 & 폰트 */
    .stApp {
        background-color: #f2f4f6;
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    /* 네비 버튼 */
    div.stButton > button {
        background: transparent;
        border: none;
        color: #ffffff;
        font-size: 13px;
        font-weight: 500;
        padding: 6px 10px;
        border-radius: 6px;
        transition: all 0.15s ease;
        white-space: nowrap;
        letter-spacing: -0.2px;
    }
    div.stButton > button:hover {
        background: rgba(255,255,255,0.15);
        color: #ffffff;
        transform: translateY(-1px);
    }
    div.stButton > button:active {
        transform: translateY(0px);
    }

    /* 마이페이지 버튼만 따로 */
    div[data-testid="column"]:last-child div.stButton > button {
        background: rgba(255,255,255,0.12);
        border: 1px solid rgba(255,255,255,0.2);
        color: #ffffff;
        font-size: 12px;
        padding: 5px 12px;
        border-radius: 20px;
    }

    /* 카드 */
    .toss-card {
        background: #ffffff;
        border-radius: 16px;
        padding: 24px 24px;
        margin-bottom: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        transition: box-shadow 0.2s ease, transform 0.2s ease;
    }
    .toss-card:hover {
        box-shadow: 0 4px 20px rgba(0,0,0,0.10);
        transform: translateY(-2px);
    }

    /* 지표 카드 */
    .metric-card {
        background: #ffffff;
        border-radius: 16px;
        padding: 20px 22px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        transition: all 0.2s ease;
        height: 100%;
    }
    .metric-card:hover {
        box-shadow: 0 6px 24px rgba(0,0,0,0.10);
        transform: translateY(-2px);
    }
    .metric-label {
        font-size: 12px;
        font-weight: 600;
        color: #8b95a1;
        letter-spacing: 0.3px;
        margin-bottom: 8px;
        text-transform: uppercase;
    }
    .metric-value {
        font-size: 26px;
        font-weight: 800;
        color: #191f28;
        letter-spacing: -1px;
        line-height: 1.2;
    }
    .metric-change-up {
        font-size: 13px;
        font-weight: 600;
        color: #f04452;
        margin-top: 6px;
    }
    .metric-change-down {
        font-size: 13px;
        font-weight: 600;
        color: #1b64da;
        margin-top: 6px;
    }
    .metric-change-flat {
        font-size: 13px;
        font-weight: 600;
        color: #8b95a1;
        margin-top: 6px;
    }

    /* 제목 */
    h1 {
        font-size: 22px !important;
        font-weight: 800 !important;
        color: #191f28 !important;
        letter-spacing: -0.5px !important;
        margin-bottom: 4px !important;
    }
    h2 {font-size: 18px !important; font-weight: 700 !important; color: #191f28 !important; letter-spacing: -0.3px !important;}
    h3 {font-size: 15px !important; font-weight: 700 !important; color: #191f28 !important;}
    p {font-size: 14px !important; line-height: 1.7 !important; color: #333d4b !important;}
    .stMarkdown p {font-size: 14px !important;}
    td, th {font-size: 13px !important;}

    /* expander */
    details[data-testid="stExpander"] {
        background: #ffffff !important;
        border: none !important;
        border-radius: 12px !important;
        box-shadow: 0 1px 6px rgba(0,0,0,0.06) !important;
        margin-bottom: 8px !important;
        overflow: hidden;
    }
    details[data-testid="stExpander"] summary {
        padding: 14px 18px !important;
        border-radius: 12px !important;
        font-size: 14px !important;
        color: #191f28 !important;
    }
    details[data-testid="stExpander"] summary:hover {
        background: #f8f9fa !important;
    }

    /* 구분선 */
    hr {border: none; border-top: 1px solid #f2f4f6; margin: 20px 0;}

    /* metric 기본 컨테이너 */
    div[data-testid="metric-container"] {
        background: #ffffff;
        border: none;
        border-radius: 14px;
        padding: 18px 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    div[data-testid="metric-container"] label {
        font-size: 12px !important;
        font-weight: 600 !important;
        color: #8b95a1 !important;
        letter-spacing: 0.2px !important;
    }
    div[data-testid="metric-container"] [data-testid="metric-value"] {
        font-size: 22px !important;
        font-weight: 800 !important;
        color: #191f28 !important;
        letter-spacing: -0.5px !important;
    }

    /* 탭 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: #f2f4f6;
        border-radius: 10px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        font-size: 13px;
        font-weight: 600;
        color: #8b95a1;
        padding: 8px 16px;
        border: none !important;
    }
    .stTabs [aria-selected="true"] {
        background: #ffffff !important;
        color: #191f28 !important;
        box-shadow: 0 1px 4px rgba(0,0,0,0.08) !important;
    }

    /* 입력창 */
    .stTextInput > div > div > input {
        border: 1.5px solid #e5e8eb;
        border-radius: 10px;
        background: #ffffff;
        font-size: 14px;
        padding: 10px 14px;
        color: #191f28;
        transition: border-color 0.15s;
    }
    .stTextInput > div > div > input:focus {
        border-color: #3182f6;
        box-shadow: 0 0 0 3px rgba(49,130,246,0.12);
    }
    .stSelectbox > div > div {
        border: 1.5px solid #e5e8eb;
        border-radius: 10px;
        background: #ffffff;
        font-size: 14px;
    }
    .stNumberInput > div > div > input {
        border: 1.5px solid #e5e8eb;
        border-radius: 10px;
        font-size: 14px;
    }

    /* 데이터프레임 */
    .stDataFrame {
        border-radius: 12px;
        border: none !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        overflow: hidden;
    }

    /* 라디오 */
    .stRadio > div {
        gap: 8px;
    }
    .stRadio label {
        font-size: 13px !important;
        font-weight: 500 !important;
    }

    /* 일반 버튼 (submit 등) */
    div[data-testid="stForm"] button[kind="primaryFormSubmit"],
    div[data-testid="stForm"] button {
        background: #3182f6 !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-size: 14px !important;
        font-weight: 600 !important;
        padding: 10px 20px !important;
        transition: background 0.15s, transform 0.1s !important;
    }
    div[data-testid="stForm"] button:hover {
        background: #1b64da !important;
        transform: translateY(-1px) !important;
    }

    /* 스피너 - 텍스트 숨기고 아이콘만 */
    .stSpinner > div {
        border-top-color: #3182f6 !important;
    }
    [data-testid="stSpinner"] p,
    [data-testid="stSpinner"] span {
        display: none !important;
    }

    /* 캡션 */
    .stCaption, [data-testid="stCaptionContainer"] p {
        font-size: 12px !important;
        color: #8b95a1 !important;
    }

    /* 성공/에러 메시지 */
    .stSuccess {border-radius: 10px !important;}
    .stError {border-radius: 10px !important;}
    .stWarning {border-radius: 10px !important;}
    .stInfo {border-radius: 10px !important;}

    </style>
""", unsafe_allow_html=True)

# 다크모드 CSS 동적 주입
if st.session_state.dark_mode:
    st.markdown("""
    <style>
    /* 전체 배경 */
    .stApp, .block-container, section[data-testid="stSidebar"],
    [data-testid="stAppViewContainer"] {
        background-color: #0e1117 !important;
    }

    /* 모든 텍스트 기본 */
    .stApp, .stApp *, .block-container * {
        color: #e6edf3 !important;
    }

    /* 제목 */
    h1, h2, h3, h4, h5, h6 { color: #f0f6fc !important; }

    /* 본문 */
    p, span, label, div { color: #e6edf3 !important; }

    /* 캡션 */
    .stCaption p, [data-testid="stCaptionContainer"] p { color: #8b949e !important; }

    /* 카드 계열 */
    div[data-testid="metric-container"] {
        background: #161b22 !important;
        border: 1px solid #30363d !important;
    }
    div[data-testid="metric-container"] label,
    div[data-testid="metric-container"] [data-testid="stMetricLabel"] p {
        color: #8b949e !important;
    }
    div[data-testid="metric-container"] [data-testid="metric-value"],
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #f0f6fc !important;
    }

    /* 입력창 */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: #21262d !important;
        border: 1.5px solid #30363d !important;
        color: #e6edf3 !important;
    }
    .stTextInput > div > div > input::placeholder,
    .stNumberInput > div > div > input::placeholder {
        color: #6e7681 !important;
    }
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: #58a6ff !important;
        box-shadow: 0 0 0 3px rgba(88,166,255,0.15) !important;
    }

    /* 셀렉트박스 */
    .stSelectbox > div > div,
    .stSelectbox > div > div > div {
        background: #21262d !important;
        border: 1.5px solid #30363d !important;
        color: #e6edf3 !important;
    }
    .stSelectbox svg { fill: #8b949e !important; }

    /* 드롭다운 옵션 */
    ul[data-testid="stSelectboxVirtualDropdown"],
    li[role="option"] {
        background: #21262d !important;
        color: #e6edf3 !important;
    }
    li[role="option"]:hover { background: #30363d !important; }

    /* expander */
    details[data-testid="stExpander"] {
        background: #161b22 !important;
        border: 1px solid #30363d !important;
        box-shadow: none !important;
    }
    details[data-testid="stExpander"] summary,
    details[data-testid="stExpander"] summary p,
    details[data-testid="stExpander"] summary span {
        color: #e6edf3 !important;
        background: #161b22 !important;
    }
    details[data-testid="stExpander"] summary:hover {
        background: #21262d !important;
    }

    /* 탭 */
    .stTabs [data-baseweb="tab-list"] {
        background: #161b22 !important;
        border-color: #30363d !important;
    }
    .stTabs [data-baseweb="tab"] {
        color: #8b949e !important;
        background: transparent !important;
    }
    .stTabs [aria-selected="true"] {
        background: #21262d !important;
        color: #f0f6fc !important;
    }

    /* 버튼 */
    div.stButton > button {
        color: #e6edf3 !important;
        border: 1px solid #30363d !important;
        background: #21262d !important;
    }
    div.stButton > button:hover {
        background: #30363d !important;
        color: #f0f6fc !important;
    }
    div[data-testid="stForm"] button {
        background: #1f6feb !important;
        color: #ffffff !important;
        border: none !important;
    }
    div[data-testid="stForm"] button:hover {
        background: #388bfd !important;
    }

    /* 토글 */
    .stCheckbox label, .stRadio label { color: #e6edf3 !important; }

    /* 데이터프레임 */
    .stDataFrame, .stDataFrame * {
        background: #161b22 !important;
        color: #e6edf3 !important;
        border-color: #30363d !important;
    }

    /* 구분선 */
    hr { border-color: #30363d !important; }

    /* 티커 */
    .ticker-wrapper {
        background: #161b22 !important;
        border-color: #30363d !important;
    }
    .ticker-wrapper * { color: #e6edf3 !important; }

    /* 인라인 HTML 카드들 (white background) */
    div[style*="background:white"],
    div[style*="background: white"],
    div[style*="background:#ffffff"],
    div[style*="background: #ffffff"],
    div[style*="background:#fff"],
    div[style*="background: #fff"] {
        background: #161b22 !important;
        border-color: #30363d !important;
        color: #e6edf3 !important;
    }

    /* 인라인 HTML 텍스트 색상 강제 */
    div[style*="color:#1a1e2e"], div[style*="color: #1a1e2e"],
    div[style*="color:#191f28"], div[style*="color: #191f28"],
    div[style*="color:#333"], div[style*="color: #333"],
    div[style*="color:#444"], div[style*="color: #444"] {
        color: #e6edf3 !important;
    }
    div[style*="color:#888"], div[style*="color: #888"],
    div[style*="color:#666"], div[style*="color: #666"] {
        color: #8b949e !important;
    }

    /* 성공/에러/경고 메시지 */
    .stSuccess { background: #1a2f1a !important; color: #56d364 !important; }
    .stError   { background: #2f1a1a !important; color: #f85149 !important; }
    .stWarning { background: #2f2a1a !important; color: #e3b341 !important; }
    .stInfo    { background: #1a1f2f !important; color: #79c0ff !important; }

    /* 배경 f2f4f6 계열 */
    div[style*="background:#f2f4f6"], div[style*="background:#f5f6f8"],
    div[style*="background:#f8f9fa"], div[style*="background:#f0f7ff"] {
        background: #0d1117 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 헤더 + 네비게이션 통합
st.markdown("""
<div style="
    background: #191f28;
    padding: 0 28px;
    display: flex;
    align-items: center;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    position: sticky; top: 0; z-index: 999;
">
    <span style="color:white; font-size:16px; font-weight:800;
        letter-spacing:-0.5px; padding: 16px 0; margin-right:32px;
        white-space:nowrap;">
        Finance
        <span style="color:#3182f6;">App</span>
    </span>
</div>
""", unsafe_allow_html=True)

# 마이페이지 버튼
_hc1, _hc2 = st.columns([9, 1])
with _hc2:
    if st.button("마이페이지", key="mypage_btn"):
        st.session_state.page = "마이페이지"
        st.rerun()

# 네비게이션 바
st.markdown("""
<div style="
    background: #191f28;
    padding: 0px 20px 6px 20px;
    border-bottom: 1px solid rgba(255,255,255,0.08);
">
""", unsafe_allow_html=True)

def clear_cache_except(keep_page):
    pass  # TTL 기반 캐시로 전환 - 탭 전환 시 삭제 안 함


cols = st.columns([1,1,1,1,1,1,1,1,1,1])
with cols[0]:
    if st.button("홈"):
        st.session_state.page = "홈"
        clear_cache_except("홈")
        st.rerun()
with cols[1]:
    if st.button("기업 분석"):
        st.session_state.page = "기업 분석"
        clear_cache_except("기업 분석")
        st.rerun()
with cols[2]:
    if st.button("뉴스"):
        st.session_state.page = "뉴스"
        clear_cache_except("뉴스")
        st.rerun()
with cols[3]:
    if st.button("국제 금융"):
        st.session_state.page = "국제 금융"
        clear_cache_except("국제 금융")
        st.rerun()
with cols[4]:
    if st.button("실시간 주가"):
        st.session_state.page = "실시간 주가"
        clear_cache_except("실시간 주가")
        st.rerun()
with cols[5]:
    if st.button("포트폴리오"):
        st.session_state.page = "포트폴리오"
        clear_cache_except("포트폴리오")
        st.rerun()
with cols[6]:
    if st.button("환율"):
        st.session_state.page = "환율"
        clear_cache_except("환율")
        st.rerun()
with cols[7]:
    if st.button("경제 캘린더"):
        st.session_state.page = "경제 캘린더"
        clear_cache_except("경제 캘린더")
        st.rerun()
with cols[8]:
    if st.button("AI 추천"):
        st.session_state.page = "AI 추천"
        clear_cache_except("AI 추천")
        st.rerun()
with cols[9]:
    if st.button("서비스 안내"):
        st.session_state.page = "서비스 안내"
        clear_cache_except("서비스 안내")
        st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

# ── 실시간 티커 슬라이더 ─────────────────────────────────────
@st.cache_data(ttl=60)
def get_ticker_banner_data():
    import concurrent.futures
    _syms = [
        ("KOSPI","^KS11"),("KOSDAQ","^KQ11"),
        ("USD/KRW","USDKRW=X"),("EUR/KRW","EURKRW=X"),
        ("JPY/KRW","JPYKRW=X"),("WTI","CL=F"),
        ("나스닥","^IXIC"),("S&P500","^GSPC"),("다우","^DJI"),
    ]
    def _fetch(args):
        name, sym = args
        try:
            h = yf.Ticker(sym).history(period="2d")
            if not h.empty:
                cur  = h["Close"].iloc[-1]
                prev = h["Close"].iloc[-2] if len(h) >= 2 else cur
                chg  = cur - prev
                pct  = chg / prev * 100
                return name, (cur, chg, pct)
        except:
            pass
        return name, None

    td = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=9) as ex:
        for name, result in ex.map(_fetch, _syms):
            if result:
                td[name] = result
    return td

# 티커 배너: session_state에 없을 때만 호출 (탭 전환 시 재호출 방지)
if "ticker_banner_cache" not in st.session_state:
    st.session_state.ticker_banner_cache = get_ticker_banner_data()
_ticker_banner = st.session_state.ticker_banner_cache

_ticker_items = []
for _name, (_cur, _chg, _pct) in _ticker_banner.items():
    _color = "#ff4d4f" if _chg >= 0 else "#4096ff"
    _arrow = "▲" if _chg >= 0 else "▼"
    if _name in ("KOSPI", "KOSDAQ", "나스닥", "S&P500", "다우"):
        _val = f"{_cur:,.2f}"
    elif _name in ("USD/KRW", "EUR/KRW", "JPY/KRW"):
        _val = f"{_cur:,.2f}원"
    else:
        _val = f"${_cur:,.2f}"
    _items_html = (
        f"<span style='margin-right:8px;color:#444;font-size:15px;font-weight:600;'>{_name}</span>"
        f"<span style='font-weight:800;font-size:18px;color:#000000;margin-right:6px;'>{_val}</span>"
        f"<span style='color:{_color};font-size:15px;font-weight:700;'>{_arrow} {abs(_pct):.2f}%</span>"
    )
    _ticker_items.append(f"<span style='display:inline-block;padding:0 32px;white-space:nowrap;'>{_items_html}</span>")

_ticker_html = "".join(_ticker_items * 3)  # 3번 반복으로 루프 자연스럽게

st.markdown(f"""
<style>
@keyframes ticker-scroll {{
    0%   {{ transform: translateX(0); }}
    100% {{ transform: translateX(-33.333%); }}
}}
.ticker-wrapper {{
    background: #ffffff;
    border-bottom: 1px solid #e8eaed;
    overflow: hidden;
    white-space: nowrap;
    padding: 10px 0;
    cursor: default;
}}
.ticker-track {{
    display: inline-block;
    animation: ticker-scroll 40s linear infinite;
    white-space: nowrap;
}}
.ticker-wrapper:hover .ticker-track {{
    animation-play-state: paused;
}}
</style>
<div class="ticker-wrapper">
    <div class="ticker-track">
        {_ticker_html}
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

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

@st.cache_data(ttl=60)  # 1분 캐시 - 1분봉 데이터로 적시성 유지
def get_stock_data(tickers):
    """
    KRX 공식 API (1차) + yfinance 병렬 (2차 fallback)
    화면이 먼저 뜨도록 타임아웃 강제 적용
    """
    import concurrent.futures, time

    names = [t[0] for t in tickers]
    syms  = [t[1] for t in tickers]
    result_map = {}  # sym → dict

    # ── 1차: KRX 공식 API (빠름, 국내 전용) ───────────────────
    def _fetch_krx(sym):
        """KRX 시세 API - yfinance보다 빠르고 안정적"""
        code = sym.replace(".KS","").replace(".KQ","")
        try:
            import datetime
            today = datetime.date.today().strftime("%Y%m%d")
            r = requests.post(
                "https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd",
                data={
                    "bld": "dbms/MDC/STAT/standard/MDCSTAT01501",
                    "mktId": "STK", "trdDd": today,
                    "share": "1", "money": "1", "csvxls_isNo": "false"
                },
                headers={"Referer": "https://data.krx.co.kr", "User-Agent": "Mozilla/5.0"},
                timeout=3
            )
            if r.status_code == 200:
                rows = r.json().get("OutBlock_1", [])
                for row in rows:
                    if row.get("ISU_SRT_CD") == code:
                        cur  = float(str(row.get("TDD_CLSPRC","0")).replace(",",""))
                        prev = float(str(row.get("PRV_DD_CLSPRC","0")).replace(",",""))
                        if cur > 0:
                            chg  = cur - prev
                            pct  = chg / prev * 100 if prev else 0
                            arrow = "▲" if chg >= 0 else "▼"
                            return sym, {"종목": None, "현재가": f"{cur:,.0f}원",
                                        "등락": f"{arrow} {abs(chg):,.0f}원",
                                        "등락률": f"{pct:+.2f}%"}
        except:
            pass
        return sym, None

    # ── 2차: yfinance 1분봉 병렬 (KRX 실패 종목 처리) ─────────
    def _fetch_yf_1min(sym):
        try:
            h = yf.Ticker(sym).history(period="1d", interval="1m", timeout=5)
            if not h.empty and len(h) >= 2:
                cur  = float(h["Close"].iloc[-1])
                prev = float(h["Open"].iloc[0])
                chg  = cur - prev
                pct  = chg / prev * 100 if prev else 0
                arrow = "▲" if chg >= 0 else "▼"
                return sym, {"종목": None, "현재가": f"{cur:,.0f}원",
                            "등락": f"{arrow} {abs(chg):,.0f}원",
                            "등락률": f"{pct:+.2f}%"}
        except:
            pass
        # 3차: 일봉 fallback
        try:
            h = yf.Ticker(sym).history(period="5d", interval="1d", timeout=5)
            if not h.empty and len(h) >= 2:
                h = h.dropna(subset=["Close"])
                cur  = float(h["Close"].iloc[-1])
                prev = float(h["Close"].iloc[-2])
                chg  = cur - prev
                pct  = chg / prev * 100 if prev else 0
                arrow = "▲" if chg >= 0 else "▼"
                return sym, {"종목": None, "현재가": f"{cur:,.0f}원",
                            "등락": f"{arrow} {abs(chg):,.0f}원",
                            "등락률": f"{pct:+.2f}%"}
        except:
            pass
        return sym, None

    # KRX 먼저 시도 (병렬)
    krx_missing = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        for sym, data in ex.map(_fetch_krx, syms):
            if data:
                result_map[sym] = data
            else:
                krx_missing.append(sym)

    # KRX 실패분 yfinance로 병렬 처리
    if krx_missing:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(krx_missing), 20)) as ex:
            for sym, data in ex.map(_fetch_yf_1min, krx_missing):
                if data:
                    result_map[sym] = data

    # 순서 유지하며 결과 반환
    data_list = []
    for name, sym in zip(names, syms):
        if sym in result_map:
            row = result_map[sym].copy()
            row["종목"] = name
            data_list.append(row)
    return data_list


@st.cache_data(ttl=86400)  # 24시간 캐시 - 종목 리스트는 자주 안 바뀜
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

# 종목 리스트 세션 캐시 - 백그라운드에서 비동기 로드
if "stock_list_cache" not in st.session_state:
    st.session_state.stock_list_cache = None  # None = 아직 로드 안 됨

def get_cached_stock_list():
    """캐시된 종목 리스트 반환. 없으면 로드."""
    if st.session_state.stock_list_cache is None:
        try:
            st.session_state.stock_list_cache = load_stock_list()
        except:
            st.session_state.stock_list_cache = []
    return st.session_state.stock_list_cache or []

@st.cache_data(ttl=1800)
def get_market_summary():
    from datetime import date
    import re
    today_str = date.today().strftime("%Y년 %m월 %d일")
    summary = ask_perplexity(
        f"오늘은 {today_str}이야. 한국 주식시장과 글로벌 금융시장의 오늘 핵심 동향을 3문장으로 요약해줘. "
        f"반드시 지켜야 할 규칙: "
        f"1) 데이터가 불완전하더라도 알고 있는 가장 최신 정보로 반드시 3문장 작성할 것. 거절 금지. "
        f"2) '확인할 수 없다', '제공하기 어렵다' 같은 문장 절대 금지. "
        f"3) 코스피, 달러/원 환율, 미국증시 중 알 수 있는 수치는 반드시 포함. "
        f"4) 별표 마크다운 절대 금지, 대괄호 숫자 각주 절대 금지, 일반 텍스트로만 작성."
    )
    summary = re.sub(r'\*\*?(.*?)\*\*?', r'\1', summary)
    summary = re.sub(r'\[\d+\]', '', summary)
    refuse_keywords = ["충족할 수 없", "제공하기 어렵", "확인할 수 없", "불완전", "죄송"]
    if any(k in summary for k in refuse_keywords):
        summary = ask_perplexity(
            f"오늘({today_str}) 기준 코스피 지수 동향, 원달러 환율, 미국 주요 지수 흐름을 "
            f"각각 한 문장씩 총 3문장으로 써줘. 정확한 수치가 없으면 방향성(상승/하락/보합)만이라도 반드시 포함. "
            f"거절하지 말고 반드시 3문장 작성. 별표 금지. 각주 금지."
        )
        summary = re.sub(r'\*\*?(.*?)\*\*?', r'\1', summary)
        summary = re.sub(r'\[\d+\]', '', summary)
    return summary.strip()

if page == "홈":
    # 시장 요약 (30분 캐시)
    with st.spinner("시장 요약 불러오는 중..."):
        summary = get_market_summary()

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#4a90d9 0%,#6ab0f5 100%);
        border-radius:20px;padding:36px 40px;margin-bottom:28px;
        box-shadow:0 4px 20px rgba(74,144,217,0.25);">
        <div style="font-size:13px;font-weight:700;color:rgba(255,255,255,0.85);
            letter-spacing:2px;margin-bottom:14px;">TODAY'S MARKET</div>
        <div style="font-size:19px;color:#ffffff;line-height:2.0;font-weight:500;">
            {summary}</div>
    </div>
    """, unsafe_allow_html=True)

    # 시총 상위 5 카드
    st.markdown("""
    <div style="font-size:18px;font-weight:700;color:#191f28;
        margin-bottom:16px;letter-spacing:-0.3px;">시총 상위 5 종목</div>
    """, unsafe_allow_html=True)

    LOGO_MAP = {
        "삼성전자":      "https://www.google.com/s2/favicons?domain=samsung.com&sz=64",
        "SK하이닉스":    "https://www.google.com/s2/favicons?domain=skhynix.com&sz=64",
        "LG에너지솔루션": "https://www.google.com/s2/favicons?domain=lgenergysolution.com&sz=64",
        "삼성바이오로직스":"https://www.google.com/s2/favicons?domain=samsungbiologics.com&sz=64",
        "현대차":        "https://www.google.com/s2/favicons?domain=hyundai.com&sz=64",
    }

    top5 = KOSPI_TOP[:5]
    mini_data = get_stock_data(top5)

    if mini_data:
        cols = st.columns(5)
        for i, (item, (name, ticker)) in enumerate(zip(mini_data, top5)):
            cur   = item["현재가"]
            chg   = item["등락"]
            pct   = item["등락률"]
            is_up = "▲" in chg
            chg_color = "#e03131" if is_up else "#1971c2"
            logo_url = LOGO_MAP.get(name, "")
            logo_tag = (
                f"<img src='{logo_url}' style='width:34px;height:34px;border-radius:8px;"
                f"object-fit:cover;margin-right:10px;vertical-align:middle;flex-shrink:0;'"
                f" onerror=\"this.outerHTML='<div style=&quot;width:34px;height:34px;border-radius:8px;"
                f"background:#e8eaed;display:flex;align-items:center;justify-content:center;"
                f"font-size:14px;font-weight:700;color:#555;margin-right:10px;flex-shrink:0;&quot;>"
                f"{name[0]}</div>'\">"
                if logo_url else
                f"<div style='width:34px;height:34px;border-radius:8px;background:#e8eaed;"
                f"display:flex;align-items:center;justify-content:center;"
                f"font-size:14px;font-weight:700;color:#555;margin-right:10px;flex-shrink:0;'>"
                f"{name[0]}</div>"
            )
            cols[i].markdown(f"""
            <div style="background:white;border-radius:16px;padding:22px 18px;
                box-shadow:0 2px 10px rgba(0,0,0,0.07);height:100%;">
                <div style="display:flex;align-items:center;margin-bottom:14px;">
                    {logo_tag}
                    <span style="font-size:15px;font-weight:700;color:#191f28;
                        overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{name}</span>
                </div>
                <div style="font-size:24px;font-weight:800;color:#191f28;
                    letter-spacing:-0.5px;margin-bottom:6px;">{cur}</div>
                <div style="font-size:14px;font-weight:600;color:{chg_color};">
                    {chg} ({pct})</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:36px'></div>", unsafe_allow_html=True)

    # 오늘 주목할 숫자 (tooltip i 버튼 포함)
    st.markdown("""
    <style>
    .stat-tooltip { position:relative; display:inline-block; }
    .stat-tooltip .tip-icon {
        display:inline-flex; align-items:center; justify-content:center;
        width:16px; height:16px; border-radius:50%;
        background:#d0d7de; color:#444; font-size:10px; font-weight:700;
        cursor:pointer; margin-left:5px; vertical-align:middle;
        flex-shrink:0;
    }
    .stat-tooltip .tip-box {
        visibility:hidden; opacity:0;
        background:#1a1e2e; color:#fff; font-size:12px; line-height:1.6;
        border-radius:8px; padding:10px 14px;
        position:absolute; z-index:999; bottom:130%; left:50%;
        transform:translateX(-50%);
        width:200px; text-align:center;
        box-shadow:0 4px 12px rgba(0,0,0,0.25);
        transition:opacity 0.2s;
        pointer-events:none;
    }
    .stat-tooltip:hover .tip-box { visibility:visible; opacity:1; }
    </style>
    <div style="font-size:18px;font-weight:700;color:#191f28;
        margin-bottom:16px;letter-spacing:-0.3px;">오늘 주목할 숫자</div>
    """, unsafe_allow_html=True)

    STAT_INFO = {
        "공포탐욕지수": "CNN이 산출하는 시장 심리 지수. 0에 가까울수록 극단적 공포(매수 기회), 100에 가까울수록 극단적 탐욕(과열 신호).",
        "VIX 변동성":   "S&P500 옵션 가격으로 산출하는 '시장 공포 지수'. 20 이하면 안정적, 30 이상이면 시장 불안이 높은 상태.",
        "금 현물가":    "안전자산 대표 지표. 달러 약세·경기 불안 시 상승. 달러/온스 단위.",
        "비트코인":     "가상자산 시장 대표 지표. 위험자산 선호 심리와 연동되며 변동성이 매우 큼.",
        "미국 국채금리": "미국 10년물 국채 수익률. 금리가 오르면 주식·채권 가격 하락 압력. 전 세계 금융시장의 기준점.",
        "달러인덱스":   "주요 6개국 통화 대비 달러 강도(DXY). 달러가 강할수록 원/달러 환율 상승, 신흥국 자산에 부담.",
    }

    # yfinance로 직접 가져올 수 있는 데이터
    def _safe_yf(sym, fmt="{:.2f}"):
        try:
            h = yf.Ticker(sym).history(period="2d")
            if not h.empty:
                return fmt.format(h["Close"].iloc[-1])
        except:
            pass
        return None

    vix_val  = _safe_yf("^VIX", "{:.1f}")
    gold_val = _safe_yf("GC=F", "{:,.0f}")
    btc_val  = _safe_yf("BTC-USD", "{:,.0f}")
    bond_val = _safe_yf("^TNX", "{:.2f}")
    dxy_val  = _safe_yf("DX-Y.NYB", "{:.2f}")

    # AI로 공포탐욕지수만 조회
    fear_val = "-"
    try:
        from datetime import date as _fd
        _today = _fd.today().strftime("%Y.%m.%d")
        _fr = ask_perplexity(
            f"오늘({_today}) CNN 공포탐욕지수(Fear & Greed Index) 현재 수치를 숫자만 답해줘. "
            f"예: 42 이런 식으로 숫자만. 마크다운 금지. 각주 금지."
        ).strip()
        import re as _re2
        _m = _re2.search(r'\d+', _fr)
        if _m:
            fear_val = _m.group()
    except:
        pass

    stat_items = [
        ("공포탐욕지수", fear_val if fear_val != "-" else "조회중"),
        ("VIX 변동성",   vix_val  or "조회중"),
        ("금 현물가",    (gold_val + "$") if gold_val else "조회중"),
        ("비트코인",     ("$" + btc_val)  if btc_val  else "조회중"),
        ("미국 국채금리",(bond_val + "%") if bond_val else "조회중"),
        ("달러인덱스",   dxy_val  or "조회중"),
    ]

    stat_cols = st.columns(6)
    for i, (label, val) in enumerate(stat_items):
        tip = STAT_INFO.get(label, "")
        tip_html = (
            f"<div class='stat-tooltip'>"
            f"<span class='tip-icon'>i</span>"
            f"<div class='tip-box'>{tip}</div>"
            f"</div>"
        ) if tip else ""
        stat_cols[i].markdown(f"""
        <div style="background:white;border-radius:14px;padding:22px 14px;
            box-shadow:0 2px 8px rgba(0,0,0,0.06);text-align:center;">
            <div style="display:flex;align-items:center;justify-content:center;
                font-size:15px;color:#555;font-weight:700;
                letter-spacing:-0.2px;margin-bottom:12px;">
                {label}{tip_html}
            </div>
            <div style="font-size:28px;font-weight:800;color:#191f28;
                letter-spacing:-0.5px;">{val}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:36px'></div>", unsafe_allow_html=True)

    # 오늘의 금융 뉴스 카드
    st.markdown("""
    <div style="font-size:18px;font-weight:700;color:#191f28;
        margin-bottom:16px;letter-spacing:-0.3px;">오늘의 금융 뉴스</div>
    """, unsafe_allow_html=True)

    @st.cache_data(ttl=1800)
    def get_home_news():
        import re as _re
        from datetime import date as _d
        today = _d.today().strftime("%Y.%m.%d")
        result = ask_perplexity(
            f"오늘({today}) 금융·경제 분야 주요 뉴스 6개를 아래 형식으로 작성해줘. 구분자 ===.\n\n"
            f"제목: 뉴스 제목 (25자 이내로 간결하게)\n"
            f"분야: 증시/환율/원자재/기업/정책/해외증시 중 하나\n"
            f"요약: 2~3문장 핵심 내용\n"
            f"===\n"
            f"규칙: 대괄호 숫자 각주 금지. 별표 마크다운 금지."
        )
        result = _re.sub(r'\[\d+\]', '', result)
        result = _re.sub(r'\*\*?(.*?)\*\*?', r'\1', result)
        return result

    with st.spinner("오늘의 뉴스 불러오는 중..."):
        home_news_raw = get_home_news()

    news_items_home = [x.strip() for x in home_news_raw.split("===") if x.strip()]

    CATEGORY_COLORS = {
        "증시": "#3182f6", "환율": "#6366f1", "원자재": "#f97316",
        "기업": "#22c55e", "정책": "#e03131", "해외증시": "#0ea5e9",
    }

    news_cols1 = st.columns(3)
    news_cols2 = st.columns(3)
    all_news_cols = news_cols1 + news_cols2

    for i, item in enumerate(news_items_home[:6]):
        fields = {}
        for line in item.split("\n"):
            line = line.strip()
            for k in ["제목", "분야", "요약"]:
                if line.startswith(f"{k}:"):
                    fields[k] = line.replace(f"{k}:", "").strip()
        title = fields.get("제목", "")
        cat   = fields.get("분야", "기타")
        desc  = fields.get("요약", "")
        if not title:
            continue
        color = CATEGORY_COLORS.get(cat, "#888")
        all_news_cols[i].markdown(f"""
        <div style="background:white;border-radius:16px;padding:22px 20px;
            box-shadow:0 2px 10px rgba(0,0,0,0.07);
            border-top:4px solid {color};margin-bottom:14px;">
            <div style="display:inline-block;font-size:12px;font-weight:700;
                color:{color};background:{color}18;
                padding:3px 10px;border-radius:20px;margin-bottom:12px;">{cat}</div>
            <div style="font-size:16px;font-weight:700;color:#191f28;
                line-height:1.6;margin-bottom:10px;">{title}</div>
            <div style="font-size:14px;color:#555;line-height:1.75;">{desc}</div>
        </div>
        """, unsafe_allow_html=True)


elif page == "마이페이지":
    import re as _re

    user = st.session_state.user or {}
    username = user.get("username", "")
    email = user.get("email", "") or ""
    slack = user.get("slack_webhook", "") or ""

    st.title("마이페이지")
    st.markdown(f"<div style='font-size:14px;color:#888;margin-bottom:24px;'>안녕하세요, <b style='color:#1a1e2e;'>{username}</b>님</div>", unsafe_allow_html=True)

    mp_tab1, mp_tab2, mp_tab3, mp_tab4 = st.tabs(["내 정보", "비밀번호 변경", "알림 설정", "서비스 안내"])

    # ── 내 정보 ────────────────────────────────────────────────
    with mp_tab1:
        st.markdown("#### 계정 정보")
        st.markdown(f"""
        <div style='background:white;border:1px solid #e8eaed;border-radius:8px;padding:20px 24px;margin-bottom:16px;'>
            <div style='font-size:13px;color:#888;margin-bottom:4px;'>아이디</div>
            <div style='font-size:16px;font-weight:600;color:#1a1e2e;'>{username}</div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("update_info_form"):
            new_email = st.text_input("이메일", value=email, placeholder="알림 수신용 이메일")
            save_btn = st.form_submit_button("저장", use_container_width=False)
        if save_btn:
            try:
                supabase.table("users").update({"email": new_email}).eq("id", user["id"]).execute()
                st.session_state.user["email"] = new_email
                st.success("이메일이 저장되었습니다.")
            except:
                st.error("저장 중 오류가 발생했습니다.")

        st.markdown("---")
        st.markdown("#### 화면 설정")
        dark_toggle = st.toggle("다크모드", value=st.session_state.dark_mode, key="dark_toggle")
        if dark_toggle != st.session_state.dark_mode:
            st.session_state.dark_mode = dark_toggle
            st.rerun()

        st.markdown("---")
        st.markdown("#### 포트폴리오 요약")
        pf = st.session_state.portfolio
        if pf:
            st.markdown(f"보유 종목 수: **{len(pf)}개**")
            total_inv = sum(p["buy_price"] * p["qty"] for p in pf)
            st.markdown(f"총 투자금액: **{total_inv:,.0f}원**")
        else:
            st.info("등록된 포트폴리오가 없습니다.")

        st.markdown("---")
        if st.button("로그아웃", key="logout_mypage"):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.session_state.portfolio = []
            st.rerun()

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        with st.expander("⚠️ 계정 탈퇴"):
            st.warning("탈퇴 시 모든 데이터가 영구 삭제됩니다.")
            confirm = st.text_input("탈퇴하려면 아이디를 입력하세요", key="withdraw_confirm")
            if st.button("탈퇴 확인", key="withdraw_btn"):
                if confirm == username:
                    try:
                        supabase.table("portfolio").delete().eq("user_id", user["id"]).execute()
                        supabase.table("price_alerts").delete().eq("user_id", user["id"]).execute()
                        supabase.table("users").delete().eq("id", user["id"]).execute()
                        st.session_state.authenticated = False
                        st.session_state.user = None
                        st.session_state.portfolio = []
                        st.rerun()
                    except:
                        st.error("탈퇴 처리 중 오류가 발생했습니다.")
                else:
                    st.error("아이디가 일치하지 않습니다.")

    # ── 비밀번호 변경 ───────────────────────────────────────────
    with mp_tab2:
        st.markdown("#### 비밀번호 변경")
        with st.form("change_pw_form"):
            cur_pw  = st.text_input("현재 비밀번호", type="password")
            new_pw  = st.text_input("새 비밀번호 (6자 이상)", type="password")
            new_pw2 = st.text_input("새 비밀번호 확인", type="password")
            pw_btn  = st.form_submit_button("변경", use_container_width=False)
        if pw_btn:
            if not cur_pw or not new_pw:
                st.error("모든 항목을 입력해주세요.")
            elif new_pw != new_pw2:
                st.error("새 비밀번호가 일치하지 않습니다.")
            elif len(new_pw) < 6:
                st.error("비밀번호는 6자 이상이어야 합니다.")
            else:
                try:
                    check = supabase.table("users").select("id").eq("id", user["id"]).eq("password_hash", hash_pw(cur_pw)).execute()
                    if check.data:
                        supabase.table("users").update({"password_hash": hash_pw(new_pw)}).eq("id", user["id"]).execute()
                        st.success("비밀번호가 변경되었습니다.")
                    else:
                        st.error("현재 비밀번호가 올바르지 않습니다.")
                except:
                    st.error("변경 중 오류가 발생했습니다.")

    # ── 알림 설정 ───────────────────────────────────────────────
    with mp_tab3:
        st.markdown("#### 목표가 알림 설정")

        # 이메일 상태 확인
        cur_email = st.session_state.user.get("email", "") or ""
        if not cur_email:
            st.warning("이메일 미등록 상태입니다. '내 정보' 탭에서 이메일을 먼저 등록해주세요.")
        else:
            st.caption(f"알림 수신 이메일: **{cur_email}**")
            # 테스트 발송 버튼
            test_col, _ = st.columns([1, 3])
            if test_col.button("테스트 이메일 발송", key="test_email_btn"):
                with st.spinner("발송 중..."):
                    ok = send_alert_email(cur_email, "테스트 종목", 50000, "이상", 52000)
                if ok:
                    st.success(f"✅ {cur_email} 으로 테스트 이메일이 발송됐습니다!")
                else:
                    st.error("❌ 발송 실패. .env의 GMAIL_USER / GMAIL_APP_PW를 확인해주세요.")

        st.markdown("---")

        stock_list_mp  = get_cached_stock_list()
        stock_names_mp = [s["name"] for s in stock_list_mp]
        stock_map_mp   = {s["name"]: s["ticker"] for s in stock_list_mp}

        with st.form("alert_form"):
            al_search = st.text_input("종목명 검색", placeholder="예: 삼성전자")
            al_col1, al_col2, al_col3 = st.columns(3)
            with al_col1:
                al_target = st.number_input("목표가 (원)", min_value=0, value=None, placeholder="예: 80000", step=100, format="%d")
            with al_col2:
                al_dir = st.selectbox("도달 조건", ["이상 (상승 목표)", "이하 (손절 목표)"])
            with al_col3:
                al_email = st.text_input("알림 이메일", value=email, placeholder="이메일 주소")
            al_btn = st.form_submit_button("알림 등록")

        al_selected = None
        if al_search:
            al_matched = [n for n in stock_names_mp if al_search.lower() in n.lower()]
            if al_matched:
                al_selected = st.selectbox("종목 선택", al_matched, key="al_select")

        if al_btn:
            if al_selected and al_target and al_target > 0:
                direction = "이상" if "이상" in al_dir else "이하"
                try:
                    ticker = stock_map_mp.get(al_selected, "")
                    supabase.table("price_alerts").insert({
                        "user_id": user["id"],
                        "name": al_selected,
                        "ticker": ticker,
                        "target_price": al_target,
                        "direction": direction,
                        "is_active": True,
                    }).execute()
                    st.success(f"{al_selected} {al_target:,}원 {direction} 알림이 등록되었습니다.")
                except:
                    st.error("등록 중 오류가 발생했습니다.")
            else:
                st.warning("종목과 목표가를 입력해주세요.")

        st.markdown("---")
        st.markdown("#### 등록된 알림 목록")
        try:
            alerts = supabase.table("price_alerts").select("*").eq("user_id", user["id"]).eq("is_active", True).execute().data or []
            if alerts:
                for al in alerts:
                    ac1, ac2, ac3, ac4 = st.columns([2, 1.5, 1.5, 0.5])
                    ac1.markdown(f"**{al['name']}**")
                    ac2.markdown(f"{float(al['target_price']):,.0f}원 {al['direction']}")
                    ac3.markdown(f"<span style='font-size:12px;color:#888;'>등록일: {str(al.get('created_at',''))[:10]}</span>", unsafe_allow_html=True)
                    if ac4.button("삭제", key=f"al_del_{al['id']}"):
                        supabase.table("price_alerts").update({"is_active": False}).eq("id", al["id"]).execute()
                        st.rerun()
            else:
                st.info("등록된 알림이 없습니다.")
        except:
            st.warning("알림 목록을 불러올 수 없습니다.")

    # ── 서비스 안내 ─────────────────────────────────────────────
    with mp_tab4:
        services_list = [
            ("기업 분석", "AI가 다트공시·뉴스·증권사 리포트를 통합 분석해 투자의견, 목표주가, 핵심 이슈를 제공합니다."),
            ("뉴스", "오늘의 주요 금융 뉴스를 AI가 요약해 제목만 보고 빠르게 파악하고, 클릭하면 전문을 확인할 수 있습니다."),
            ("국제 금융", "미국·중동·아시아 시장 동향, 환율 흐름, 주요 리스크 요인을 AI가 분석해 제공합니다."),
            ("실시간 주가", "코스피 시총 상위 100개 종목의 현재가와 등락률을 확인하고, 종목명으로 직접 검색할 수 있습니다."),
            ("포트폴리오", "보유 종목과 매수 평균가를 입력하면 현재가 기준 평가금액과 수익률을 자동으로 계산합니다."),
            ("환율", "주요 통화의 실시간 환율을 확인하고, 원하는 통화 간 환전 금액을 즉시 계산할 수 있습니다."),
            ("경제 캘린더", "이번 주 주요 글로벌 경제 지표 발표 일정을 중요도와 함께 확인할 수 있습니다."),
            ("AI 추천", "뉴스·공시·증권사 리포트를 AI가 종합 분석해 보수적 관점의 종목·섹터 추천을 제공합니다."),
        ]
        for name, desc in services_list:
            st.markdown(f"""
            <div style="background:white;border:1px solid #e8eaed;border-radius:8px;padding:16px 22px;margin-bottom:10px;display:flex;align-items:flex-start;gap:16px;">
                <div style="min-width:90px;font-size:13px;font-weight:600;color:#2563eb;">{name}</div>
                <div style="font-size:14px;color:#444;line-height:1.6;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)

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

    def get_corp_code(company_name):
        import zipfile, io, xml.etree.ElementTree as ET
        url = "https://opendart.fss.or.kr/api/corpCode.xml"
        params = {"crtfc_key": DART_API_KEY}
        res = requests.get(url, params=params)
        z = zipfile.ZipFile(io.BytesIO(res.content))
        xml_data = z.read("CORPCODE.xml")
        root = ET.fromstring(xml_data)
        for corp in root.findall("list"):
            name = corp.findtext("corp_name")
            code = corp.findtext("corp_code")
            stock_code = corp.findtext("stock_code")
            if name == company_name and stock_code and stock_code.strip():
                return code
        for corp in root.findall("list"):
            name = corp.findtext("corp_name")
            code = corp.findtext("corp_code")
            stock_code = corp.findtext("stock_code")
            if company_name in name and stock_code and stock_code.strip():
                return code
        return None

    def get_financial_data(corp_code):
        """최신 분기 → 반기 → 연간 순서로 탐색, 연도도 최신부터"""
        url = "https://opendart.fss.or.kr/api/fnlttSinglAcnt.json"
        # (연도, 보고서코드, 레이블) 우선순위 순
        candidates = []
        for year in ["2025", "2024"]:
            candidates += [
                (year, "11014", f"{year} 3분기"),
                (year, "11012", f"{year} 1분기"),
                (year, "11013", f"{year} 반기"),
                (year, "11011", f"{year} 연간"),
            ]
        for year, code, label in candidates:
            params = {
                "crtfc_key": DART_API_KEY,
                "corp_code": corp_code,
                "bsns_year": year,
                "reprt_code": code,
            }
            try:
                res = requests.get(url, params=params, timeout=6)
                data = res.json()
                if data.get("status") == "000" and data.get("list"):
                    return data.get("list", []), year, label
            except:
                continue
        return [], "2024", "연간"

    def get_annual_series(corp_code):
        """연간 3개년 데이터 (차트용)"""
        url = "https://opendart.fss.or.kr/api/fnlttSinglAcnt.json"
        results = {}
        for year in ["2025", "2024", "2023", "2022"]:
            try:
                params = {"crtfc_key": DART_API_KEY, "corp_code": corp_code,
                          "bsns_year": year, "reprt_code": "11011"}
                res = requests.get(url, params=params, timeout=6)
                data = res.json()
                if data.get("status") == "000" and data.get("list"):
                    results[year] = data["list"]
                    if len(results) >= 3:
                        break
            except:
                continue
        return results

    if submitted and company:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        import re
        import numpy as np

        # ── AI 분석 ─────────────────────────────────────────────────
        with st.spinner(f"{company} AI 분석 중..."):
            prompt = (
                f"{company}에 대해 다음 항목을 한국어로 분석해줘:\n"
                f"1. 투자의견 (매수/중립/매도)\n2. 목표주가 컨센서스\n"
                f"3. 핵심 이슈\n4. 최근 뉴스 요약\n5. 산업 분위기\n\n"
                f"규칙: 대괄호 각주 절대 금지. 별표 마크다운 사용 금지."
            )
            result = ask_perplexity(prompt)
            result = re.sub(r'\[\d+\]', '', result)
            result = re.sub(r'\*\*?(.*?)\*\*?', r'\1', result)

        st.markdown("### AI 투자 분석")
        st.markdown(result)
        st.markdown("---")

        # ── 주가 차트 + 기술적 지표 ─────────────────────────────────
        st.markdown("### 주가 차트 및 기술적 지표")
        with st.spinner(f"{company} 주가 데이터 불러오는 중..."):
            ticker_found = None
            hist_tech = pd.DataFrame()
            corp_code_for_ticker = get_corp_code(company)

            # DART corp_code → stock_code 매핑으로 ticker 찾기
            try:
                import zipfile, io, xml.etree.ElementTree as ET
                url_corp = "https://opendart.fss.or.kr/api/corpCode.xml"
                res_corp = requests.get(url_corp, params={"crtfc_key": DART_API_KEY}, timeout=10)
                z = zipfile.ZipFile(io.BytesIO(res_corp.content))
                xml_data = z.read("CORPCODE.xml")
                root_xml = ET.fromstring(xml_data)
                for corp in root_xml.findall("list"):
                    if corp.findtext("corp_name") == company:
                        sc = corp.findtext("stock_code", "").strip()
                        if sc:
                            for suffix in [".KS", ".KQ"]:
                                t = yf.Ticker(sc + suffix)
                                h = t.history(period="1y", interval="1d")
                                if not h.empty:
                                    hist_tech = h
                                    ticker_found = sc + suffix
                                    break
                        break
                if hist_tech.empty:
                    # 이름 포함 검색
                    for corp in root_xml.findall("list"):
                        if company in corp.findtext("corp_name", ""):
                            sc = corp.findtext("stock_code", "").strip()
                            if sc:
                                for suffix in [".KS", ".KQ"]:
                                    t = yf.Ticker(sc + suffix)
                                    h = t.history(period="1y", interval="1d")
                                    if not h.empty:
                                        hist_tech = h
                                        ticker_found = sc + suffix
                                        break
                            if not hist_tech.empty:
                                break
            except Exception as e:
                st.warning(f"주가 데이터 조회 실패: {e}")

        if not hist_tech.empty:
            close = hist_tech["Close"]
            volume = hist_tech["Volume"]
            high52 = close.rolling(252).max().iloc[-1]
            low52  = close.rolling(252).min().iloc[-1]
            current_price = close.iloc[-1]

            # RSI 계산
            delta = close.diff()
            gain  = delta.clip(lower=0).rolling(14).mean()
            loss  = (-delta.clip(upper=0)).rolling(14).mean()
            rs    = gain / loss.replace(0, float('nan'))
            rsi   = 100 - (100 / (1 + rs))

            # MACD 계산
            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            macd_line   = ema12 - ema26
            signal_line = macd_line.ewm(span=9, adjust=False).mean()
            macd_hist   = macd_line - signal_line

            # 52주 고저 카드
            w1, w2, w3, w4 = st.columns(4)
            w1.metric("현재가", f"{current_price:,.0f}원")
            w2.metric("52주 최고", f"{high52:,.0f}원")
            w3.metric("52주 최저", f"{low52:,.0f}원")
            pct_from_high = (current_price - high52) / high52 * 100
            w4.metric("고점 대비", f"{pct_from_high:.1f}%")

            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

            # 기간 선택
            period_opt = st.radio("기간", ["3개월", "6개월", "1년"], horizontal=True, key="tech_period")
            days_map = {"3개월": 63, "6개월": 126, "1년": 252}
            n = days_map[period_opt]
            idx = hist_tech.index[-n:]

            # subplot: 주가+거래량 / RSI / MACD
            fig_tech = make_subplots(
                rows=3, cols=1,
                shared_xaxes=True,
                row_heights=[0.55, 0.22, 0.23],
                vertical_spacing=0.04,
                subplot_titles=("주가 & 거래량", "RSI (14)", "MACD (12/26/9)")
            )

            # 주가 캔들
            fig_tech.add_trace(go.Candlestick(
                x=idx,
                open=hist_tech["Open"][-n:],
                high=hist_tech["High"][-n:],
                low=hist_tech["Low"][-n:],
                close=close[-n:],
                name="주가",
                increasing_line_color="#ef4444",
                decreasing_line_color="#3b82f6",
                increasing_fillcolor="#ef4444",
                decreasing_fillcolor="#3b82f6",
            ), row=1, col=1)

            # 이동평균선
            for ma_d, ma_col, ma_name in [(20,"#f97316","MA20"),(60,"#8b5cf6","MA60")]:
                ma = close.rolling(ma_d).mean()[-n:]
                fig_tech.add_trace(go.Scatter(
                    x=idx, y=ma, name=ma_name,
                    line=dict(color=ma_col, width=1.3, dash="dot"),
                    hovertemplate=f"{ma_name}: %{{y:,.0f}}원<extra></extra>"
                ), row=1, col=1)

            # 거래량
            vol_colors = ["#ef4444" if c >= o else "#3b82f6"
                          for c, o in zip(hist_tech["Close"][-n:], hist_tech["Open"][-n:])]
            fig_tech.add_trace(go.Bar(
                x=idx, y=volume[-n:], name="거래량",
                marker_color=vol_colors, opacity=0.6,
                yaxis="y2", showlegend=False,
            ), row=1, col=1)

            # RSI
            fig_tech.add_trace(go.Scatter(
                x=idx, y=rsi[-n:], name="RSI",
                line=dict(color="#6366f1", width=1.5),
                hovertemplate="RSI: %{y:.1f}<extra></extra>"
            ), row=2, col=1)
            for lvl, col in [(70,"#ef4444"),(30,"#22c55e")]:
                fig_tech.add_hline(y=lvl, line_dash="dash", line_color=col,
                                   line_width=1, row=2, col=1)

            # MACD
            fig_tech.add_trace(go.Scatter(
                x=idx, y=macd_line[-n:], name="MACD",
                line=dict(color="#0ea5e9", width=1.5)
            ), row=3, col=1)
            fig_tech.add_trace(go.Scatter(
                x=idx, y=signal_line[-n:], name="Signal",
                line=dict(color="#f97316", width=1.5, dash="dot")
            ), row=3, col=1)
            hist_colors = ["#ef4444" if v >= 0 else "#3b82f6" for v in macd_hist[-n:]]
            fig_tech.add_trace(go.Bar(
                x=idx, y=macd_hist[-n:], name="Histogram",
                marker_color=hist_colors, opacity=0.6
            ), row=3, col=1)

            fig_tech.update_layout(
                height=680,
                margin=dict(l=0, r=0, t=30, b=0),
                paper_bgcolor="white", plot_bgcolor="white",
                legend=dict(orientation="h", y=1.02, font=dict(size=11)),
                xaxis_rangeslider_visible=False,
                hovermode="x unified",
                font=dict(family="sans-serif"),
            )
            for row_i in [1, 2, 3]:
                fig_tech.update_yaxes(
                    gridcolor="#f3f4f6", tickfont=dict(size=10, color="#888"),
                    zeroline=False, row=row_i, col=1
                )
            st.plotly_chart(fig_tech, use_container_width=True)

            # RSI 해석 안내
            rsi_now = rsi.iloc[-1]
            if rsi_now >= 70:
                rsi_msg = f"🔴 RSI {rsi_now:.1f} — 과매수 구간. 단기 조정 가능성."
                rsi_bg = "#fff0f0"
            elif rsi_now <= 30:
                rsi_msg = f"🟢 RSI {rsi_now:.1f} — 과매도 구간. 반등 가능성."
                rsi_bg = "#f0fff4"
            else:
                rsi_msg = f"⚪ RSI {rsi_now:.1f} — 중립 구간."
                rsi_bg = "#f8f9fa"
            st.markdown(
                f"<div style='background:{rsi_bg};border-radius:6px;padding:10px 16px;"
                f"font-size:13px;color:#444;margin-bottom:16px;'>{rsi_msg}</div>",
                unsafe_allow_html=True
            )
        else:
            st.info("주가 차트를 불러올 수 없습니다.")

        st.markdown("---")

        # ── 재무 데이터 ──────────────────────────────────────────────
        st.markdown("### 재무 현황")
        with st.spinner(f"{company} 재무 데이터 불러오는 중..."):
            corp_code = get_corp_code(company)
            if corp_code:
                # 최신 단일 분기/반기/연간
                fin_list, latest_year, latest_label = get_financial_data(corp_code)
                # 연간 3개년 시계열
                annual_map = get_annual_series(corp_code)

                def parse_amt(v):
                    try:
                        return int(str(v).replace(",","").replace("-","").strip() or 0)
                    except:
                        return 0

                def get_val_from_list(lst, account):
                    cfs = [x for x in lst if x.get("fs_div") == "CFS"]
                    target = cfs if cfs else lst
                    for item in target:
                        if item.get("account_nm") == account:
                            return {
                                "y2": parse_amt(item.get("bfefrmtrm_amount","0")),
                                "y1": parse_amt(item.get("frmtrm_amount","0")),
                                "y0": parse_amt(item.get("thstrm_amount","0")),
                            }
                    return {"y2":0,"y1":0,"y0":0}

                if fin_list:
                    latest_cfs = [x for x in fin_list if x.get("fs_div") == "CFS"] or fin_list
                    rev_now  = get_val_from_list(fin_list, "매출액")["y0"]
                    op_now   = get_val_from_list(fin_list, "영업이익")["y0"]
                    net_now  = get_val_from_list(fin_list, "당기순이익(손실)")["y0"]
                    debt_now = get_val_from_list(fin_list, "부채총계")["y0"]
                    eq_now   = get_val_from_list(fin_list, "자본총계")["y0"]

                    def tri(v): return round(v/1_000_000_000_000, 2)

                    st.caption(f"📌 최신 보고서: {latest_label} (DART 공시 기준)")
                    m1,m2,m3,m4,m5 = st.columns(5)
                    m1.metric("매출액",   f"{tri(rev_now)}조")
                    m2.metric("영업이익", f"{tri(op_now)}조")
                    m3.metric("순이익",   f"{tri(net_now)}조")
                    m4.metric("부채비율", f"{round(debt_now/eq_now*100,1) if eq_now else 0}%")
                    m5.metric("영업이익률",f"{round(op_now/rev_now*100,1) if rev_now else 0}%")

                    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

                # 연간 3개년 차트
                if annual_map:
                    sorted_years = sorted(annual_map.keys())[-3:]
                    rev_t, op_t, net_t = [], [], []
                    for yr in sorted_years:
                        lst = annual_map[yr]
                        rev_t.append(tri(get_val_from_list(lst,"매출액")["y0"]))
                        op_t.append(tri(get_val_from_list(lst,"영업이익")["y0"]))
                        net_t.append(tri(get_val_from_list(lst,"당기순이익(손실)")["y0"]))

                    st.markdown(f"**연간 실적 추이 (조원) — {sorted_years[0]}~{sorted_years[-1]}**")
                    fig_fin = go.Figure()
                    for name, vals, color, border in [
                        ("매출액", rev_t, "#93c5fd","#60a5fa"),
                        ("영업이익", op_t, "#6ee7b7","#34d399"),
                        ("순이익", net_t, "#fcd34d","#fbbf24"),
                    ]:
                        fig_fin.add_trace(go.Bar(
                            name=name, x=sorted_years, y=vals,
                            marker_color=color, marker_line_color=border,
                            marker_line_width=1.2, width=0.22
                        ))
                    fig_fin.update_layout(
                        barmode="group", bargroupgap=0.35, height=280,
                        margin=dict(l=0,r=0,t=10,b=0),
                        paper_bgcolor="white", plot_bgcolor="white",
                        legend=dict(orientation="h", y=-0.25, font=dict(size=12)),
                        yaxis=dict(ticksuffix="조", gridcolor="#f3f4f6", zeroline=False,
                                   tickfont=dict(size=11, color="#888")),
                        xaxis=dict(gridcolor="#f3f4f6", tickfont=dict(size=12, color="#444")),
                    )
                    st.plotly_chart(fig_fin, use_container_width=True)
                else:
                    st.warning("연간 재무 데이터를 불러올 수 없습니다.")
            else:
                st.warning("DART에서 해당 기업을 찾을 수 없습니다.")

elif page == "뉴스":
    st.title("오늘의 시장 뉴스")
    st.markdown("""
    <style>
    details[data-testid="stExpander"] summary p,
    details summary p { font-weight: 700 !important; }
    </style>
    """, unsafe_allow_html=True)
    import re

    news_main_tab1, news_main_tab2 = st.tabs(["분야별 뉴스", "내 종목 뉴스"])

    with news_main_tab2:
        pf_names = [p["name"] for p in st.session_state.portfolio] if st.session_state.portfolio else []
        if not pf_names:
            st.info("포트폴리오 탭에서 종목을 추가하면 해당 종목의 최신 뉴스를 여기서 바로 확인할 수 있습니다.")
        else:
            st.caption(f"보유 종목 {len(pf_names)}개 관련 최신 뉴스를 모아드립니다.")
            pf_news_key = f"pf_news_{'_'.join(pf_names[:5])}"
            if st.button("내 종목 뉴스 불러오기", key="pf_news_btn") or pf_news_key not in st.session_state:
                st.session_state.pop(pf_news_key, None)
            if pf_news_key not in st.session_state:
                with st.spinner("보유 종목 뉴스 수집 중..."):
                    from datetime import date as _nd
                    today_str = _nd.today().strftime("%Y.%m.%d")
                    stocks_str = ", ".join(pf_names)
                    result = ask_perplexity(
                        f"오늘은 {today_str}이야. 다음 종목들과 관련된 오늘 최신 뉴스를 각 종목당 1~2개씩 찾아줘: {stocks_str}\n\n"
                        f"아래 형식 엄수. 구분자는 ===.\n\n"
                        f"종목: 종목명\n"
                        f"제목: 뉴스 제목\n"
                        f"출처: 신문사명\n"
                        f"날짜: {today_str}\n"
                        f"중요도: HIGH 또는 NORMAL\n"
                        f"요약: 한 줄 핵심 요약\n"
                        f"상세: 2~3문장 상세 내용\n"
                        f"===\n"
                        f"규칙: 대괄호 숫자 각주 절대 금지. 별표 마크다운 절대 금지."
                    )
                    result = re.sub(r'\[\d+\]', '', result)
                    result = re.sub(r'\*\*?(.*?)\*\*?', r'\1', result)
                    st.session_state[pf_news_key] = result

            if pf_news_key in st.session_state:
                items = [x.strip() for x in st.session_state[pf_news_key].split("===") if x.strip()]
                for item in items:
                    fields = {}
                    for line in item.split("\n"):
                        line = line.strip()
                        for k in ["종목","제목","출처","날짜","중요도","요약","상세"]:
                            if line.startswith(f"{k}:"):
                                fields[k] = line.replace(f"{k}:", "").strip()
                    if not fields.get("제목"):
                        continue
                    is_high = fields.get("중요도","").upper() == "HIGH"
                    meta = []
                    if fields.get("출처"): meta.append(fields["출처"])
                    if fields.get("날짜"): meta.append(fields["날짜"])
                    meta_str = " · ".join(meta)
                    prefix = "🔴 " if is_high else ""
                    stock_badge = f"[{fields.get('종목','')}] " if fields.get("종목") else ""
                    label = f"{prefix}{stock_badge}{fields.get('제목','')}  ({meta_str})" if meta_str else f"{prefix}{stock_badge}{fields.get('제목','')}"
                    with st.expander(label):
                        st.markdown(f"<div style='font-size:15px;font-weight:700;color:#1a1e2e;margin-bottom:10px;'>{prefix}{fields.get('제목','')}</div>", unsafe_allow_html=True)
                        if is_high:
                            st.markdown(f"<div style='background:#fff0f0;border-left:3px solid #ef4444;padding:8px 12px;border-radius:4px;font-size:13px;color:#b91c1c;margin-bottom:10px;'>⚠️ 주가 영향 주목 — {fields.get('요약','')}</div>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<div style='font-size:13px;color:#666;margin-bottom:10px;'>핵심: {fields.get('요약','')}</div>", unsafe_allow_html=True)
                        if fields.get("상세"):
                            st.markdown(fields["상세"])

    with news_main_tab1:
        NEWS_CATEGORIES = {
        "전체 시장": "오늘의 주요 경제·금융·산업",
        "반도체·IT": "반도체 및 IT 기술 산업",
        "바이오·제약": "바이오 및 제약 산업",
        "방산·우주": "방위산업 및 우주항공 산업",
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
            "분야 선택",
            list(NEWS_CATEGORIES.keys()),
            key="news_category",
            label_visibility="collapsed"
        )

        @st.cache_data(ttl=1800)
        def fetch_news_by_category(category, keyword):
            import re as _re
            from datetime import date as _d
            today_str = _d.today().strftime("%Y.%m.%d")
            result = ask_perplexity(
                f"오늘은 {today_str}이야. {keyword} 관련 오늘({today_str}) 보도된 뉴스만 10개를 최신 순으로 한국어로 작성해줘.\n"
                f"오늘 보도된 뉴스가 10개 미만이면 가장 최근 날짜 순으로 채워줘. 단 날짜 필드에 실제 보도 날짜를 정확히 적을 것.\n"
                f"해당 분야 주요 주식 주가에 큰 영향을 끼칠 수 있는 뉴스는 중요도를 HIGH로 표시해줘.\n"
                f"반드시 10개 전부 작성할 것. 대괄호 숫자 각주 절대 금지. 별표 마크다운 절대 금지.\n"
                f"각 뉴스는 아래 형식을 정확히 지키고, 뉴스 사이 구분은 반드시 ===로만 할 것.\n\n"
                f"제목: 뉴스 제목\n출처: 신문사명\n날짜: {today_str}\n"
                f"중요도: HIGH 또는 NORMAL\n요약: 한 줄 핵심 요약\n"
                f"상세: 3~4문장 상세 내용. 배경 원인 시장영향 포함.\n==="
            )
            result = _re.sub(r'\[\d+\]', '', result)
            result = _re.sub(r'\*\*?(.*?)\*\*?', r'\1', result)
            return result

        with st.spinner(f"{selected_category} 뉴스 불러오는 중..."):
            news_raw = fetch_news_by_category(selected_category, NEWS_CATEGORIES[selected_category])

        news_items = [x.strip() for x in news_raw.split("===") if x.strip()]
        count = 0
        for item in news_items:
            lines = item.split("\n")
            title = source = date_str = importance = summary = detail = ""
            detail_lines = []
            in_detail = False
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("제목:"):
                    title = line.replace("제목:", "").strip()
                    in_detail = False
                elif line.startswith("출처:"):
                    source = line.replace("출처:", "").strip()
                    in_detail = False
                elif line.startswith("날짜:"):
                    date_str = line.replace("날짜:", "").strip()
                    in_detail = False
                elif line.startswith("중요도:"):
                    importance = line.replace("중요도:", "").strip().upper()
                    in_detail = False
                elif line.startswith("요약:"):
                    summary = line.replace("요약:", "").strip()
                    in_detail = False
                elif line.startswith("상세:"):
                    detail_lines = [line.replace("상세:", "").strip()]
                    in_detail = True
                elif in_detail:
                    detail_lines.append(line)
            detail = " ".join(detail_lines).strip()

            if not title:
                continue

            is_high = importance == "HIGH"
            meta_parts = []
            if source:
                meta_parts.append(source)
            if date_str:
                meta_parts.append(date_str)
            meta_str = " · ".join(meta_parts)
            meta_display = f"  ({meta_str})" if meta_str else ""

            prefix = "🔴 " if is_high else ""
            expander_label = f"{prefix}{title}{meta_display}"

            with st.expander(expander_label):
                # 볼드 제목 재표시
                st.markdown(f"<div style='font-size:15px;font-weight:700;color:#1a1e2e;margin-bottom:10px;'>{prefix}{title}</div>", unsafe_allow_html=True)
                if is_high:
                    st.markdown(
                        f"<div style='background:#fff0f0;border-left:3px solid #ef4444;"
                        f"padding:8px 12px;border-radius:4px;font-size:13px;color:#b91c1c;"
                        f"margin-bottom:10px;'>⚠️ 주가 영향 주목 — {summary}</div>",
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f"<div style='font-size:13px;color:#666;margin-bottom:10px;'>"
                        f"핵심: {summary}</div>",
                        unsafe_allow_html=True
                    )
                if detail:
                    st.markdown(detail)
            count += 1
            if count >= 10:
                break

elif page == "국제 금융":
    st.title("국제 금융")

    @st.cache_data(ttl=1800)
    def get_intl_data():
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
        return result

    with st.spinner("국제 금융 동향 분석 중..."):
        intl_result = get_intl_data()
    st.markdown(intl_result)

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

    tab2, tab3, tab1, tab4 = st.tabs(["국내 주식 검색", "해외 주식 검색", "시총 상위 100", "외국인·기관 수급"])

    with tab1:
        st.caption("코스피 시가총액 상위 100개 종목 · KRX+yfinance 분산 조회 · 1분 캐시")
        # 스켈레톤 placeholder - 화면 즉시 표시
        placeholder = st.empty()
        placeholder.markdown("""
        <div style='background:white;border-radius:12px;padding:32px;text-align:center;
            box-shadow:0 2px 8px rgba(0,0,0,0.05);'>
            <div style='font-size:14px;color:#888;'>📡 주가 데이터 수집 중...</div>
            <div style='font-size:12px;color:#aaa;margin-top:8px;'>KRX → yfinance 순으로 빠른 소스에서 가져옵니다</div>
        </div>
        """, unsafe_allow_html=True)
        data_list = get_stock_data(KOSPI_100)
        placeholder.empty()
        if data_list:
            df = pd.DataFrame(data_list)
            df.index = range(1, len(df) + 1)
            row_h = 35
            st.dataframe(df, use_container_width=True, height=min(len(df) * row_h + 38, 3500))
            st.caption(f"업데이트: {pd.Timestamp.now().strftime('%H:%M:%S')} · 총 {len(df)}개 종목")
        else:
            st.warning("주가 데이터를 불러올 수 없습니다. 잠시 후 다시 시도해주세요.")

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
        stock_list = get_cached_stock_list()
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

    with tab4:
        import re as _re
        from datetime import date as _date
        st.caption("외국인·기관 순매수/순매도 동향을 AI가 분석합니다. 수급은 주가를 선행하는 경우가 많습니다.")

        sd_col1, sd_col2 = st.columns([2, 1])
        with sd_col1:
            sd_search = st.text_input("종목명 검색 (비워두면 시장 전체)", placeholder="예: 삼성전자 (빈칸=전체)", key="sd_search")
        with sd_col2:
            sd_period = st.selectbox("기간", ["오늘", "최근 5일", "최근 20일"], key="sd_period")

        if st.button("수급 분석", key="sd_run"):
            today_str = _date.today().strftime("%Y.%m.%d")
            target = sd_search.strip() if sd_search.strip() else "코스피 전체 시장"
            period_txt = {"오늘": "오늘", "최근 5일": "최근 5거래일", "최근 20일": "최근 20거래일"}[sd_period]
            cache_key = f"sd_{target}_{sd_period}"
            st.session_state.pop(cache_key, None)

            with st.spinner(f"{target} 수급 분석 중..."):
                prompt = (
                    f"오늘은 {today_str}이야. {target}의 {period_txt} 외국인·기관 수급 동향을 분석해줘.\n\n"
                    f"아래 형식으로 정확히 작성해줘. 구분자는 ===.\n\n"
                    f"항목: 외국인\n"
                    f"동향: 순매수 또는 순매도\n"
                    f"금액: 대략적인 금액 또는 규모\n"
                    f"분석: 2~3문장. 주요 매수/매도 종목, 섹터 포함.\n"
                    f"===\n"
                    f"항목: 기관\n"
                    f"동향: 순매수 또는 순매도\n"
                    f"금액: 대략적인 금액 또는 규모\n"
                    f"분석: 2~3문장. 주요 매수/매도 종목, 섹터 포함.\n"
                    f"===\n"
                    f"항목: 개인\n"
                    f"동향: 순매수 또는 순매도\n"
                    f"금액: 대략적인 금액 또는 규모\n"
                    f"분석: 1~2문장.\n"
                    f"===\n"
                    f"항목: 수급 종합 의견\n"
                    f"분석: 현재 수급 흐름이 주가에 미치는 영향과 단기 전망 2~3문장.\n"
                    f"===\n"
                    f"규칙: 대괄호 숫자 각주 절대 금지. 별표 마크다운 절대 금지. 거절 금지."
                )
                result = ask_perplexity(prompt)
                result = _re.sub(r'\[\d+\]', '', result)
                result = _re.sub(r'\*\*?(.*?)\*\*?', r'\1', result)
                st.session_state[cache_key] = result

            items = [x.strip() for x in st.session_state[cache_key].split("===") if x.strip()]
            color_map = {"외국인": "#3182f6", "기관": "#6366f1", "개인": "#f97316", "수급 종합 의견": "#22c55e"}

            for item in items:
                fields = {}
                for line in item.split("\n"):
                    line = line.strip()
                    for k in ["항목", "동향", "금액", "분석"]:
                        if line.startswith(f"{k}:"):
                            fields[k] = line.replace(f"{k}:", "").strip()
                name = fields.get("항목", "")
                if not name:
                    continue
                color  = color_map.get(name, "#888")
                동향    = fields.get("동향", "")
                금액    = fields.get("금액", "")
                분석    = fields.get("분석", "")
                동향색  = "#e03131" if "순매수" in 동향 else "#1971c2" if "순매도" in 동향 else "#888"
                meta   = f"<span style='color:{동향색};font-weight:700;'>{동향}</span>"
                if 금액:
                    meta += f"  |  {금액}"
                st.markdown(f"""
                <div style='background:white;border:1px solid #e8eaed;
                    border-left:4px solid {color};border-radius:8px;
                    padding:18px 22px;margin-bottom:12px;'>
                    <div style='font-size:15px;font-weight:700;color:#1a1e2e;margin-bottom:8px;'>
                        {name}  <span style='font-size:13px;font-weight:400;'>{meta}</span>
                    </div>
                    <div style='font-size:14px;color:#444;line-height:1.8;'>{분석}</div>
                </div>
                """, unsafe_allow_html=True)

elif page == "포트폴리오":
    st.title("포트폴리오 트래커")

    stock_list = get_cached_stock_list()

    stock_names = [s["name"] for s in stock_list]
    stock_map = {s["name"]: s["ticker"] for s in stock_list}

    # ── 목표가 알림 체크 (5분에 1번만) ──────────────────────
    import time as _time
    _last_alert_check = st.session_state.get("last_alert_check", 0)
    if _time.time() - _last_alert_check > 300:  # 5분 간격
        st.session_state.last_alert_check = _time.time()
        def check_price_alerts():
            user = st.session_state.user
            if not user:
                return
            email = user.get("email", "")
            if not email:
                return
            try:
                alerts = supabase.table("price_alerts").select("*")\
                    .eq("user_id", user["id"]).eq("is_active", True).execute().data or []
                if not alerts:
                    return
                import concurrent.futures as _cfa
                def _check_one(al):
                    try:
                        ticker = al.get("ticker", "")
                        if not ticker:
                            return None
                        h = yf.Ticker(ticker).history(period="1d")
                        if h.empty:
                            return None
                        cur = float(h["Close"].iloc[-1])
                        target = float(al["target_price"])
                        direction = al.get("direction", "")
                        hit = (direction == "이상" and cur >= target) or \
                              (direction == "이하" and cur <= target)
                        return (al, cur) if hit else None
                    except:
                        return None
                with _cfa.ThreadPoolExecutor(max_workers=5) as ex:
                    results = list(ex.map(_check_one, alerts))
                for r in results:
                    if r:
                        al, cur = r
                        sent = send_alert_email(email, al["name"],
                                                float(al["target_price"]),
                                                al["direction"], cur)
                        if sent:
                            supabase.table("price_alerts")\
                                .update({"is_active": False})\
                                .eq("id", al["id"]).execute()
                            st.toast(f"📧 {al['name']} 목표가 알림 이메일 발송됨!", icon="✅")
            except:
                pass
        check_price_alerts()

    pf_main_tab1, pf_main_tab2, pf_main_tab3 = st.tabs(["포트폴리오", "관심종목", "시뮬레이터"])

    # ══════════════════════════════════════════════════════════
    # 탭1: 기존 포트폴리오
    # ══════════════════════════════════════════════════════════
    with pf_main_tab1:

        # 섹터 매핑 (주요 종목)
        SECTOR_MAP = {
            "삼성전자": "반도체·IT", "SK하이닉스": "반도체·IT", "LG이노텍": "반도체·IT",
            "삼성전기": "반도체·IT", "DB하이텍": "반도체·IT",
            "현대차": "자동차", "기아": "자동차", "현대모비스": "자동차",
            "현대위아": "자동차", "만도": "자동차",
            "LG에너지솔루션": "2차전지", "삼성SDI": "2차전지", "에코프로비엠": "2차전지",
            "포스코퓨처엠": "2차전지", "엘앤에프": "2차전지",
            "삼성바이오로직스": "바이오·제약", "셀트리온": "바이오·제약", "한미약품": "바이오·제약",
            "유한양행": "바이오·제약", "종근당": "바이오·제약",
            "KB금융": "금융", "신한지주": "금융", "하나금융지주": "금융",
            "우리금융지주": "금융", "삼성생명": "금융", "삼성화재": "금융",
            "POSCO홀딩스": "소재·철강", "고려아연": "소재·철강", "OCI": "소재·철강",
            "한화에어로스페이스": "방산·우주", "한국항공우주": "방산·우주", "현대중공업": "방산·우주",
            "카카오": "플랫폼·게임", "네이버": "플랫폼·게임", "크래프톤": "플랫폼·게임",
            "엔씨소프트": "플랫폼·게임", "하이브": "플랫폼·게임",
            "대한항공": "항공·여행", "제주항공": "항공·여행", "진에어": "항공·여행",
            "이마트": "유통·소비", "신세계": "유통·소비", "롯데쇼핑": "유통·소비",
            "한국전력": "에너지·유틸리티", "SK이노베이션": "에너지·유틸리티", "S-Oil": "에너지·유틸리티",
            "HMM": "물류·해운", "현대글로비스": "물류·해운",
        }

        # 입력 초기화용 키 관리
        if "pf_input_ver" not in st.session_state:
            st.session_state.pf_input_ver = 0
        ver = st.session_state.pf_input_ver

        col_a, col_b = st.columns(2)
        with col_a:
            search = st.text_input("종목명 검색", placeholder="예: 삼성전자", key=f"pf_search_{ver}")
        with col_b:
            qty_input = st.number_input("보유 수량", min_value=1, value=1, key=f"pf_qty_{ver}")

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
                selected_display = st.selectbox("종목 선택", matched_with_code, key=f"pf_select_{ver}")
                selected_stock = selected_display.split("  (")[0]
            else:
                st.warning("검색 결과가 없습니다.")

        buy_price = st.number_input(
            "매수 평균가 (원)",
            min_value=0,
            value=None,
            placeholder="예: 73000",
            step=100,
            format="%d",
            key=f"pf_price_{ver}"
        )

        if st.button("종목 추가", key="add_btn"):
            if selected_stock and buy_price and buy_price > 0:
                ticker_auto = stock_map.get(selected_stock, "")
                new_item = {
                    "name": selected_stock,
                    "ticker": ticker_auto,
                    "qty": qty_input,
                    "buy_price": buy_price
                }
                # DB 저장
                user_id = st.session_state.user["id"]
                try:
                    res = supabase.table("portfolio").insert({
                        "user_id": user_id,
                        "name": new_item["name"],
                        "ticker": new_item["ticker"],
                        "qty": new_item["qty"],
                        "buy_price": new_item["buy_price"],
                    }).execute()
                    new_item["id"] = res.data[0]["id"]
                except:
                    new_item["id"] = None
                st.session_state.portfolio.append(new_item)
                st.session_state.pf_input_ver += 1
                st.rerun()
            else:
                st.warning("종목과 매수 평균가를 입력해주세요.")

        if st.session_state.portfolio:
            import plotly.graph_objects as go
            import plotly.express as px
            import numpy as np

            st.markdown("---")

            # ── 종목별 현재가 / 수익 계산 ──────────────────────────────
            total_invested = 0
            total_value = 0
            rows = []
            enriched = []   # {name, ticker, qty, buy_price, current, sector}

            # 스켈레톤 UI - 화면 즉시 표시
            pf_skel = st.empty()
            pf_skel.markdown("""
            <div style='background:white;border-radius:12px;padding:24px;text-align:center;
                box-shadow:0 2px 8px rgba(0,0,0,0.05);margin-bottom:16px;'>
                <div style='font-size:14px;color:#888;'>📡 현재가 조회 중...</div>
                <div style='font-size:12px;color:#aaa;margin-top:6px;'>KRX → yfinance 병렬 수집</div>
            </div>
            """, unsafe_allow_html=True)

            # 포트폴리오 현재가 일괄 조회 (KRX + yfinance 분산)
            import concurrent.futures as _cf
            pf_items = st.session_state.portfolio

            @st.cache_data(ttl=300)
            def _get_pf_prices(tickers_tuple):
                tickers_list = list(tickers_tuple)
                try:
                    raw = yf.download(
                        tickers_list, period="5d", interval="1d",
                        group_by="ticker", auto_adjust=True,
                        progress=False, threads=True, timeout=15
                    )
                    prices = {}
                    for sym in tickers_list:
                        try:
                            if len(tickers_list) == 1:
                                h = raw
                            else:
                                h = raw[sym] if sym in raw.columns.get_level_values(0) else pd.DataFrame()
                            if h is not None and not h.empty:
                                h = h.dropna(subset=["Close"])
                                if not h.empty:
                                    prices[sym] = float(h["Close"].iloc[-1])
                        except:
                            pass
                    return prices
                except:
                    return {}

            pf_syms = tuple(item["ticker"] for item in pf_items)
            bulk_prices = _get_pf_prices(pf_syms)

            def _fetch_pf_price(item):
                # bulk에서 찾으면 바로 반환
                if item["ticker"] in bulk_prices:
                    return bulk_prices[item["ticker"]]
                # 없으면 개별 조회
                try:
                    h = yf.Ticker(item["ticker"]).history(period="5d")
                    if h.empty:
                        code = item["ticker"].replace(".KS","").replace(".KQ","")
                        for sfx in [".KS", ".KQ"]:
                            h2 = yf.Ticker(code + sfx).history(period="5d")
                            if not h2.empty:
                                h = h2
                                item["ticker"] = code + sfx
                                break
                    return float(h["Close"].iloc[-1]) if not h.empty else item["buy_price"]
                except:
                    return item["buy_price"]

            with _cf.ThreadPoolExecutor(max_workers=min(len(pf_items), 10)) as ex:
                prices = list(ex.map(_fetch_pf_price, pf_items))

            pf_skel.empty()  # 스켈레톤 제거

            for item, current in zip(pf_items, prices):
                invested = item["buy_price"] * item["qty"]
                value    = current * item["qty"]
                profit   = value - invested
                profit_pct = (profit / invested * 100) if invested > 0 else 0
                total_invested += invested
                total_value    += value
                sector = SECTOR_MAP.get(item["name"], "기타")
                enriched.append({**item, "current": current, "value": value,
                                  "profit": profit, "profit_pct": profit_pct, "sector": sector})
                rows.append({
                    "종목": item["name"],
                    "섹터": sector,
                    "보유수량": item["qty"],
                    "매수가": f"{item['buy_price']:,.0f}원",
                    "현재가": f"{current:,.0f}원",
                    "투자금액": f"{invested:,.0f}원",
                    "평가금액": f"{value:,.0f}원",
                    "수익금액": f"{profit:+,.0f}원",
                    "수익률": f"{profit_pct:+.2f}%",
                })

            total_profit = total_value - total_invested
            total_pct    = (total_profit / total_invested * 100) if total_invested > 0 else 0

            # ── 상단 요약 카드 ──────────────────────────────────────────
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("총 투자금액", f"{total_invested:,.0f}원")
            c2.metric("총 평가금액", f"{total_value:,.0f}원")
            pnl_delta = f"{total_pct:+.2f}%"
            c3.metric("총 수익금액", f"{total_profit:+,.0f}원", pnl_delta)
            c4.metric("보유 종목 수", f"{len(enriched)}개")

            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

            # ── 종목 테이블 + 삭제 버튼 ────────────────────────────────
            st.markdown("""
            <style>
            .row-header {color: #888; font-size: 12px; font-weight:600; padding: 4px 0;}
            .row-item   {font-size: 14px; padding: 6px 0;}
            </style>
            """, unsafe_allow_html=True)

            header = st.columns([1.8, 1, 1, 1.2, 1.2, 1.4, 1.4, 1.4, 1.2, 0.4])
            for h, col in zip(["종목","섹터","보유수량","매수가","현재가","투자금액","평가금액","수익금액","수익률",""], header):
                col.markdown(f"<span class='row-header'>{h}</span>", unsafe_allow_html=True)

            for i, (row, en) in enumerate(zip(rows, enriched)):
                profit_color = "#e03131" if en["profit"] < 0 else "#2f9e44"
                cols = st.columns([1.8, 1, 1, 1.2, 1.2, 1.4, 1.4, 1.4, 1.2, 0.4])
                cols[0].markdown(f"<span class='row-item'>{row['종목']}</span>", unsafe_allow_html=True)
                cols[1].markdown(f"<span class='row-item' style='color:#6366f1;font-size:12px'>{row['섹터']}</span>", unsafe_allow_html=True)
                cols[2].markdown(f"<span class='row-item'>{row['보유수량']}</span>", unsafe_allow_html=True)
                cols[3].markdown(f"<span class='row-item'>{row['매수가']}</span>", unsafe_allow_html=True)
                cols[4].markdown(f"<span class='row-item'>{row['현재가']}</span>", unsafe_allow_html=True)
                cols[5].markdown(f"<span class='row-item'>{row['투자금액']}</span>", unsafe_allow_html=True)
                cols[6].markdown(f"<span class='row-item'>{row['평가금액']}</span>", unsafe_allow_html=True)
                cols[7].markdown(f"<span class='row-item' style='color:{profit_color}'>{row['수익금액']}</span>", unsafe_allow_html=True)
                cols[8].markdown(f"<span class='row-item' style='color:{profit_color};font-weight:600'>{row['수익률']}</span>", unsafe_allow_html=True)
                if cols[9].button("✕", key=f"del_{i}"):
                    item_id = st.session_state.portfolio[i].get("id")
                    if item_id:
                        db_delete_portfolio_item(item_id)
                    st.session_state.portfolio.pop(i)
                    st.rerun()

            st.markdown("---")

            # ── 섹터별 비중 파이차트 + 종목별 비중 도넛 ──────────────
            st.markdown("### 📊 포트폴리오 구성")
            pie_c1, pie_c2 = st.columns(2)

            # 섹터별
            sector_vals = {}
            for en in enriched:
                sector_vals[en["sector"]] = sector_vals.get(en["sector"], 0) + en["value"]
            s_labels = list(sector_vals.keys())
            s_vals   = list(sector_vals.values())
            pastel_colors = [
                "#a5b4fc","#86efac","#fde68a","#fca5a5","#67e8f9",
                "#f9a8d4","#c4b5fd","#6ee7b7","#fcd34d","#93c5fd","#fb923c"
            ]
            fig_sector = go.Figure(go.Pie(
                labels=s_labels, values=s_vals,
                hole=0.45,
                marker=dict(colors=pastel_colors[:len(s_labels)], line=dict(color="white", width=2)),
                textinfo="label+percent",
                textfont=dict(size=12),
                hovertemplate="%{label}<br>%{value:,.0f}원 (%{percent})<extra></extra>"
            ))
            fig_sector.update_layout(
                title=dict(text="섹터별 비중", font=dict(size=14, color="#1a1e2e"), x=0.5),
                height=320, margin=dict(l=10,r=10,t=40,b=10),
                paper_bgcolor="white", showlegend=True,
                legend=dict(font=dict(size=11), orientation="v")
            )
            pie_c1.plotly_chart(fig_sector, use_container_width=True)

            # 종목별
            stock_labels = [en["name"] for en in enriched]
            stock_vals   = [en["value"] for en in enriched]
            fig_stock = go.Figure(go.Pie(
                labels=stock_labels, values=stock_vals,
                hole=0.45,
                marker=dict(colors=pastel_colors[:len(stock_labels)], line=dict(color="white", width=2)),
                textinfo="label+percent",
                textfont=dict(size=12),
                hovertemplate="%{label}<br>%{value:,.0f}원 (%{percent})<extra></extra>"
            ))
            fig_stock.update_layout(
                title=dict(text="종목별 비중", font=dict(size=14, color="#1a1e2e"), x=0.5),
                height=320, margin=dict(l=10,r=10,t=40,b=10),
                paper_bgcolor="white", showlegend=True,
                legend=dict(font=dict(size=11), orientation="v")
            )
            pie_c2.plotly_chart(fig_stock, use_container_width=True)

            st.markdown("---")

            # ── 수익률 추이 + 코스피 벤치마크 ─────────────────────────
            st.markdown("### 📈 수익률 추이 (3개월) vs KOSPI 벤치마크")
            with st.spinner("3개월 수익률 데이터 불러오는 중..."):
                try:
                    # 포트폴리오 일별 가치 계산
                    all_hist = {}
                    for en in enriched:
                        try:
                            h = yf.Ticker(en["ticker"]).history(period="3mo", interval="1d")["Close"]
                            h.index = pd.to_datetime(h.index).tz_localize(None)
                            all_hist[en["name"]] = h
                        except:
                            pass

                    if all_hist:
                        idx_union = sorted(set().union(*[h.index for h in all_hist.values()]))
                        portfolio_series = pd.Series(0.0, index=idx_union)
                        total_invested_hist = 0
                        for en in enriched:
                            if en["name"] in all_hist:
                                h = all_hist[en["name"]].reindex(idx_union, method="ffill")
                                portfolio_series += h * en["qty"]
                                total_invested_hist += en["buy_price"] * en["qty"]

                        port_return = ((portfolio_series / total_invested_hist) - 1) * 100

                        # KOSPI
                        kospi_h = yf.Ticker("^KS11").history(period="3mo", interval="1d")["Close"]
                        kospi_h.index = pd.to_datetime(kospi_h.index).tz_localize(None)
                        kospi_h = kospi_h.reindex(idx_union, method="ffill")
                        kospi_return = ((kospi_h / kospi_h.iloc[0]) - 1) * 100

                        fig_ret = go.Figure()
                        fig_ret.add_trace(go.Scatter(
                            x=port_return.index, y=port_return.values,
                            name="내 포트폴리오",
                            line=dict(color="#6366f1", width=2.5),
                            hovertemplate="%{x|%Y/%m/%d}<br>%{y:+.2f}%<extra>포트폴리오</extra>"
                        ))
                        fig_ret.add_trace(go.Scatter(
                            x=kospi_return.index, y=kospi_return.values,
                            name="KOSPI",
                            line=dict(color="#f97316", width=2, dash="dot"),
                            hovertemplate="%{x|%Y/%m/%d}<br>%{y:+.2f}%<extra>KOSPI</extra>"
                        ))
                        fig_ret.add_hline(y=0, line_dash="solid", line_color="#e5e7eb", line_width=1)
                        fig_ret.update_layout(
                            height=360,
                            margin=dict(l=0, r=0, t=10, b=0),
                            paper_bgcolor="white", plot_bgcolor="white",
                            legend=dict(orientation="h", y=-0.15, font=dict(size=12)),
                            yaxis=dict(ticksuffix="%", gridcolor="#f3f4f6", zeroline=False, tickfont=dict(size=11)),
                            xaxis=dict(gridcolor="#f3f4f6", tickfont=dict(size=11)),
                            hovermode="x unified",
                        )
                        st.plotly_chart(fig_ret, use_container_width=True)

                        # 초과 성과 요약
                        port_final  = port_return.iloc[-1] if not port_return.empty else 0
                        kospi_final = kospi_return.iloc[-1] if not kospi_return.empty else 0
                        excess      = port_final - kospi_final
                        sc1, sc2, sc3 = st.columns(3)
                        sc1.metric("포트폴리오 수익률 (3개월)", f"{port_final:+.2f}%")
                        sc2.metric("KOSPI 수익률 (3개월)",     f"{kospi_final:+.2f}%")
                        sc3.metric("초과 성과 (α)",            f"{excess:+.2f}%",
                                   delta_color="normal" if excess >= 0 else "inverse")
                    else:
                        st.warning("수익률 추이 데이터를 불러올 수 없습니다.")
                except Exception as e:
                    st.warning(f"수익률 추이 계산 중 오류: {e}")

            st.markdown("---")

            # ── MDD (최대 낙폭) 분석 ───────────────────────────────────
            st.markdown("### 📉 변동성 및 MDD 분석")
            with st.spinner("MDD 분석 중..."):
                try:
                    if all_hist and not portfolio_series.empty:
                        port_arr = portfolio_series.values.astype(float)
                        roll_max = pd.Series(port_arr).cummax()
                        drawdown = (pd.Series(port_arr) - roll_max) / roll_max * 100
                        mdd      = drawdown.min()

                        # 변동성 (일간 수익률 표준편차 × √252 연환산)
                        daily_ret   = port_return.pct_change().dropna()
                        annual_vol  = daily_ret.std() * (252 ** 0.5) * 100 if not daily_ret.empty else 0
                        sharpe_like = (port_final / annual_vol) if annual_vol > 0 else 0  # 무위험 0% 가정 간이 샤프

                        fig_dd = go.Figure()
                        fig_dd.add_trace(go.Scatter(
                            x=portfolio_series.index,
                            y=drawdown.values,
                            fill="tozeroy",
                            name="낙폭 (Drawdown)",
                            line=dict(color="#f87171", width=1.5),
                            fillcolor="rgba(248,113,113,0.18)",
                            hovertemplate="%{x|%Y/%m/%d}<br>%{y:.2f}%<extra>낙폭</extra>"
                        ))
                        fig_dd.add_hline(y=mdd, line_dash="dash", line_color="#ef4444",
                                         annotation_text=f"MDD {mdd:.2f}%",
                                         annotation_position="top right",
                                         annotation_font=dict(color="#ef4444", size=12))
                        fig_dd.update_layout(
                            height=260,
                            margin=dict(l=0, r=0, t=16, b=0),
                            paper_bgcolor="white", plot_bgcolor="white",
                            legend=dict(orientation="h", y=-0.2),
                            yaxis=dict(ticksuffix="%", gridcolor="#f3f4f6", zeroline=True,
                                       zerolinecolor="#e5e7eb", tickfont=dict(size=11)),
                            xaxis=dict(gridcolor="#f3f4f6", tickfont=dict(size=11)),
                        )
                        st.plotly_chart(fig_dd, use_container_width=True)

                        m1, m2, m3 = st.columns(3)
                        m1.metric("최대 낙폭 (MDD)",     f"{mdd:.2f}%")
                        m2.metric("연환산 변동성",        f"{annual_vol:.2f}%")
                        m3.metric("간이 샤프지수",        f"{sharpe_like:.2f}")
                    else:
                        st.info("MDD 분석을 위한 데이터가 부족합니다.")
                except Exception as e:
                    st.warning(f"MDD 분석 중 오류: {e}")

            # ── AI 포트폴리오 리스크 진단 + 리밸런싱 제안 ──────────────
            st.markdown("### 🤖 AI 포트폴리오 진단 리포트")
            if st.button("AI 리포트 생성", key="ai_report_btn"):
                portfolio_summary = "\n".join([
                    f"- {en['name']}: 매수가 {en['buy_price']:,.0f}원 × {en['qty']}주 "
                    f"/ 현재가 {en['current']:,.0f}원 / 섹터 {en['sector']} "
                    f"/ 수익률 {en['profit_pct']:+.2f}%"
                    for en in enriched
                ])
                total_str = (
                    f"총 투자금액: {total_invested:,.0f}원 / "
                    f"총 평가금액: {total_value:,.0f}원 / "
                    f"총 수익률: {total_pct:+.2f}%"
                )
                report_prompt = (
                    f"아래는 내 주식 포트폴리오야. 전문 자산관리사처럼 한국어로 분석해줘.\n\n"
                    f"[포트폴리오]\n{portfolio_summary}\n\n"
                    f"[요약]\n{total_str}\n\n"
                    f"반드시 아래 형식을 정확히 지켜서 작성해줘:\n\n"
                    f"한줄해결책: [지금 당장 해야 할 가장 핵심적인 한 줄 액션. 예: 'OO 비중 줄이고 XX 섹터 분산 필요']\n\n"
                    f"현황요약: [포트폴리오 전반 현황을 2~3문장으로 요약]\n\n"
                    f"1. 전체 리스크 진단\n[섹터 쏠림, 종목 집중도, 수익률 편차 분석 2~3문장]\n\n"
                    f"2. 손실 종목 원인 분석 및 대응 전략\n[손실 종목별 원인과 대응 2~3문장]\n\n"
                    f"3. 리밸런싱 제안\n[비중 조정, 추가 매수/매도 추천 2~3문장]\n\n"
                    f"4. 포트폴리오 전반적 투자의견\n[긍정/중립/부정 판단과 근거 2~3문장]\n\n"
                    f"5. 주의해야 할 리스크 요인\n[주요 리스크 2~3문장]\n\n"
                    f"규칙: 대괄호 숫자 각주 절대 금지. 별표 마크다운 절대 금지."
                )
                with st.spinner("AI가 포트폴리오를 분석하는 중..."):
                    report = ask_perplexity(report_prompt)
                    import re as _re
                    report = _re.sub(r'\[\d+\]', '', report)
                    report = _re.sub(r'\*\*?(.*?)\*\*?', r'\1', report)

                # 파싱
                oneliner = ""
                summary_text = ""
                sections = {}  # {제목: 내용}
                current_key = None
                section_order = []

                for line in report.split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("한줄해결책:"):
                        oneliner = line.replace("한줄해결책:", "").strip()
                    elif line.startswith("현황요약:"):
                        summary_text = line.replace("현황요약:", "").strip()
                        current_key = None
                    elif _re.match(r'^[1-5]\.\s', line):
                        current_key = line
                        sections[current_key] = []
                        section_order.append(current_key)
                    elif current_key:
                        sections[current_key].append(line)
                    elif summary_text and not oneliner:
                        summary_text += " " + line

                # 렌더링
                html = "<div style='background:white;border:1px solid #e8eaed;border-left:4px solid #6366f1;border-radius:8px;padding:28px 32px;margin-top:8px;'>"
                html += "<div style='font-size:13px;color:#6366f1;font-weight:700;margin-bottom:16px;letter-spacing:0.3px;'>AI 포트폴리오 진단 리포트</div>"

                # 한줄 해결책
                if oneliner:
                    html += (
                        f"<div style='background:#f0f4ff;border-radius:8px;padding:16px 20px;margin-bottom:20px;'>"
                        f"<div style='font-size:11px;color:#6366f1;font-weight:700;margin-bottom:6px;letter-spacing:0.5px;'>💡 지금 당장 해야 할 것</div>"
                        f"<div style='font-size:17px;font-weight:700;color:#1a1e2e;line-height:1.6;'>{oneliner}</div>"
                        f"</div>"
                    )

                # 현황 요약
                if summary_text:
                    html += f"<div style='font-size:14px;color:#555;line-height:1.8;margin-bottom:24px;'>{summary_text}</div>"

                # 섹션별
                for key in section_order:
                    content = " ".join(sections[key]).strip()
                    # 섹션 번호+제목 분리
                    m = _re.match(r'^([1-5])\.\s+(.+)', key)
                    if m:
                        num = m.group(1)
                        title = m.group(2)
                    else:
                        num, title = "", key
                    html += (
                        f"<div style='margin-bottom:20px;'>"
                        f"<div style='font-size:16px;font-weight:700;color:#1a1e2e;margin-bottom:8px;'>"
                        f"{num}. {title}</div>"
                        f"<div style='font-size:14px;color:#444;line-height:1.85;'>{content}</div>"
                        f"</div>"
                    )

                html += "</div>"
                st.markdown(html, unsafe_allow_html=True)

        st.markdown("---")
        if st.button("포트폴리오 초기화", key="reset_btn"):
            db_clear_portfolio(st.session_state.user["id"])
            st.session_state.portfolio = []
            st.rerun()

    # ══════════════════════════════════════════════════════════
    # 탭2: 관심종목
    # ══════════════════════════════════════════════════════════
    with pf_main_tab2:
        st.markdown("#### 관심종목 (위시리스트)")
        st.caption("포트폴리오에 담기 전 모니터링하고 싶은 종목을 추가하세요.")

        if "watchlist" not in st.session_state:
            st.session_state.watchlist = []
        if "wl_input_ver" not in st.session_state:
            st.session_state.wl_input_ver = 0

        wl_ver = st.session_state.wl_input_ver
        wl_col1, wl_col2 = st.columns([3, 1])
        with wl_col1:
            wl_search = st.text_input("종목명 검색", placeholder="예: 카카오", key=f"wl_search_{wl_ver}")
        wl_selected = None
        if wl_search:
            wl_matched = [n for n in stock_names if wl_search.lower() in n.lower()]
            if wl_matched:
                wl_display = st.selectbox("종목 선택", [
                    f"{n}  ({stock_map.get(n,'').replace('.KS','')})" for n in wl_matched
                ], key=f"wl_select_{wl_ver}")
                wl_selected = wl_display.split("  (")[0]
            else:
                st.warning("검색 결과가 없습니다.")

        if st.button("관심종목 추가", key="wl_add_btn"):
            if wl_selected:
                already = [w["name"] for w in st.session_state.watchlist]
                if wl_selected in already:
                    st.warning("이미 추가된 종목입니다.")
                else:
                    st.session_state.watchlist.append({
                        "name": wl_selected,
                        "ticker": stock_map.get(wl_selected, "")
                    })
                    st.session_state.wl_input_ver += 1
                    st.rerun()
            else:
                st.warning("종목을 선택해주세요.")

        if st.session_state.watchlist:
            st.markdown("---")
            wl_header = st.columns([2, 1.5, 1.5, 1.5, 1.5, 0.5])
            for h, col in zip(["종목", "현재가", "전일 대비", "등락률", "52주 고점 대비", ""], wl_header):
                col.markdown(f"<span style='font-size:12px;color:#888;font-weight:600;'>{h}</span>", unsafe_allow_html=True)

            for i, item in enumerate(st.session_state.watchlist):
                try:
                    stk = yf.Ticker(item["ticker"])
                    h5 = stk.history(period="2d")
                    h52 = stk.history(period="52wk")
                    if not h5.empty:
                        cur = h5["Close"].iloc[-1]
                        prev = h5["Close"].iloc[-2] if len(h5) >= 2 else cur
                        chg = cur - prev
                        chg_pct = chg / prev * 100
                        high52 = h52["Close"].max() if not h52.empty else cur
                        from_high = (cur - high52) / high52 * 100
                        arrow = "▲" if chg >= 0 else "▼"
                        color = "#e03131" if chg >= 0 else "#1971c2"
                        cur_str   = f"{cur:,.0f}원"
                        chg_str   = f"{arrow} {abs(chg):,.0f}원"
                        pct_str   = f"{chg_pct:+.2f}%"
                        high_str  = f"{from_high:.1f}%"
                    else:
                        cur_str = chg_str = pct_str = high_str = "-"
                        color = "#888"
                except:
                    cur_str = chg_str = pct_str = high_str = "-"
                    color = "#888"

                wl_row = st.columns([2, 1.5, 1.5, 1.5, 1.5, 0.5])
                wl_row[0].markdown(f"<span style='font-size:14px;font-weight:600;'>{item['name']}</span>", unsafe_allow_html=True)
                wl_row[1].markdown(f"<span style='font-size:14px;font-weight:700;'>{cur_str}</span>", unsafe_allow_html=True)
                wl_row[2].markdown(f"<span style='font-size:13px;color:{color};'>{chg_str}</span>", unsafe_allow_html=True)
                wl_row[3].markdown(f"<span style='font-size:13px;color:{color};font-weight:600;'>{pct_str}</span>", unsafe_allow_html=True)
                wl_row[4].markdown(f"<span style='font-size:13px;color:#888;'>{high_str}</span>", unsafe_allow_html=True)
                if wl_row[5].button("✕", key=f"wl_del_{i}"):
                    st.session_state.watchlist.pop(i)
                    st.rerun()

            st.markdown("---")
            _, wl_add_col = st.columns([4, 1])
            if wl_add_col.button("포트폴리오에 일괄 추가", key="wl_to_pf"):
                st.info("각 종목을 포트폴리오 탭에서 매수가와 함께 직접 추가해주세요.")
        else:
            st.info("관심종목이 없습니다. 종목을 검색해서 추가해보세요.")

    # ══════════════════════════════════════════════════════════
    # 탭3: 시뮬레이터
    # ══════════════════════════════════════════════════════════
    with pf_main_tab3:
        sim_tab1, sim_tab2 = st.tabs(["매수/매도 시뮬레이션", "손익분기점 계산기"])

        # ── 매수/매도 시뮬레이션 ───────────────────────────────
        with sim_tab1:
            st.markdown("#### 매수/매도 시뮬레이션")
            st.caption("종목을 매수하거나 매도하면 포트폴리오 비중이 어떻게 바뀌는지 미리 확인하세요.")

            sim_col1, sim_col2, sim_col3 = st.columns(3)
            with sim_col1:
                sim_action = st.radio("매수/매도", ["매수", "매도"], horizontal=True, key="sim_action")
            with sim_col2:
                sim_search = st.text_input("종목명", placeholder="예: 삼성전자", key="sim_search")
            with sim_col3:
                sim_qty = st.number_input("수량 (주)", min_value=1, value=10, key="sim_qty")

            sim_selected = None
            if sim_search:
                sim_matched = [n for n in stock_names if sim_search.lower() in n.lower()]
                if sim_matched:
                    sim_disp = st.selectbox("종목 선택", [
                        f"{n}  ({stock_map.get(n,'').replace('.KS','')})" for n in sim_matched
                    ], key="sim_select")
                    sim_selected = sim_disp.split("  (")[0]

            if st.button("시뮬레이션 실행", key="sim_run"):
                if not sim_selected:
                    st.warning("종목을 선택해주세요.")
                elif not st.session_state.portfolio:
                    st.warning("포트폴리오 탭에서 종목을 먼저 추가해주세요.")
                else:
                    with st.spinner("현재가 조회 중..."):
                        try:
                            ticker = stock_map.get(sim_selected, "")
                            stk = yf.Ticker(ticker)
                            h = stk.history(period="2d")
                            if h.empty:
                                for sfx in [".KS", ".KQ"]:
                                    code = ticker.replace(".KS","").replace(".KQ","")
                                    h = yf.Ticker(code + sfx).history(period="2d")
                                    if not h.empty:
                                        break
                            sim_price = h["Close"].iloc[-1] if not h.empty else 0
                        except:
                            sim_price = 0

                    if sim_price == 0:
                        st.error("현재가를 불러올 수 없습니다.")
                    else:
                        # 현재 포트폴리오 총 평가금액
                        cur_total = 0
                        cur_items = []
                        for p in st.session_state.portfolio:
                            try:
                                ph = yf.Ticker(p["ticker"]).history(period="2d")
                                pc = ph["Close"].iloc[-1] if not ph.empty else p["buy_price"]
                            except:
                                pc = p["buy_price"]
                            val = pc * p["qty"]
                            cur_total += val
                            cur_items.append({"name": p["name"], "value": val})

                        # 시뮬레이션 후 포트폴리오
                        sim_value = sim_price * sim_qty
                        if sim_action == "매수":
                            new_total = cur_total + sim_value
                            sim_items = cur_items.copy()
                            existing = next((x for x in sim_items if x["name"] == sim_selected), None)
                            if existing:
                                existing["value"] += sim_value
                            else:
                                sim_items.append({"name": sim_selected, "value": sim_value})
                        else:  # 매도
                            existing = next((x for x in cur_items if x["name"] == sim_selected), None)
                            if not existing:
                                st.error(f"포트폴리오에 {sim_selected} 종목이 없습니다.")
                                st.stop()
                            sell_val = min(sim_value, existing["value"])
                            new_total = cur_total - sell_val
                            sim_items = [{"name": x["name"], "value": x["value"] - (sell_val if x["name"] == sim_selected else 0)} for x in cur_items]
                            sim_items = [x for x in sim_items if x["value"] > 0]

                        st.markdown("---")
                        st.markdown(f"**{sim_selected} {sim_qty}주 {sim_action} 시뮬레이션 결과**")
                        st.markdown(f"거래 금액: **{sim_value:,.0f}원** (주당 {sim_price:,.0f}원)")

                        bc1, bc2, bc3 = st.columns(3)
                        bc1.metric("현재 총 평가금액", f"{cur_total:,.0f}원")
                        bc2.metric(f"{sim_action} 후 총액", f"{new_total:,.0f}원",
                                   f"{new_total - cur_total:+,.0f}원")
                        bc3.metric("거래 비중", f"{sim_value/new_total*100:.1f}%" if new_total > 0 else "-")

                        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

                        import plotly.graph_objects as go
                        bc_left, bc_right = st.columns(2)
                        with bc_left:
                            st.markdown("**현재 비중**")
                            fig_cur = go.Figure(go.Pie(
                                labels=[x["name"] for x in cur_items],
                                values=[x["value"] for x in cur_items],
                                hole=0.4,
                                textinfo="label+percent",
                                textfont=dict(size=11),
                                marker=dict(line=dict(color="white", width=2))
                            ))
                            fig_cur.update_layout(height=280, margin=dict(l=0,r=0,t=10,b=0),
                                                  paper_bgcolor="white", showlegend=False)
                            st.plotly_chart(fig_cur, use_container_width=True, key="sim_pie_cur")
                        with bc_right:
                            st.markdown(f"**{sim_action} 후 비중**")
                            fig_sim = go.Figure(go.Pie(
                                labels=[x["name"] for x in sim_items],
                                values=[x["value"] for x in sim_items],
                                hole=0.4,
                                textinfo="label+percent",
                                textfont=dict(size=11),
                                marker=dict(line=dict(color="white", width=2))
                            ))
                            fig_sim.update_layout(height=280, margin=dict(l=0,r=0,t=10,b=0),
                                                  paper_bgcolor="white", showlegend=False)
                            st.plotly_chart(fig_sim, use_container_width=True, key="sim_pie_after")

        # ── 손익분기점 계산기 ──────────────────────────────────
        with sim_tab2:
            st.markdown("#### 손익분기점 계산기")
            st.caption("손실 중인 종목에서 원금 회복까지 얼마나 올라야 하는지 계산합니다.")

            bep_col1, bep_col2 = st.columns(2)
            with bep_col1:
                bep_buy  = st.number_input("매수 평균가 (원)", min_value=1, value=50000, step=100, format="%d", key="bep_buy")
                bep_qty  = st.number_input("보유 수량 (주)", min_value=1, value=100, key="bep_qty")
            with bep_col2:
                bep_cur  = st.number_input("현재가 (원)", min_value=1, value=40000, step=100, format="%d", key="bep_cur")
                bep_fee  = st.number_input("매도 수수료율 (%)", min_value=0.0, value=0.015,
                                           step=0.001, format="%.3f", key="bep_fee")

            invested   = bep_buy * bep_qty
            cur_val    = bep_cur * bep_qty
            loss       = cur_val - invested
            loss_pct   = loss / invested * 100
            fee_rate   = bep_fee / 100
            bep_price  = bep_buy / (1 - fee_rate)
            need_pct   = (bep_price - bep_cur) / bep_cur * 100

            st.markdown("---")
            r1, r2, r3, r4 = st.columns(4)
            r1.metric("투자 원금",   f"{invested:,.0f}원")
            r2.metric("현재 평가",   f"{cur_val:,.0f}원")
            r3.metric("평가 손익",   f"{loss:+,.0f}원", f"{loss_pct:+.2f}%")
            r4.metric("손익분기 주가", f"{bep_price:,.0f}원")

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

            if need_pct > 0:
                st.markdown(f"""
                <div style='background:#fff0f0;border-left:4px solid #e03131;border-radius:8px;
                    padding:16px 20px;font-size:14px;color:#333;line-height:1.8;'>
                    본전을 찾으려면 현재가 대비 <b style='color:#e03131;font-size:17px;'>+{need_pct:.2f}%</b> 상승이 필요합니다.<br>
                    현재 손실률 <b>{loss_pct:.2f}%</b>를 회복하려면 <b>{need_pct:.2f}%</b> 더 올라야 합니다.
                    (수수료 {bep_fee:.3f}% 포함)
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style='background:#f0fff4;border-left:4px solid #2f9e44;border-radius:8px;
                    padding:16px 20px;font-size:14px;color:#333;line-height:1.8;'>
                    현재 수익 중입니다. 수익률 <b style='color:#2f9e44;font-size:17px;'>{loss_pct:+.2f}%</b>
                </div>
                """, unsafe_allow_html=True)

            # 회복 시나리오 테이블
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            st.markdown("**회복 시나리오**")
            scenarios = []
            for pct in [5, 10, 15, 20, 30, 50]:
                target = bep_cur * (1 + pct/100)
                profit = target * bep_qty * (1 - fee_rate) - invested
                scenarios.append({
                    "상승률": f"+{pct}%",
                    "목표 주가": f"{target:,.0f}원",
                    "예상 손익": f"{profit:+,.0f}원",
                    "손익률": f"{profit/invested*100:+.2f}%",
                    "본전 달성": "✅" if profit >= 0 else "❌"
                })
            st.dataframe(pd.DataFrame(scenarios), use_container_width=True, hide_index=True)

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

    @st.cache_data(ttl=3600)
    def get_calendar_data():
        return ask_perplexity("""
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

    with st.spinner("경제 일정 불러오는 중..."):
        calendar_result = get_calendar_data()

    items = calendar_result.strip().split("---")
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


elif page == "AI 추천":
    import re as _re
    from datetime import date

    today_str = date.today().strftime("%Y.%m.%d")

    st.title("AI 투자 추천")
    st.markdown(
        "<div style='background:#fffbeb;border:1px solid #fcd34d;border-radius:6px;"
        "padding:12px 16px;font-size:13px;color:#92400e;margin-bottom:20px;line-height:1.8;'>"
        "⚠️ 본 추천은 AI가 공개된 뉴스·공시·리포트를 수집·분석한 참고 정보입니다. 투자 판단과 책임은 본인에게 있습니다.<br>"
        "보수적 분석 기준 적용 — 펀더멘털·컨센서스 다수 의견·리스크 동시 검토. 단기 급등 모멘텀 종목 배제. 확실하지 않으면 추천 불가 판정 포함."
        "</div>",
        unsafe_allow_html=True,
    )

    # ── 캐시 함수 정의 ──────────────────────────────────────────
    @st.cache_data(ttl=1800)
    def _ai_stock(today):
        prompt = (
            f"오늘은 {today}이야. 한국 주식시장에서 오늘 기준 최신 뉴스, DART 공시, 증권사 리포트를 종합 분석해서 "
            f"보수적 관점의 매수 추천 종목 3~5개를 한국어로 제시해줘.\n\n"
            f"[분석 기준]\n"
            f"- 펀더멘털 우선: 실적 성장성, 재무건전성, 영업이익률 기반\n"
            f"- 증권사 컨센서스 다수(3곳 이상) 매수 의견 종목만\n"
            f"- 단기 급등 모멘텀만 있는 종목 배제\n"
            f"- 리스크를 추천 이유만큼 비중 있게 명시\n"
            f"- 근거 불충분 시 해당 종목 추천 불가 판정\n"
            f"- 중장기(3~12개월) 관점\n\n"
            f"각 종목마다 아래 형식 엄수. 구분자는 ===.\n\n"
            f"종목명: 종목명\n투자의견: 매수/중립/매도\n목표주가: 원\n"
            f"손절기준: 현재가 대비 몇% 하락 시\n추천근거: 3~4문장. 실적·공시·리포트 근거 포함.\n"
            f"리스크: 2~3문장. 구체적으로.\n투자기간: 단기/중기/장기\n확신도: 상/중/하\n===\n"
            f"규칙: 대괄호 숫자 각주 절대 금지. 별표 마크다운 절대 금지."
        )
        res = ask_perplexity(prompt)
        res = _re.sub(r'\[\d+\]', '', res)
        res = _re.sub(r'\*\*?(.*?)\*\*?', r'\1', res)
        return res

    @st.cache_data(ttl=1800)
    def _ai_sector(today):
        prompt = (
            f"오늘은 {today}이야. 한국 주식시장에서 보수적 관점으로 지금 주목할 섹터 TOP3를 선정하고 "
            f"각 섹터마다 대표 종목 2개씩 제시해줘. 단기 테마가 아닌 구조적 성장 섹터 우선.\n\n"
            f"각 섹터마다 아래 형식 엄수. 구분자는 ===.\n\n"
            f"섹터명: 섹터명\n선정이유: 2~3문장. 구조적 성장 근거.\n리스크: 1~2문장.\n"
            f"대표종목1: 종목명 — 한 줄 이유\n대표종목2: 종목명 — 한 줄 이유\n===\n"
            f"규칙: 대괄호 숫자 각주 절대 금지. 별표 마크다운 절대 금지."
        )
        res = ask_perplexity(prompt)
        res = _re.sub(r'\[\d+\]', '', res)
        res = _re.sub(r'\*\*?(.*?)\*\*?', r'\1', res)
        return res

    @st.cache_data(ttl=1800)
    def _ai_warning(today):
        prompt = (
            f"오늘은 {today}이야. 오늘 기준 한국 주식시장에서 악재 공시, 실적 쇼크, "
            f"대규모 손실, 대주주 매도, 상장폐지 위험 등 위험 신호 종목 3~5개를 찾아줘.\n\n"
            f"각 종목마다 아래 형식 엄수. 구분자는 ===.\n\n"
            f"종목명: 종목명\n위험유형: 악재공시/실적쇼크/대주주매도/기타\n"
            f"위험내용: 2~3문장. 구체적 수치 포함.\n주가영향: 단기 하락 예상 폭 또는 영향\n"
            f"대응방안: 보유자를 위한 1~2문장 조언\n===\n"
            f"규칙: 대괄호 숫자 각주 절대 금지. 별표 마크다운 절대 금지."
        )
        res = ask_perplexity(prompt)
        res = _re.sub(r'\[\d+\]', '', res)
        res = _re.sub(r'\*\*?(.*?)\*\*?', r'\1', res)
        return res

    @st.cache_data(ttl=1800)
    def _ai_dart(today):
        prompt = (
            f"오늘은 {today}이야. 오늘 DART에 올라온 한국 상장사 주요 공시 중 "
            f"주가에 큰 영향을 줄 수 있는 공시 5~8개를 정리해줘.\n\n"
            f"각 공시마다 아래 형식 엄수. 구분자는 ===.\n\n"
            f"종목명: 종목명\n공시유형: 유상증자/자사주매입/실적공시/대표이사변경/기타\n"
            f"영향도: HIGH/MID/LOW\n공시내용: 2문장 요약\n주가방향: 상승요인/하락요인/중립\n===\n"
            f"규칙: 대괄호 숫자 각주 절대 금지. 별표 마크다운 절대 금지."
        )
        res = ask_perplexity(prompt)
        res = _re.sub(r'\[\d+\]', '', res)
        res = _re.sub(r'\*\*?(.*?)\*\*?', r'\1', res)
        return res

    @st.cache_data(ttl=1800)
    def _ai_consensus(today):
        prompt = (
            f"오늘은 {today}이야. 최근 1주일 내 국내 주요 증권사(미래에셋·삼성·KB·신한·NH 등)가 "
            f"발간한 리포트 중 목표주가 상향·하향 종목을 각각 3~5개씩 정리해줘.\n\n"
            f"각 항목마다 아래 형식 엄수. 구분자는 ===.\n\n"
            f"구분: 상향 또는 하향\n종목명: 종목명\n증권사: 증권사명\n"
            f"기존목표가: 원\n신규목표가: 원\n변경이유: 1~2문장\n===\n"
            f"규칙: 대괄호 숫자 각주 절대 금지. 별표 마크다운 절대 금지."
        )
        res = ask_perplexity(prompt)
        res = _re.sub(r'\[\d+\]', '', res)
        res = _re.sub(r'\*\*?(.*?)\*\*?', r'\1', res)
        return res

    # ── 공통 함수 ──────────────────────────────────────────────
    def render_card(title, body_html, border_color="#6366f1", bg="#fafafe"):
        st.markdown(
            f"<div style='background:{bg};border:1px solid #e8eaed;"
            f"border-left:4px solid {border_color};border-radius:8px;"
            f"padding:20px 24px;margin-bottom:14px;'>"
            f"<div style='font-size:15px;font-weight:700;color:#1a1e2e;margin-bottom:10px;'>{title}</div>"
            f"<div style='font-size:14px;color:#333;line-height:1.85;'>{body_html}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    def parse_items(raw):
        return [x.strip() for x in raw.split("===") if x.strip()]

    def parse_fields(item, keys):
        fields = {}
        for line in item.split("\n"):
            line = line.strip()
            for k in keys:
                if line.startswith(f"{k}:"):
                    fields[k] = line.replace(f"{k}:", "").strip()
        return fields

    # ── 탭 ────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "추천 종목", "주목 섹터", "위험 종목", "주요 공시", "증권사 컨센서스"
    ])

    with tab1:
        _, col_btn = st.columns([5, 1])
        if col_btn.button("새로고침", key="btn_stock"):
            _ai_stock.clear()
            st.rerun()
        with st.spinner("추천 종목 분석 중..."):
            stock_res = _ai_stock(today_str)
        for item in parse_items(stock_res):
            f = parse_fields(item, ["종목명","투자의견","목표주가","손절기준","추천근거","리스크","투자기간","확신도"])
            if not f.get("종목명"): continue
            확신 = f.get("확신도","중")
            불가 = "하" in 확신 or "불가" in 확신
            border = "#ef4444" if 불가 else ("#22c55e" if "상" in 확신 else "#6366f1")
            badge = "🚫 추천 불가" if 불가 else ("⭐⭐⭐ 확신 높음" if "상" in 확신 else "⭐⭐ 확신 보통")
            body = (
                f"<div style='margin-bottom:10px;'>"
                f"<span style='background:{border};color:white;font-size:11px;font-weight:700;padding:2px 8px;border-radius:4px;margin-right:8px;'>{badge}</span>"
                f"<span style='font-size:12px;color:#666;'>투자기간: {f.get('투자기간','-')} | 목표주가: {f.get('목표주가','-')} | 손절기준: {f.get('손절기준','-')}</span>"
                f"</div>"
                f"<b>추천 근거</b><br>{f.get('추천근거','-')}<br><br>"
                f"<b style='color:#ef4444;'>⚠️ 리스크</b><br>{f.get('리스크','-')}"
            )
            render_card(f"{f.get('종목명','-')}  ({f.get('투자의견','-')})", body, border_color=border)

    with tab2:
        _, col_btn = st.columns([5, 1])
        if col_btn.button("새로고침", key="btn_sector"):
            _ai_sector.clear()
            st.rerun()
        with st.spinner("섹터 분석 중..."):
            sector_res = _ai_sector(today_str)
        colors = ["#6366f1", "#0ea5e9", "#22c55e"]
        for i, item in enumerate(parse_items(sector_res)[:3]):
            f = parse_fields(item, ["섹터명","선정이유","리스크","대표종목1","대표종목2"])
            if not f.get("섹터명"): continue
            body = (
                f"{f.get('선정이유','-')}<br><br>"
                f"<b style='color:#ef4444;'>⚠️ 리스크</b><br>{f.get('리스크','-')}<br><br>"
                f"<b>대표 종목</b><br>• {f.get('대표종목1','-')}<br>• {f.get('대표종목2','-')}"
            )
            render_card(f"#{i+1} {f.get('섹터명','-')}", body, border_color=colors[i % 3])

    with tab3:
        st.markdown(
            "<div style='background:#fff0f0;border:1px solid #fca5a5;border-radius:6px;"
            "padding:10px 16px;font-size:12px;color:#991b1b;margin-bottom:18px;'>"
            "🚨 악재 공시·실적 쇼크·이상 매도 신호 포착 종목. 보유 중이라면 반드시 확인하세요."
            "</div>",
            unsafe_allow_html=True,
        )
        _, col_btn = st.columns([5, 1])
        if col_btn.button("새로고침", key="btn_warning"):
            _ai_warning.clear()
            st.rerun()
        with st.spinner("위험 신호 스캔 중..."):
            warning_res = _ai_warning(today_str)
        for item in parse_items(warning_res):
            f = parse_fields(item, ["종목명","위험유형","위험내용","주가영향","대응방안"])
            if not f.get("종목명"): continue
            body = (
                f"<span style='background:#ef4444;color:white;font-size:11px;font-weight:700;"
                f"padding:2px 8px;border-radius:4px;display:inline-block;margin-bottom:10px;'>{f.get('위험유형','-')}</span><br>"
                f"<b>위험 내용</b><br>{f.get('위험내용','-')}<br><br>"
                f"<b>주가 영향</b><br>{f.get('주가영향','-')}<br><br>"
                f"<b style='color:#22c55e;'>💡 대응 방안</b><br>{f.get('대응방안','-')}"
            )
            render_card(f.get("종목명","-"), body, border_color="#ef4444", bg="#fff8f8")

    with tab4:
        _, col_btn = st.columns([5, 1])
        if col_btn.button("새로고침", key="btn_dart"):
            _ai_dart.clear()
            st.rerun()
        with st.spinner("주요 공시 분석 중..."):
            dart_res = _ai_dart(today_str)
        for item in parse_items(dart_res):
            f = parse_fields(item, ["종목명","공시유형","영향도","공시내용","주가방향"])
            if not f.get("종목명"): continue
            영향도 = f.get("영향도","MID")
            border = "#ef4444" if 영향도=="HIGH" else "#f97316" if 영향도=="MID" else "#6b7280"
            방향 = f.get("주가방향","-")
            방향색 = "#22c55e" if "상승" in 방향 else "#ef4444" if "하락" in 방향 else "#6b7280"
            body = (
                f"<span style='background:{border};color:white;font-size:11px;font-weight:700;"
                f"padding:2px 8px;border-radius:4px;margin-right:6px;'>영향도 {영향도}</span>"
                f"<span style='background:{방향색};color:white;font-size:11px;font-weight:700;"
                f"padding:2px 8px;border-radius:4px;'>{방향}</span><br><br>"
                f"<b>공시 유형:</b> {f.get('공시유형','-')}<br><br>"
                f"{f.get('공시내용','-')}"
            )
            render_card(f.get("종목명","-"), body, border_color=border)

    with tab5:
        _, col_btn = st.columns([5, 1])
        if col_btn.button("새로고침", key="btn_consensus"):
            _ai_consensus.clear()
            st.rerun()
        with st.spinner("증권사 리포트 수집 중..."):
            consensus_res = _ai_consensus(today_str)
        items = parse_items(consensus_res)
        상향 = [x for x in items if "상향" in x[:60]]
        하향 = [x for x in items if "하향" in x[:60]]
        col_up, col_dn = st.columns(2)
        for col, group, color, label in [
            (col_up, 상향, "#22c55e", "📈 목표주가 상향"),
            (col_dn, 하향, "#ef4444", "📉 목표주가 하향"),
        ]:
            with col:
                st.markdown(
                    f"<div style='font-size:15px;font-weight:700;color:{color};margin-bottom:12px;'>{label}</div>",
                    unsafe_allow_html=True,
                )
                for item in group:
                    f = parse_fields(item, ["종목명","증권사","기존목표가","신규목표가","변경이유"])
                    if not f.get("종목명"): continue
                    body = (
                        f"<b>{f.get('증권사','-')}</b>  |  "
                        f"{f.get('기존목표가','-')} → "
                        f"<b style='color:{color};'>{f.get('신규목표가','-')}</b><br><br>"
                        f"{f.get('변경이유','-')}"
                    )
                    render_card(f.get("종목명","-"), body, border_color=color)