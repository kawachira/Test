import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import time
import random

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Stock Master", page_icon="💎", layout="wide")

# --- 2. CSS ปรับแต่งความสวยงาม ---
st.markdown("""
    <style>
    /* ลดระยะห่างด้านบน */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
    }

    /* ล็อคการเลื่อนหน้าจอ (Scroll) เป็นค่าเริ่มต้น */
    div[data-testid="stAppViewContainer"] {
        overflow: hidden !important;
    }

    /* จัด Title ให้อยู่ตรงกลาง */
    h1 {
        text-align: center;
        font-size: 2.8rem !important;
        margin-bottom: 10px;
    }
    
    /* กรอบค้นหาแบบใหม่ */
    div[data-testid="stForm"] {
        border: none;
        padding: 30px;
        border-radius: 20px;
        background-color: var(--secondary-background-color);
        box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        max-width: 800px;
        margin: 0 auto;
    }
    
    /* ปรับปุ่มกดให้เต็มและตัวใหญ่ */
    div[data-testid="stFormSubmitButton"] button {
        width: 100%;
        border-radius: 12px;
        font-size: 1.2rem;
        font-weight: bold;
        padding: 15px 0;
    }
    
    /* ปรับขนาดตัวหนังสือใน Metric ให้ใหญ่ขึ้น */
    div[data-testid="metric-container"] label { font-size: 1.1rem; }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] { font-size: 1.8rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ส่วนหัวข้อและค้นหา ---
st.markdown("<h1>💎 Ai<br><span style='font-size: 1.5rem; opacity: 0.7;'>ระบบวิเคราะห์หุ้นอัจฉริยะ</span></h1>", unsafe_allow_html=True)

st.write("") # เว้นระยะ

# สร้าง Form ค้นหา (จัดกึ่งกลาง)
col_space1, col_form, col_space2 = st.columns([1, 2, 1])

with col_form:
    with st.form(key='search_form'):
        st.markdown("### 🔍 ค้นหาหุ้นที่ต้องการ")
        c1, c2 = st.columns([3, 1])
        with c1:
            symbol_input = st.text_input("ชื่อหุ้น (เช่น AMZN,GOOGL,RKLB, TSLA):", value="EOSE").upper().strip()
        with c2:
            timeframe = st.selectbox("Timeframe:", ["1h (รายชั่วโมง)", "1d (รายวัน)", "1wk (รายสัปดาห์)"], index=1)
            
            # Logic แปลงค่าเป็น code ที่ yfinance เข้าใจ
            if "1wk" in timeframe: tf_code = "1wk"
            elif "1h" in timeframe: tf_code = "1h"
            else: tf_code = "1d"
        
        realtime_mode = st.checkbox("🔴 เปิดโหมด Real-time (ราคาขยับเองทุก 10 วิ)", value=False)
        submit_btn = st.form_submit_button("🚀 วิเคราะห์ทันที")

# --- 4. ฟังก์ชันช่วยแปลความหมาย & Helper Functions ---

def arrow_html(change):
    if change is None: return ""
    if change > 0:
        return "<span style='color:#16a34a;font-weight:600'>▲</span>"  # เขียว
    elif change < 0:
        return "<span style='color:#dc2626;font-weight:600'>▼</span>"  # แดง
    else:
        return "<span style='color:gray'>—</span>"

def get_rsi_interpretation(rsi):
    if rsi >= 80: return "🔴 **Extreme Overbought (80+):** แรงซื้อบ้าคลั่ง ระวังการเทขายรุนแรง (ห้ามไล่ราคา)"
    elif rsi >= 70: return "🟠 **Overbought (70-80):** ราคาเริ่มตึงตัว อาจมีการเทขายพักฐานเร็วๆ นี้"
    elif rsi >= 55: return "🟢 **Bullish Zone (55-70):** โมเมนตัมกระทิงครองตลาด ราคาแข็งแกร่ง"
    elif rsi >= 45: return "⚪ **Sideway/Neutral (45-55):** แรงซื้อขายก้ำกึ่ง รอเลือกทางที่ชัดเจน"
    elif rsi >= 30: return "🟠 **Bearish Zone (30-45):** โมเมนตัมหมีครองตลาด ระวังราคาไหลลงต่อ"
    elif rsi > 20: return "🟢 **Oversold (20-30):** ขายมากเกินไป เริ่มเข้าเขต 'ของถูก' ลุ้นเด้งรีบาวด์"
    else: return "🟢 **Extreme Oversold (<20):** ลงลึกมาก Panic Sell จบแล้ว เป็นจุดวัดใจซื้อสวนสั้นๆ"

def get_pe_interpretation(pe):
    if isinstance(pe, str) and pe == 'N/A': return "⚪ **N/A:** ไม่มีข้อมูล หรือบริษัทขาดทุน (คำนวณไม่ได้)"
    if pe < 0: return "🔴 **ขาดทุน (Negative P/E):** บริษัทยังไม่มีกำไร"
    if pe < 15: return "🟢 **หุ้นถูก (Low P/E):** ราคาต่ำเมื่อเทียบกับกำไร (Value Stock) หรือตลาดคาดหวังต่ำ"
    if pe < 30: return "🟡 **ราคาเหมาะสม (Average P/E):** ราคาอยู่ในเกณฑ์ค่าเฉลี่ยปกติ"
    return "🟠 **หุ้นแพง (High P/E):** ราคาสูง หรือตลาดคาดหวังการเติบโตสูงมาก (Growth Stock)"

# --- 5. ฟังก์ชันดึงข้อมูล (Cache) ---
@st.cache_data(ttl=5, show_spinner=False)
def get_data(symbol, interval):
    try:
        ticker = yf.Ticker(symbol)
        
        if interval == "1h": period_val = "730d"
        else: period_val = "10y"
            
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

# --- 6. ฟังก์ชันสมอง AI (ใหม่: สุ่มได้ + หลากหลาย) ---
def analyze_market_structure(price, ema20, ema50, ema200, rsi):
    report = {
        "technical": {},
        "context": "",
        "action": {},
        "status_color": "",
        "banner_title": ""
    }

    def pick_one(sentences):
        return random.choice(sentences)

    # --- Scenario 1: ขาขึ้นแข็งแกร่ง ---
    if price > ema200 and price > ema50 and price > ema20:
        report["status_color"] = "green"
        report["banner_title"] = pick_one([
            "Bullish Mode: กระทิงดุเต็มพิกัด",
            "Strong Uptrend: หุ้นแกร่งกว่าตลาด",
            "Momentum High: แรงส่งขาขึ้นรุนแรง"
        ])
        report["technical"] = {
            "structure": "ราคาเรียงตัวสวยงามยืนเหนือทุกเส้น (Price > EMA20 > 50 > 200)",
            "status": pick_one(["Volume เข้า แรงซื้อสนับสนุนชัดเจน", "กราฟทรงนี้คือผู้ชนะ (Winner Stock)", "Trend ขาขึ้นชัดเจน"])
        }
        report["context"] = pick_one([
            "ใครมีของกอดแน่นๆ ตลาดยังให้ค่า Premium กับหุ้นตัวนี้",
            "ทรงกราฟแบบนี้ รายใหญ่น่าจะยังคุมเกมอยู่",
            "เป็นช่วงเวลาโกยกำไร (Harvest Time) ปล่อยให้ Trend ทำงาน"
        ])
        strategy = "**กลยุทธ์: Let Profit Run & Trailing Stop**"
        if rsi > 75: 
            action_1 = "⚠️ **เตือนภัย:** RSI สูงจัด (Overbought) ห้ามไล่ราคาเด็ดขาด!"
            action_2 = "สายซิ่ง: แบ่งขายล็อกกำไรเข้ากระเป๋าบ้าง (Lock Profit)"
        else:
            action_1 = "🟢 **คนมีของ:** ถือต่อ (Hold) ใช้เส้น EMA 20 เป็นจุดหนี"
            action_2 = f"🟡 **คนไม่มีของ:** รอจังหวะย่อแตะ EMA 20 ({ema20:.2f}) แล้วค่อยเข้า"
        report["action"] = {"strategy": strategy, "steps": [action_1, action_2]}

    # --- Scenario 2: ขาขึ้นพักตัว ---
    elif price > ema200 and price < ema20:
        report["status_color"] = "orange"
        report["banner_title"] = pick_one([
            "Correction: พักตัวเพื่อไปต่อ?",
            "Healthy Pullback: ย่อตัวสร้างฐาน"
        ])
        report["technical"] = {
            "structure": "ราคาหลุด EMA 20 ลงมาหาแนวรับ EMA 50",
            "status": "แรงขายทำกำไรกดดัน แต่เทรนด์ใหญ่ยังเป็นขาขึ้น"
        }
        report["context"] = pick_one([
            "ตลาดกำลังวัดใจว่าจะรับอยู่ไหม แถวๆ EMA 50 คือจุดวัดใจสำคัญ",
            "เป็นการย่อเคลียร์คนเล่นสั้น (Shake out) ถ้าพื้นฐานดี นี่คือโอกาส"
        ])
        strategy = "**กลยุทธ์: Wait & See (รอสัญญาณกลับตัว)**"
        action_1 = f"🎯 **จุด Sniper:** รอรับที่ EMA 50 ({ema50:.2f}) ถ้ามีแท่งเทียนกลับตัว"
        if price < ema50: action_2 = f"ระวัง! ราคาหลุด EMA 50 แนวรับถัดไปคือ EMA 200 ({ema200:.2f})"
        else: action_2 = f"🛡️ **จุดหนี:** ถ้าหลุด {ema50:.2f} ให้ถอยออกมาดูสถานการณ์ก่อน"
        report["action"] = {"strategy": strategy, "steps": [action_1, action_2]}

    # --- Scenario 3: ขาลง ---
    elif price < ema200 and price < ema50:
        if price < ema20:
            if rsi < 25:
                report["status_color"] = "orange" 
                report["banner_title"] = "Oversold Bounce: ลุ้นเด้งสั้น (ความเสี่ยงสูง)"
                report["technical"] = {"structure": "ราคาลงลึกมากจน RSI ต่ำ (<25)", "status": "Panic Sell รุนแรง อาจเกิด Technical Rebound"}
                report["context"] = "ลงแรงเกินพื้นฐาน หรือเกิดความกลัวสุดขีด มักจะมีแรงซื้อเก็งกำไรสวนเข้ามา"
                strategy = "**กลยุทธ์: Contrarian (ชาวสวน)**"
                action_1 = "🧨 **สายซิ่งเท่านั้น:** เข้าเร็ว-ออกเร็ว (Hit & Run)"
                action_2 = "ถ้าเด้งขึ้นไปชน EMA 20 ให้ขายทิ้งทันที"
            else:
                report["status_color"] = "red"
                report["banner_title"] = pick_one(["Bearish Market: หมีตะปบ", "Downtrend: ขาลงสมบูรณ์แบบ"])
                report["technical"] = {"structure": "ขาลงเต็มตัว (Price < All EMAs)", "status": "หมีครองตลาด! แรงขายชนะขาดลอย"}
                report["context"] = pick_one(["ฝนตกหนักอย่าเพิ่งออกไปตากฝน รอฟ้าเปิดก่อน", "การเด้งขึ้นคือการเด้งเพื่อลงต่อ (Rebound)"])
                strategy = "**กลยุทธ์: Defensive / Cash is King**"
                action_1 = "ห้ามรับมีด! (Don't catch a falling knife)"
                action_2 = "ใครมีของพิจารณาตัดขาดทุน หรืออาศัยจังหวะเด้งเพื่อขายออก"
        else:
            report["status_color"] = "orange"
            report["banner_title"] = "พยายามฟื้นตัว (ระดับ: รีบาวด์ในขาลง)"
            report["technical"] = {"structure": "เด้งรีบาวด์สั้นๆ ในเทรนด์ขาลงใหญ่", "status": "แรงซื้อเก็งกำไรระยะสั้นเข้ามา"}
            report["context"] = "ภาพรวมวันนี้: เป็นเพียงการเด้งขึ้นทางเทคนิค (Dead Cat Bounce) ภาพใหญ่ยังมองลง"
            strategy = "**กลยุทธ์: Play for Rebound (เล่นเด้งสั้น)**"
            action_1 = "เล่นสั้นเท่านั้น (Scalping) ห้ามถือยาว"
            action_2 = f"แนวต้านสำคัญ **EMA 50 ({ema50:.2f})** ถ้าไม่ผ่านให้ขายทิ้งทันที"
        report["action"] = {"strategy": strategy, "steps": [action_1, action_2]}

    # --- Scenario 4: ไซด์เวย์ ---
    else:
        report["status_color"] = "yellow"
        report["banner_title"] = pick_one(["Sideway: รอเลือกทาง", "Recovery: พยายามสร้างฐาน"])
        report["technical"] = {"structure": "ราคาพันกันนัวเนียอยู่กับเส้น EMA", "status": "แรงซื้อแรงขายพอๆ กัน รอความชัดเจน"}
        report["context"] = "ตลาดขาดปัจจัยชี้นำที่ชัดเจน เล่นยากเพราะราคาเหวี่ยงขึ้นลงในกรอบแคบๆ"
        strategy = "**กลยุทธ์: Wait for Confirmation**"
        action_1 = f"ผู้เล่นระยะกลาง: ถือเงินสดรอให้ราคายืนเหนือ EMA 200"
        action_2 = f"ผู้เล่นระยะสั้น: ซื้อใกล้รับ {min(ema20,ema50):.2f} / ขายใกล้ต้าน {max(ema20,ema50,ema200):.2f}"
        report["action"] = {"strategy": strategy, "steps": [action_1, action_2]}

    return report

# --- 7. ส่วนแสดงผล ---
if submit_btn:
    st.markdown("""
        <style>
        div[data-testid="stAppViewContainer"] { overflow: auto !important; }
        </style>
    """, unsafe_allow_html=True)
    
    st.divider()

    result_placeholder = st.empty()
    
    while True:
        with result_placeholder.container():
            with st.spinner(f"AI กำลังประมวลผล {symbol_input} ..."):
                df, info = get_data(symbol_input, tf_code)

            if df is not None and not df.empty and len(df) > 200:
                # คำนวณ Indicator
                df['EMA20'] = ta.ema(df['Close'], length=20); df['EMA50'] = ta.ema(df['Close'], length=50)
                df['EMA200'] = ta.ema(df['Close'], length=200); df['RSI'] = ta.rsi(df['Close'], length=14)
                
                last = df.iloc[-1]; prev = df.iloc[-2]
                price = info['regularMarketPrice'] if info['regularMarketPrice'] else last['Close']
                rsi = last['RSI']
                ema20=last['EMA20']; ema50=last['EMA50']; ema200=last['EMA200']

                # AI Analysis (เรียกฟังก์ชันใหม่)
                ai_report = analyze_market_structure(price, ema20, ema50, ema200, rsi)

                # --- HEADER ---
                st.markdown(f"<h2 style='text-align: center; margin-top: -15px; margin-bottom: 25px;'>🏢 {info['longName']} ({symbol_input})</h2>", unsafe_allow_html=True)
                
                # --- Row 1: ราคา & Banner ---
                c1, c2 = st.columns(2)
                with c1:
                    reg_price = info.get('regularMarketPrice')
                    reg_chg = info.get('regularMarketChange')
                    
                    if reg_price and reg_chg:
                        prev_c = reg_price - reg_chg
                        if prev_c != 0: reg_pct = (reg_chg / prev_c) * 100
                        else: reg_pct = 0.0
                    else: reg_pct = 0.0
                    
                    color_text = "#16a34a" if reg_chg and reg_chg > 0 else "#dc2626"
                    bg_color = "#e8f5ec" if reg_chg and reg_chg > 0 else "#fee2e2"
                    
                    st.markdown(f"""
                    <div style="margin-bottom:5px; display: flex; align-items: center; gap: 15px; flex-wrap: wrap;">
                      <div style="font-size:40px; font-weight:600; line-height: 1;">
                        {reg_price:,.2f} <span style="font-size: 20px; color: #6b7280; font-weight: 400;">USD</span>
                      </div>
                      <div style="display:inline-flex; align-items:center; gap:6px; background:{bg_color}; color:{color_text}; padding:4px 12px; border-radius:999px; font-size:18px; font-weight:500;">
                        {arrow_html(reg_chg)} {reg_chg:+.2f} ({reg_pct:.2f}%)
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

                    pre_price = info.get('preMarketPrice'); pre_chg = info.get('preMarketChange')
                    post_price = info.get('postMarketPrice'); post_chg = info.get('postMarketChange')
                    pre_pct = 0.0; post_pct = 0.0
                    if pre_price and reg_price and reg_price != 0: pre_pct = ((pre_price - reg_price) / reg_price) * 100
                    if post_price and reg_price and reg_price != 0: post_pct = ((post_price - reg_price) / reg_price) * 100
                    
                    extra_market_html = ""
                    if pre_price and pre_chg is not None:
                        extra_market_html += f"<div>☀️ ก่อนเปิด: <b>{pre_price:.2f}</b> <span style='color:{'#16a34a' if pre_chg>0 else '#dc2626'}'>{arrow_html(pre_chg)} {pre_chg:+.2f} ({pre_pct:+.2f}%)</span></div>"
                    if post_price and post_chg is not None:
                        extra_market_html += f"<div>🌙 หลังปิด: <b>{post_price:.2f}</b> <span style='color:{'#16a34a' if post_chg>0 else '#dc2626'}'>{arrow_html(post_chg)} {post_chg:+.2f} ({post_pct:+.2f}%)</span></div>"

                    if extra_market_html:
                        st.markdown(f"<div style='font-size:14px; color:#6b7280; display:flex; gap: 15px; flex-wrap: wrap; margin-top: 5px;'>{extra_market_html}</div>", unsafe_allow_html=True)

                if tf_code == "1h": tf_label = "TF Hour (รายชั่วโมง)"
                elif tf_code == "1wk": tf_label = "TF Week (รายสัปดาห์)"
                else: tf_label = "TF Day (รายวัน)"

                st_color = ai_report["status_color"]
                main_status = ai_report["banner_title"]

                if st_color == "green": c2.success(f"📈 {main_status}\n\n**{tf_label}**")
                elif st_color == "red": c2.error(f"📉 {main_status}\n\n**{tf_label}**")
                else: c2.warning(f"⚖️ {main_status}\n\n**{tf_label}**")

                # --- Row 2: P/E & RSI ---
                c3, c4 = st.columns(2)
                with c3:
                    pe_val = info['trailingPE']
                    pe_str = f"{pe_val:.2f}" if isinstance(pe_val, (int, float)) else "N/A"
                    st.metric("📊 P/E Ratio", pe_str)
                    st.caption(get_pe_interpretation(pe_val))
                with c4:
                    if rsi >= 70: rsi_label = "Overbought"
                    elif rsi <= 30: rsi_label = "Oversold"
                    else: rsi_label = "Neutral"
                    st.metric("⚡ RSI (14)", f"{rsi:.2f}", rsi_label, delta_color="inverse" if rsi>70 else "normal")
                    st.caption(get_rsi_interpretation(rsi))

                st.write("") 

                # --- Row 3: EMA (Left) & AI Report (Right) ---
                col_ema, col_ai = st.columns([1.5, 1.5])
                
                with col_ema:
                    st.subheader("📉 ค่าเส้นค่าเฉลี่ย (EMA)")
                    st.markdown(f"""
                        <div style='font-size: 1.1rem; line-height: 1.8;'>
                            <b>EMA 20</b> = {ema20:.2f}<br>
                            <b>EMA 50</b> = {ema50:.2f}<br>
                            <b>EMA 200</b> = {ema200:.2f}
                        </div>
                    """, unsafe_allow_html=True)
                    
                with col_ai:
                    st.subheader("🤖 AI INTELLIGENT REPORT")
                    with st.chat_message("assistant"):
                        st.markdown(f"### 🧠 1. บทวิเคราะห์เทคนิค:")
                        st.markdown(f"- {ai_report['technical']['structure']}\n- {ai_report['technical']['status']}")
                        st.markdown("---")
                        st.markdown(f"### 📚 2. คำอธิบายสถานะ:")
                        st.markdown(f"- {ai_report['context']}")
                        st.markdown("---")
                        st.markdown(f"### ✅ 3. สรุปสิ่งที่ควรทำ:")
                        st.markdown(f"🟡 {ai_report['action']['strategy']}")
                        for idx, step in enumerate(ai_report['action']['steps'], 1):
                            st.markdown(f"{idx}. {step}")

                # --- Row 4: Support & Resistance (ย้ายกลับมาด้านล่างสุดเต็มจอ) ---
                st.subheader("🚧 แผนการเทรด (Support & Resistance)")
                supports, resistances = [], []
                res_val = df['High'].tail(60).max(); resistances.append((res_val, "High เดิม (60 แท่ง)"))
                if price < ema200: resistances.append((ema200, "เส้น EMA 200"))
                if price > ema200: supports.extend([(ema20, "EMA 20 (รับซิ่ง)"), (ema50, "EMA 50 (รับหลัก)"), (ema200, "EMA 200 (รับสุดท้าย)")])
                else: supports.extend([(df['Low'].tail(60).min(), "Low เดิม"), (df['Low'].tail(200).min(), "Low รอบใหญ่")])

                c_sup, c_res = st.columns(2)
                with c_sup:
                    st.markdown("#### 🟢 แนวรับ (จุดรอซื้อ)")
                    for v, d in supports: 
                        if v < price: st.write(f"- **{v:.2f}** : {d}")
                with c_res:
                    st.markdown("#### 🔴 แนวต้าน (จุดรอขาย)")
                    for v, d in resistances:
                        if v > price: st.write(f"- **{v:.2f}** : {d}")

            elif df is not None: st.warning("⚠️ หุ้นใหม่ ข้อมูลไม่พอคำนวณ EMA200"); st.line_chart(df['Close'])
            else: st.error(f"❌ ไม่พบข้อมูลหุ้น: {symbol_input}")
        
        # [Logic Loop]
        if not realtime_mode:
            break
        
        time.sleep(10)
