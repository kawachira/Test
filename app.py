import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import random

# --- 1. ตั้งค่าหน้าเว็บ (Web Config) ---
st.set_page_config(page_title="AI Stock Master KR", page_icon="💎", layout="wide")

# --- 2. CSS ปรับแต่ง (CSS Styles) ---
st.markdown("""
    <style>
    .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; }
    h1 { text-align: center; font-size: 2.8rem !important; margin-bottom: 10px; }
    div[data-testid="stForm"] {
        border: none; padding: 30px; border-radius: 20px;
        background-color: var(--secondary-background-color);
        box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        max-width: 800px; margin: 0 auto;
    }
    div[data-testid="stFormSubmitButton"] button {
        width: 100%; border-radius: 12px; font-size: 1.2rem; font-weight: bold; padding: 15px 0;
    }
    div[data-testid="metric-container"] label { font-size: 1.1rem; }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] { font-size: 1.8rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ส่วนหัวข้อ (Header) ---
st.markdown("<h1>💎 Ai<br><span style='font-size: 1.5rem; opacity: 0.7;'>지능형 주식 분석 시스템</span></h1>", unsafe_allow_html=True)
st.write("")

# --- Form ค้นหา (Search Form) ---
col_space1, col_form, col_space2 = st.columns([1, 2, 1])
with col_form:
    with st.form(key='search_form'):
        st.markdown("### 🔍 종목 검색 (Search Stock)")
        c1, c2 = st.columns([3, 1])
        with c1:
            symbol_input = st.text_input("티커 입력 (예: AMZN, EOSE, RKLB, TSLA):", value="EOSE").upper().strip()
        with c2:
            timeframe = st.selectbox("시간대 (Timeframe):", ["1h (1시간)", "1d (일봉)", "1wk (주봉)"], index=1)
            if "1wk" in timeframe: tf_code = "1wk"
            elif "1h" in timeframe: tf_code = "1h"
            else: tf_code = "1d"
            
        submit_btn = st.form_submit_button("🚀 분석 시작 / 새로고침")

# --- 4. Helper Functions ---
def arrow_html(change):
    if change is None: return ""
    return "<span style='color:#16a34a;font-weight:600'>▲</span>" if change > 0 else "<span style='color:#dc2626;font-weight:600'>▼</span>"

def get_rsi_interpretation(rsi):
    if rsi >= 80: return "🔴 **초과매수 (80+):** 매수세 과열! 급락 주의 (Extreme Overbought)"
    elif rsi >= 70: return "🟠 **과매수 구간 (70-80):** 가격 부담, 곧 조정 가능성 있음 (Overbought)"
    elif rsi >= 55: return "🟢 **상승세 (55-70):** 매수세 우위, 강한 흐름 (Bullish)"
    elif rsi >= 45: return "⚪ **횡보/중립 (45-55):** 방향성 탐색 중 (Neutral)"
    elif rsi >= 30: return "🟠 **하락세 (30-45):** 매도세 우위, 하락 주의 (Bearish)"
    elif rsi > 20: return "🟢 **과매도 구간 (20-30):** 저평가 국면, 반등 기대 (Oversold)"
    else: return "🟢 **침체 구간 (<20):** 패닉 셀링 종료 임박 (Extreme Oversold)"

def get_pe_interpretation(pe):
    if isinstance(pe, str) and pe == 'N/A': return "⚪ N/A (적자/수익 없음)"
    if pe < 0: return "🔴 적자 기업 (Earnings 마이너스)"
    if pe < 15: return "🟢 저평가 (Value Stock)"
    if pe < 30: return "🟡 적정 주가"
    return "🟠 고평가 (Growth Stock)"

# --- 5. Get Data ---
@st.cache_data(ttl=60, show_spinner=False)
def get_data(symbol, interval):
    try:
        ticker = yf.Ticker(symbol)
        period_val = "730d" if interval == "1h" else "10y"
        df = ticker.history(period=period_val, interval=interval)
        
        stock_info = {
            'longName': ticker.info.get('longName', symbol),
            'trailingPE': ticker.info.get('trailingPE', 'N/A'),
            'regularMarketPrice': ticker.info.get('regularMarketPrice'),
            'regularMarketChange': ticker.info.get('regularMarketChange'),
            'regularMarketChangePercent': ticker.info.get('regularMarketChangePercent'),
            'preMarketPrice': ticker.info.get('preMarketPrice'),
            'preMarketChange': ticker.info.get('preMarketChange'),
            'preMarketChangePercent': ticker.info.get('preMarketChangePercent'),
            'postMarketPrice': ticker.info.get('postMarketPrice'),
            'postMarketChange': ticker.info.get('postMarketChange'),
            'postMarketChangePercent': ticker.info.get('postMarketChangePercent'),
        }
        
        if stock_info['regularMarketPrice'] is None and not df.empty:
             stock_info['regularMarketPrice'] = df['Close'].iloc[-1]
             stock_info['regularMarketChange'] = df['Close'].iloc[-1] - df['Close'].iloc[-2]
             stock_info['regularMarketChangePercent'] = (stock_info['regularMarketChange'] / df['Close'].iloc[-2])

        return df, stock_info
    except:
        return None, None

# --- 6. AI Logic (Korean Translated) ---
def analyze_market_structure(price, ema20, ema50, ema200, rsi):
    report = {
        "technical": {},
        "context": "",
        "action": {},
        "status_color": "",
        "banner_title": ""
    }

    # --- Helper: Random Sentence Picker ---
    def pick_one(sentences):
        return random.choice(sentences)

    # --- Scenario 1: Super Strong Uptrend ---
    if price > ema200 and price > ema50 and price > ema20:
        report["status_color"] = "green"
        report["banner_title"] = pick_one([
            "Bullish Mode: 강력한 상승장 진입",
            "Strong Uptrend: 시장보다 강한 종목",
            "Momentum High: 상승 모멘텀 최고조"
        ])
        
        report["technical"] = {
            "structure": "정배열 상태, 모든 이평선 위에 가격 위치 (Price > EMA20 > 50 > 200)",
            "status": pick_one([
                "거래량 동반 상승, 매수세 강력함",
                "현재 시장의 주도주 (Winner Stock)",
                "상승 추세가 뚜렷하여 쉽게 꺾이지 않을 기세"
            ])
        }
        
        ctx_options = [
            "보유자는 꽉 붙드세요! 아직 프리미엄이 붙어있는 상태입니다. 서둘러 매도하지 마세요.",
            "세력(기관/외국인)이 주가를 관리하는 듯한 모습입니다. 눌림목은 있어도 추세는 살아있습니다.",
            "지금은 수익을 극대화할 시기(Harvest Time)입니다. 추세를 믿으세요."
        ]
        report["context"] = pick_one(ctx_options)
        
        # Action Plan
        strategy = "**전략: 이익 실현 & 트레일링 스탑 (Let Profit Run)**"
        
        if rsi > 75: 
            action_1 = "⚠️ **경고:** RSI 초과매수 상태! 추격 매수 금지."
            action_2 = "단기 트레이더: 분할 매도로 수익을 챙기고(Lock Profit), 눌림목을 기다리세요."
        else:
            action_1 = "🟢 **보유자:** 지속 보유 (Hold). EMA 20 이탈 시 매도 고려."
            action_2 = f"🟡 **미보유자:** EMA 20 ({ema20:.2f}) 근처까지 눌릴 때 매수 (Buy on Dip)."

        report["action"] = {"strategy": strategy, "steps": [action_1, action_2]}

    # --- Scenario 2: Correction in Uptrend ---
    elif price > ema200 and price < ema20:
        report["status_color"] = "orange"
        report["banner_title"] = pick_one([
            "Correction: 상승 중 조정?",
            "Healthy Pullback: 건전한 눌림목",
            "Short-term Weakness: 단기 매도세 출현"
        ])

        report["technical"] = {
            "structure": "EMA 20 하향 돌파, EMA 50 지지 테스트 중 (중기 조정)",
            "status": "차익 실현 매물이 나오고 있으나, 장기 추세(EMA 200)는 여전히 상승"
        }
        
        ctx_options = [
            "시장이 지지선을 테스트 중입니다. EMA 50 부근이 중요한 승부처입니다.",
            "단기 트레이더를 털어내는 과정(Shake out)일 수 있습니다. 펀더멘털이 좋다면 기회입니다.",
            "주의! 여기서 지지받지 못하면 EMA 200까지 밀릴 수 있습니다."
        ]
        report["context"] = pick_one(ctx_options)
        
        strategy = "**전략: 관망 (Wait & See) - 반등 신호 확인**"
        action_1 = f"🎯 **매수 포인트:** EMA 50 ({ema50:.2f}) 지지 확인 후 양봉 발생 시 진입."
        
        if price < ema50: 
             action_2 = f"주의! EMA 50 이탈 발생. 다음 지지선인 EMA 200 ({ema200:.2f})까지 관망하세요."
        else:
             action_2 = f"🛡️ **손절가:** {ema50:.2f} 하향 돌파 시 일단 후퇴하여 상황을 지켜보세요."

        report["action"] = {"strategy": strategy, "steps": [action_1, action_2]}

    # --- Scenario 3: Downtrend ---
    elif price < ema200 and price < ema50:
        if price < ema20:
            # Oversold Bounce
            if rsi < 25:
                report["status_color"] = "orange" 
                report["banner_title"] = "Oversold Bounce: 낙폭 과대, 기술적 반등 기대"
                report["technical"] = {
                    "structure": "과매도 구간 진입 (RSI < 25), 급격한 하락",
                    "status": "패닉 셀링(Panic Sell) 발생, 곧 기술적 반등이 나올 수 있음"
                }
                report["context"] = "펀더멘털 대비 과도한 하락이거나 공포 심리가 극에 달했습니다. 단기 반등을 노리는 매수세가 들어올 수 있습니다."
                strategy = "**전략: 역추세 매매 (Contrarian)**"
                action_1 = "🧨 **고수익/고위험:** 짧게 치고 빠지기 (Hit & Run). 오래 들고 있지 마세요."
                action_2 = "반등 시 EMA 20 근처에 오면 즉시 매도하세요."
            else:
                report["status_color"] = "red"
                report["banner_title"] = pick_one([
                    "Bearish Market: 하락장 지배",
                    "Downtrend: 완벽한 역배열",
                    "Danger Zone: 위험 구역"
                ])
                report["technical"] = {
                    "structure": "완연한 하락 추세 (Downtrend), 신저가 경신 중",
                    "status": "곰(Bear)이 시장을 지배함. 지지선보다 저항선이 더 강력하게 작용"
                }
                ctx_options = [
                    "소나기는 피해야 합니다. 바닥을 다질 때까지 기다리세요.",
                    "지금의 상승은 '데드캣 바운스'일 확률이 높습니다. 떨어지는 칼날을 잡지 마세요.",
                    "지금은 '현금이 왕(Cash is King)'입니다."
                ]
                report["context"] = pick_one(ctx_options)
                
                strategy = "**전략: 방어적 투자 / 현금 확보 (Cash is King)**"
                action_1 = "매수 금지! (Don't catch a falling knife) 하락이 멈출 때까지 기다리세요."
                action_2 = "보유자는 손절(Stop Loss)을 고려하거나, 반등 시 매도하여 비중을 줄이세요."
        else:
             # Rebound in Downtrend
            report["status_color"] = "orange"
            report["banner_title"] = "회복 시도 (하락장 속 반등)"
            report["technical"] = {
                "structure": "하락 추세 속 기술적 반등 (Technical Rebound)",
                "status": "단기 매수세 유입 중이나, 상단 저항이 두터움"
            }
            report["context"] = "오늘의 상승은 기술적 반등(Dead Cat Bounce)일 수 있습니다. 큰 추세는 여전히 하락입니다."
            strategy = "**전략: 단기 반등 노리기 (Play for Rebound)**"
            action_1 = "초단기 트레이딩(Scalping)만 유효합니다. 장기 보유 금지."
            action_2 = f"주요 저항선 **EMA 50 ({ema50:.2f})** 돌파 실패 시 즉시 매도."

        report["action"] = {"strategy": strategy, "steps": [action_1, action_2]}

    # --- Scenario 4: Recovery / Sideway ---
    else:
        report["status_color"] = "yellow"
        report["banner_title"] = pick_one([
            "Sideway: 방향성 탐색 중",
            "Recovery: 바닥 다지기"
        ])
        report["technical"] = {
            "structure": "이동평균선들이 얽혀있거나(혼조세), 회복을 시도하는 단계",
            "status": "매수와 매도 힘의 균형(Equilibrium) 상태. 확실한 신호 대기 중"
        }
        report["context"] = "시장을 움직일 명확한 재료가 부족합니다. 박스권 등락이 반복되어 매매가 까다롭습니다."
        
        strategy = "**전략: 관망 및 확인 (Wait for Confirmation)**"
        action_1 = f"중기 투자자: 주가가 EMA 200 위에 안착할 때까지 현금을 보유하세요."
        action_2 = f"단기 투자자: 박스권 매매 - 지지선 {min(ema20,ema50):.2f} 매수 / 저항선 {max(ema20,ema50,ema200):.2f} 매도."
        
        report["action"] = {"strategy": strategy, "steps": [action_1, action_2]}

    return report

# --- 7. Display ---
if submit_btn:
    st.divider()
    with st.spinner(f"AI가 {symbol_input} 데이터를 분석 중입니다..."):
        df, info = get_data(symbol_input, tf_code)

        if df is not None and not df.empty and len(df) > 200:
            df['EMA20'] = ta.ema(df['Close'], length=20); df['EMA50'] = ta.ema(df['Close'], length=50)
            df['EMA200'] = ta.ema(df['Close'], length=200); df['RSI'] = ta.rsi(df['Close'], length=14)
            
            last = df.iloc[-1]
            price = info['regularMarketPrice'] if info['regularMarketPrice'] else last['Close']
            rsi = last['RSI']
            ema20=last['EMA20']; ema50=last['EMA50']; ema200=last['EMA200']
            
            ai_report = analyze_market_structure(price, ema20, ema50, ema200, rsi)

            # Header
            st.markdown(f"<h2 style='text-align: center; margin-top: -15px; margin-bottom: 25px;'>🏢 {info['longName']} ({symbol_input})</h2>", unsafe_allow_html=True)
            
            # Info Section
            c1, c2 = st.columns(2)
            with c1:
                reg_price = info.get('regularMarketPrice')
                reg_chg = info.get('regularMarketChange')
                
                if reg_price and reg_chg:
                    prev_c = reg_price - reg_chg
                    if prev_c != 0:
                        reg_pct = (reg_chg / prev_c) * 100
                    else: reg_pct = 0.0
                else: reg_pct = 0.0
                
                color_text = "#16a34a" if reg_chg and reg_chg > 0 else "#dc2626"
                bg_color = "#e8f5ec" if reg_chg and reg_chg > 0 else "#fee2e2"
                
                # Main Price
                st.markdown(f"""
                <div style="margin-bottom:5px; display: flex; align-items: center; gap: 15px; flex-wrap: wrap;">
                  <div style="font-size:40px; font-weight:600; line-height: 1;">
                    {reg_price:,.2f} <span style="font-size: 20px; color: #6b7280; font-weight: 400;">USD</span>
                  </div>
                  <div style="
                    display:inline-flex; align-items:center; gap:6px; background:{bg_color}; color:{color_text};
                    padding:4px 12px; border-radius:999px; font-size:18px; font-weight:500;">
                    {arrow_html(reg_chg)} {reg_chg:+.2f} ({reg_pct:.2f}%)
                  </div>
                </div>
                """, unsafe_allow_html=True)

                # Pre/Post Market
                pre_p = info.get('preMarketPrice'); pre_c = info.get('preMarketChange'); pre_pc = info.get('preMarketChangePercent')
                post_p = info.get('postMarketPrice'); post_c = info.get('postMarketChange'); post_pc = info.get('postMarketChangePercent')
                
                if pre_p and reg_price and reg_price != 0: pre_pc = ((pre_p - reg_price) / reg_price) * 100
                if post_p and reg_price and reg_price != 0: post_pc = ((post_p - reg_price) / reg_price) * 100

                extra_html = ""
                if pre_p and pre_c is not None:
                    extra_html += f"<div>☀️ 장전 (Pre): <b>{pre_p:.2f}</b> <span style='color:{'#16a34a' if pre_c>0 else '#dc2626'}'>{arrow_html(pre_c)} {pre_c:+.2f} ({pre_pc:+.2f}%)</span></div>"
                if post_p and post_c is not None:
                    extra_html += f"<div>🌙 장후 (Post): <b>{post_p:.2f}</b> <span style='color:{'#16a34a' if post_c>0 else '#dc2626'}'>{arrow_html(post_c)} {post_c:+.2f} ({post_pc:+.2f}%)</span></div>"
                
                if extra_html:
                    st.markdown(f"<div style='font-size:14px; color:#6b7280; display:flex; gap: 15px; flex-wrap: wrap; margin-top: 5px;'>{extra_html}</div>", unsafe_allow_html=True)

            # AI Status Banner
            if tf_code == "1h": tf_label = "시간봉 (1H)"
            elif tf_code == "1wk": tf_label = "주봉 (Weekly)"
            else: tf_label = "일봉 (Daily)"
            
            st_color = ai_report["status_color"]
            main_status = ai_report["banner_title"]
            
            if st_color == "green": c2.success(f"📈 {main_status}\n\n**{tf_label}**")
            elif st_color == "red": c2.error(f"📉 {main_status}\n\n**{tf_label}**")
            else: c2.warning(f"⚖️ {main_status}\n\n**{tf_label}**")

            # Metrics
            c3, c4 = st.columns(2)
            with c3:
                st.metric("📊 P/E Ratio (주가수익비율)", f"{info['trailingPE']:.2f}" if isinstance(info['trailingPE'], (int,float)) else "N/A")
                st.caption(get_pe_interpretation(info['trailingPE']))
            with c4:
                rsi_lbl = "Overbought" if rsi>=70 else ("Oversold" if rsi<=30 else "Neutral")
                st.metric("⚡ RSI (14)", f"{rsi:.2f}", rsi_lbl, delta_color="inverse" if rsi>70 else "normal")
                st.caption(get_rsi_interpretation(rsi))

            st.write("") 

            # Analysis Section & AI Report
            c_ema, c_ai = st.columns([1.5, 2])
            with c_ema:
                st.subheader("📉 이동평균선 (EMA)")
                st.markdown(f"""
                <div style='background-color: var(--secondary-background-color); padding: 15px; border-radius: 10px;'>
                    <div style='display:flex; justify-content:space-between; margin-bottom:5px;'><span>🔵 EMA 20 (단기)</span> <b>{ema20:.2f}</b></div>
                    <div style='display:flex; justify-content:space-between; margin-bottom:5px;'><span>🟠 EMA 50 (중기)</span> <b>{ema50:.2f}</b></div>
                    <div style='display:flex; justify-content:space-between;'><span>⚫ EMA 200 (장기)</span> <b>{ema200:.2f}</b></div>
                </div>
                """, unsafe_allow_html=True)
                
                st.subheader("🚧 매매 전략 (지지/저항)")
                supports, resistances = [], []
                res_val = df['High'].tail(60).max(); resistances.append((res_val, "전고점 (60일)"))
                if price < ema200: resistances.append((ema200, "EMA 200 저항선"))
                if price > ema200: supports.extend([(ema20, "EMA 20"), (ema50, "EMA 50"), (ema200, "EMA 200")])
                else: supports.extend([(df['Low'].tail(60).min(), "전저점"), (df['Low'].tail(200).min(), "장기 최저점")])
                
                st.markdown("#### 🟢 지지선 (Support)")
                for v, d in supports: 
                    if v < price: st.write(f"- **{v:.2f}** : {d}")
                st.markdown("#### 🔴 저항선 (Resistance)")
                for v, d in resistances:
                    if v > price: st.write(f"- **{v:.2f}** : {d}")

            with c_ai:
                st.subheader("🤖 AI INTELLIGENT REPORT")
                with st.chat_message("assistant"):
                    st.markdown("### 🧠 1. 기술적 분석 (Technical Analysis):")
                    st.markdown(f"- **구조:** {ai_report['technical']['structure']}")
                    st.markdown(f"- **상태:** {ai_report['technical']['status']}")
                    
                    st.markdown("---")
                    
                    st.markdown("### 📚 2. 시장 상황 설명 (Context):")
                    st.markdown(f"- {ai_report['context']}")
                    
                    st.markdown("---")
                    
                    st.markdown("### ✅ 3. 대응 전략 (Action Plan):")
                    st.markdown(f"🟡 {ai_report['action']['strategy']}")
                    for idx, step in enumerate(ai_report['action']['steps'], 1):
                        st.markdown(f"{idx}. {step}")

            # --- พื้นที่ว่างด้านล่าง 50px (ตามที่ขอ ห้ามลบ) ---
            st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)

        elif df is not None: st.warning("⚠️ 데이터가 부족하여 계산할 수 없습니다 (Not enough data)."); st.line_chart(df['Close'])
        else: st.error(f"❌ 데이터를 찾을 수 없습니다: {symbol_input}")
