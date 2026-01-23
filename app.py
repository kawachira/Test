import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Stock Master", page_icon="💎", layout="wide")

# --- 2. CSS ปรับแต่ง ---
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

# --- 3. ส่วนหัวข้อ ---
st.markdown("<h1>💎 Ai<br><span style='font-size: 1.5rem; opacity: 0.7;'>ระบบวิเคราะห์หุ้นอัจฉริยะ</span></h1>", unsafe_allow_html=True)
st.write("")

# --- Form ค้นหา ---
col_space1, col_form, col_space2 = st.columns([1, 2, 1])
with col_form:
    with st.form(key='search_form'):
        st.markdown("### 🔍 ค้นหาหุ้นที่ต้องการ")
        c1, c2 = st.columns([3, 1])
        with c1:
            symbol_input = st.text_input("ชื่อหุ้น (เช่น AMZN,EOSE,RKLB, TSLA):", value="EOSE").upper().strip()
        with c2:
            timeframe = st.selectbox("Timeframe:", ["1h (รายชั่วโมง)", "1d (รายวัน)", "1wk (รายสัปดาห์)"], index=1)
            if "1wk" in timeframe: tf_code = "1wk"
            elif "1h" in timeframe: tf_code = "1h"
            else: tf_code = "1d"
            
        submit_btn = st.form_submit_button("🚀 วิเคราะห์ทันที / รีเฟรชข้อมูล")

# --- 4. Helper Functions ---
def arrow_html(change):
    if change is None: return ""
    return "<span style='color:#16a34a;font-weight:600'>▲</span>" if change > 0 else "<span style='color:#dc2626;font-weight:600'>▼</span>"

def get_rsi_interpretation(rsi):
    if rsi >= 80: return "🔴 **Extreme Overbought (80+):** แรงซื้อบ้าคลั่ง ระวังการเทขายรุนแรง"
    elif rsi >= 70: return "🟠 **Overbought (70-80):** ราคาเริ่มตึงตัว อาจมีการเทขายพักฐานเร็วๆ นี้"
    elif rsi >= 55: return "🟢 **Bullish Zone (55-70):** โมเมนตัมกระทิงครองตลาด ราคาแข็งแกร่ง"
    elif rsi >= 45: return "⚪ **Sideway/Neutral (45-55):** แรงซื้อขายก้ำกึ่ง รอเลือกทางที่ชัดเจน"
    elif rsi >= 30: return "🟠 **Bearish Zone (30-45):** โมเมนตัมหมีครองตลาด ระวังราคาไหลลงต่อ"
    elif rsi > 20: return "🟢 **Oversold (20-30):** ขายมากเกินไป เริ่มเข้าเขต 'ของถูก' ลุ้นเด้งรีบาวด์"
    else: return "🟢 **Extreme Oversold (<20):** ลงลึกมาก Panic Sell จบแล้ว"

def get_pe_interpretation(pe):
    if isinstance(pe, str) and pe == 'N/A': return "⚪ N/A (บริษัทอาจขาดทุน/ไม่มีกำไร)"
    if pe < 0: return "🔴 ขาดทุน (Earnings ติดลบ)"
    if pe < 15: return "🟢 หุ้นถูก (Value)"
    if pe < 30: return "🟡 ราคาเหมาะสม"
    return "🟠 หุ้นแพง (Growth)"

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

# --- 6. AI Logic ---
def analyze_market_structure(price, ema20, ema50, ema200, rsi):
    report = {
        "technical": {},
        "context": "",
        "action": {},
        "status_color": "",
        "banner_title": ""
    }

    # --- Scenario 1: ขาขึ้นแข็งแกร่ง (Super Strong Uptrend) ---
    if price > ema200 and price > ema50 and price > ema20:
        report["status_color"] = "green"
        report["banner_title"] = "หุ้นแข็งแกร่งมาก (ระดับ: ขาขึ้นต้นเทรนด์/กระทิงดุ)"
        report["technical"] = {
            "structure": "หุ้นแข็งแกร่งมาก (Strong Uptrend) วิ่งเกาะเส้น EMA 20",
            "status": "กระทิงดุ! แรงซื้อยังคงสนับสนุนต่อเนื่อง โมเมนตัมเป็นบวกเต็มที่"
        }
        report["context"] = "ภาพรวมวันนี้: หุ้นเนื้อหอมมาก ตลาดยังมีความเชื่อมั่นสูง คนที่มีของก็นั่งยิ้มปล่อยกำไรไหลไป ส่วนคนไม่มีของต้องใจเย็นรอจังหวะย่อ ห้ามไล่ราคาดอยๆ"
        
        # Action Plan
        strategy = "**กลยุทธ์: Let Profit Run**"
        action_1 = "ถือต่อ (Hold) อย่าเพิ่งรีบขายหมู จนกว่ากราฟจะเสียทรง"
        action_2 = f"ใช้เส้น **EMA 20 ({ema20:.2f})** เป็นจุด Trailing Stop เลื่อนตามราคาไปเรื่อยๆ"
        
        if rsi > 75: 
            report["context"] += " (แต่ระวัง RSI สูงเกินไป อาจมีการพักตัวระยะสั้น)"
            action_1 = "ถือต่อ แต่เริ่มแบ่งขายทำกำไรบางส่วน (Take Profit) เมื่อราคาพุ่งแรงผิดปกติ"

        report["action"] = {"strategy": strategy, "steps": [action_1, action_2]}

    # --- Scenario 2: ขาขึ้นพักตัว (Correction in Uptrend) ---
    elif price > ema200 and price < ema20:
        report["status_color"] = "orange"
        report["banner_title"] = "ย่อตัวในขาขึ้น (ระดับ: พักฐานระยะสั้น)"
        report["technical"] = {
            "structure": "ย่อตัวในขาขึ้น (Correction) ราคาหลุด EMA 20 ลงมาทดสอบแนวรับ",
            "status": "พักฐานชั่วคราว แรงขายทำกำไรเริ่มออกมา แต่เทรนด์หลักยังไม่เสีย"
        }
        report["context"] = "ภาพรวมวันนี้: ราคาเริ่มตึงและมีการย่อตัวลงมา เป็นเรื่องปกติของหุ้นขาขึ้นเพื่อลดความร้อนแรง เป็นช่วงวัดใจว่าจะรับอยู่หรือไม่"
        
        # Action Plan
        strategy = "**กลยุทธ์: Buy on Dip (รอซื้อเมื่อย่อ)**"
        action_1 = "Wait & See: รอดูว่ายืนเหนือเส้น EMA 50 ได้หรือไม่"
        action_2 = f"ตั้งจุดรอรับบริเวณ **EMA 50 ({ema50:.2f})** ถ้ารับอยู่คือโอกาสทองในการสะสมเพิ่ม"
        
        if price < ema50: 
             action_2 = f"ระวัง! ราคาหลุด EMA 50 ลงมา แนวรับถัดไปคือ EMA 200 ({ema200:.2f}) ชะลอการซื้อ"

        report["action"] = {"strategy": strategy, "steps": [action_1, action_2]}

    # --- Scenario 3: ขาลง (Downtrend) ---
    elif price < ema200 and price < ema50:
        if price < ema20:
            report["status_color"] = "red"
            report["banner_title"] = "ขาลงเต็มตัว (ระดับ: ขาลงรุนแรง/หมีครองตลาด)"
            report["technical"] = {
                "structure": "ขาลงเต็มตัว (Downtrend) ราคายังทำ Low ใหม่ต่อเนื่อง",
                "status": "หมีครองตลาด! แรงขายชนะขาดลอย แนวต้านทำงานได้ดีกว่าแนวรับ"
            }
            report["context"] = "ภาพรวมวันนี้: บรรยากาศอึมครึม แรงขายกดดันตลอดทาง การเด้งขึ้นเป็นเพียงการเด้งเพื่อลงต่อ (Rebound) ยังไม่เห็นสัญญาณกลับตัว"
            
            # Action Plan
            strategy = "**กลยุทธ์: Defensive / Cash is King**"
            action_1 = "ห้ามรับมีด! (Don't catch a falling knife) รอให้ราคาหยุดลงและสร้างฐานก่อน"
            action_2 = f"ใครมีของพิจารณาตัดขาดทุน (Stop Loss) หรืออาศัยจังหวะเด้งเพื่อขายออก ลดความเสี่ยง"
        else:
             # กรณีพิเศษ: ราคา < 200 แต่ > 20 (เริ่มเด้ง)
            report["status_color"] = "orange"
            report["banner_title"] = "พยายามฟื้นตัว (ระดับ: รีบาวด์ในขาลง)"
            report["technical"] = {
                "structure": "เด้งรีบาวด์สั้นๆ (Technical Rebound) ในเทรนด์ขาลงใหญ่",
                "status": "แรงซื้อเก็งกำไรระยะสั้นเข้ามา แต่ยังติดแนวต้านสำคัญ"
            }
            report["context"] = "ภาพรวมวันนี้: เป็นเพียงการเด้งขึ้นทางเทคนิค (Dead Cat Bounce) ภาพใหญ่ยังมองลง ระวังแรงเทขายที่แนวต้าน"
            strategy = "**กลยุทธ์: Play for Rebound (เล่นเด้งสั้น)**"
            action_1 = "เล่นสั้นเท่านั้น (Scalping) ห้ามถือยาว"
            action_2 = f"แนวต้านสำคัญ **EMA 50 ({ema50:.2f})** ถ้าไม่ผ่านให้ขายทิ้งทันที"
        
        if rsi < 25: 
            strategy = "**กลยุทธ์: Speculative Buy (เก็งกำไรสั้นๆ)**"
            report["context"] += " (แต่ RSI ต่ำมาก อาจมีเด้งสั้นๆ เร็วๆ นี้)"
            action_1 = "เสี่ยงซื้อเล่นเด้งสั้นๆ (Oversold Bounce) เข้าไวออกไว"
            action_2 = "วางจุด Cut Loss ให้ชิดที่สุด ถ้าหลุด Low เดิมต้องทิ้งทันที"

        report["action"] = {"strategy": strategy, "steps": [action_1, action_2]}

    # --- Scenario 4: ช่วงฟื้นตัว / ไซด์เวย์ (Recovery / Sideway) ---
    else:
        report["status_color"] = "yellow"
        report["banner_title"] = "เลือกทาง (ระดับ: ไซด์เวย์/รอความชัดเจน)"
        report["technical"] = {
            "structure": "พยายามสร้างฐาน / ฟื้นตัว (Recovery)",
            "status": "สู้กันดุเดือด! แรงซื้อและแรงขายก้ำกึ่ง ราคากำลังเลือกทาง"
        }
        report["context"] = "ภาพรวมวันนี้: ตลาดมีความผันผวน ราคาพยายามจะกลับมายืนเหนือเส้นค่าเฉลี่ย แต่ยังไม่คอนเฟิร์มร้อยเปอร์เซ็นต์"
        
        # Action Plan
        strategy = "**กลยุทธ์: Wait for Confirmation**"
        action_1 = "ผู้เล่นระยะกลาง: ถือเงินสดรอให้ราคายืนเหนือ EMA 200 ได้อย่างมั่นคงก่อน"
        action_2 = f"ผู้เล่นระยะสั้น: เล่นรอบในกรอบ แนวต้าน {ema200:.2f} แนวรับ {ema20:.2f}"
        
        report["action"] = {"strategy": strategy, "steps": [action_1, action_2]}

    return report

# --- 7. Display ---
if submit_btn:
    st.divider()
    with st.spinner(f"AI กำลังประมวลผล {symbol_input} ..."):
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
                    extra_html += f"<div>☀️ ก่อนเปิด: <b>{pre_p:.2f}</b> <span style='color:{'#16a34a' if pre_c>0 else '#dc2626'}'>{arrow_html(pre_c)} {pre_c:+.2f} ({pre_pc:+.2f}%)</span></div>"
                if post_p and post_c is not None:
                    extra_html += f"<div>🌙 หลังปิด: <b>{post_p:.2f}</b> <span style='color:{'#16a34a' if post_c>0 else '#dc2626'}'>{arrow_html(post_c)} {post_c:+.2f} ({post_pc:+.2f}%)</span></div>"
                
                if extra_html:
                    st.markdown(f"<div style='font-size:14px; color:#6b7280; display:flex; gap: 15px; flex-wrap: wrap; margin-top: 5px;'>{extra_html}</div>", unsafe_allow_html=True)

            # AI Status Banner
            if tf_code == "1h": tf_label = "TF Hour (รายชั่วโมง)"
            elif tf_code == "1wk": tf_label = "TF Week (รายสัปดาห์)"
            else: tf_label = "TF Day (รายวัน)"
            
            st_color = ai_report["status_color"]
            main_status = ai_report["banner_title"]
            
            if st_color == "green": c2.success(f"📈 {main_status}\n\n**{tf_label}**")
            elif st_color == "red": c2.error(f"📉 {main_status}\n\n**{tf_label}**")
            else: c2.warning(f"⚖️ {main_status}\n\n**{tf_label}**")

            # Metrics
            c3, c4 = st.columns(2)
            with c3:
                st.metric("📊 P/E Ratio", f"{info['trailingPE']:.2f}" if isinstance(info['trailingPE'], (int,float)) else "N/A")
                st.caption(get_pe_interpretation(info['trailingPE']))
            with c4:
                rsi_lbl = "Overbought" if rsi>=70 else ("Oversold" if rsi<=30 else "Neutral")
                st.metric("⚡ RSI (14)", f"{rsi:.2f}", rsi_lbl, delta_color="inverse" if rsi>70 else "normal")
                st.caption(get_rsi_interpretation(rsi))

            st.write("") 

            # Analysis Section & AI Report
            c_ema, c_ai = st.columns([1.5, 2])
            with c_ema:
                st.subheader("📉 ค่าเส้นค่าเฉลี่ย (EMA)")
                st.markdown(f"""
                <div style='background-color: var(--secondary-background-color); padding: 15px; border-radius: 10px;'>
                    <div style='display:flex; justify-content:space-between; margin-bottom:5px;'><span>🔵 EMA 20 (ระยะสั้น)</span> <b>{ema20:.2f}</b></div>
                    <div style='display:flex; justify-content:space-between; margin-bottom:5px;'><span>🟠 EMA 50 (ระยะกลาง)</span> <b>{ema50:.2f}</b></div>
                    <div style='display:flex; justify-content:space-between;'><span>⚫ EMA 200 (ระยะยาว)</span> <b>{ema200:.2f}</b></div>
                </div>
                """, unsafe_allow_html=True)
                
                st.subheader("🚧 แผนการเทรด (S/R)")
                supports, resistances = [], []
                res_val = df['High'].tail(60).max(); resistances.append((res_val, "High เดิม (60 แท่ง)"))
                if price < ema200: resistances.append((ema200, "เส้น EMA 200"))
                if price > ema200: supports.extend([(ema20, "EMA 20"), (ema50, "EMA 50"), (ema200, "EMA 200")])
                else: supports.extend([(df['Low'].tail(60).min(), "Low เดิม"), (df['Low'].tail(200).min(), "Low รอบใหญ่")])
                
                st.markdown("#### 🟢 แนวรับ (จุดรอซื้อ)")
                for v, d in supports: 
                    if v < price: st.write(f"- **{v:.2f}** : {d}")
                st.markdown("#### 🔴 แนวต้าน (จุดรอขาย)")
                for v, d in resistances:
                    if v > price: st.write(f"- **{v:.2f}** : {d}")

            with c_ai:
                st.subheader("🤖 AI INTELLIGENT REPORT")
                with st.chat_message("assistant"):
                    st.markdown("### 🧠 1. บทวิเคราะห์ทางเทคนิค (AI Technical Analysis):")
                    st.markdown(f"- **โครงสร้าง:** {ai_report['technical']['structure']}")
                    st.markdown(f"- **สถานะ:** {ai_report['technical']['status']}")
                    
                    st.markdown("---")
                    
                    st.markdown("### 📚 2. คำอธิบายสถานะรายวัน (Daily Context):")
                    st.markdown(f"- {ai_report['context']}")
                    
                    st.markdown("---")
                    
                    st.markdown("### ✅ 3. สรุปสิ่งที่ควรทำ (Action Plan):")
                    st.markdown(f"🟡 {ai_report['action']['strategy']}")
                    for idx, step in enumerate(ai_report['action']['steps'], 1):
                        st.markdown(f"{idx}. {step}")

            # --- พื้นที่ว่างด้านล่าง 50px ---
            st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)

        elif df is not None: st.warning("⚠️ ข้อมูลไม่พอคำนวณ"); st.line_chart(df['Close'])
        else: st.error(f"❌ ไม่พบข้อมูล: {symbol_input}")
