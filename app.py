import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import time
from datetime import datetime, timedelta

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="AI Stock Master (Fixed)", page_icon="💎", layout="wide")

# --- Initialize Session State ---
if 'history_log' not in st.session_state: st.session_state['history_log'] = []

# --- 2. CSS ---
st.markdown("""<style>
    body { overflow-x: hidden; }
    .block-container { padding-top: 1rem !important; padding-bottom: 5rem !important; }
    h1 { text-align: center; font-size: 2.8rem !important; margin-bottom: 0px !important; margin-top: 5px !important; }
    div[data-testid="stForm"] { border: none; padding: 30px; border-radius: 20px; background-color: var(--secondary-background-color); box-shadow: 0 8px 24px rgba(0,0,0,0.12); max-width: 800px; margin: 0 auto; }
    div[data-testid="stFormSubmitButton"] button { width: 100%; border-radius: 12px; font-size: 1.2rem; font-weight: bold; padding: 15px 0; }
    .disclaimer-box { margin-top: 20px; margin-bottom: 20px; padding: 20px; background-color: #fff8e1; border: 2px solid #ffc107; border-radius: 12px; font-size: 1rem; color: #5d4037; text-align: center; font-weight: 500; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .xray-box { background-color: #f0f9ff; border: 1px solid #bae6fd; border-radius: 10px; padding: 15px; margin-bottom: 20px; }
    .xray-title { font-weight: bold; color: #0369a1; font-size: 1.1rem; margin-bottom: 10px; border-bottom: 1px solid #e0f2fe; padding-bottom: 5px; }
    .xray-item { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 0.95rem; }
    .fund-box { padding: 10px; border-radius: 8px; margin-bottom: 5px; font-size: 0.9rem; }
    .fund-good { background-color: #dcfce7; color: #14532d; border: 1px solid #22c55e; }
    .fund-mid { background-color: #fef9c3; color: #713f12; border: 1px solid #eab308; }
    .fund-bad { background-color: #fee2e2; color: #7f1d1d; border: 1px solid #ef4444; }
    </style>""", unsafe_allow_html=True)

# --- 3. Header & Form ---
st.markdown("<h1>💎 Ai<br><span style='font-size: 1.5rem; opacity: 0.7;'>Ultimate Sniper (No Crash Edition)🚀</span></h1>", unsafe_allow_html=True)
col_space1, col_form, col_space2 = st.columns([1, 2, 1])
with col_form:
    with st.form(key='search_form'):
        st.markdown("### 🔍 ค้นหาหุ้น")
        c1, c2 = st.columns([3, 1])
        with c1: symbol_input = st.text_input("ชื่อหุ้น (เช่น AMZN,EOSE,RKLB,TSLA)🪐", value="").upper().strip()
        with c2:
            timeframe = st.selectbox("Timeframe:", ["1h (รายชั่วโมง)", "1d (รายวัน)", "1wk (รายสัปดาห์)"], index=1)
            if "1wk" in timeframe: tf_code = "1wk"; mtf_code = "1mo"
            elif "1h" in timeframe: tf_code = "1h"; mtf_code = "1d"
            else: tf_code = "1d"; mtf_code = "1wk"
        st.markdown("---"); submit_btn = st.form_submit_button("🚀 วิเคราะห์ทันที")

# --- 4. Helper Functions ---
def analyze_candlestick(open_price, high, low, close):
    body = abs(close - open_price); wick_upper = high - max(close, open_price); wick_lower = min(close, open_price) - low; total_range = high - low
    color = "🟢 เขียว (Buying)" if close >= open_price else "🔴 แดง (Selling)"
    if total_range == 0: return "Doji (N/A)", color, "N/A", False
    pattern_name = "Normal Candle (ปกติ)"; detail = "แรงซื้อขายสมดุล"; is_big = False
    if wick_lower > (body * 2) and wick_upper < body: pattern_name = "Hammer/Pinbar (ค้อน)"; detail = "มีการปฏิเสธราคาต่ำ (แรงซื้อสวน)"
    elif wick_upper > (body * 2) and wick_lower < body: pattern_name = "Shooting Star (ดาวตก)"; detail = "มีการปฏิเสธราคาสูง (แรงขายกด)"
    elif body > (total_range * 0.6): 
        is_big = True
        if close > open_price: pattern_name = "Big Bullish Candle (แท่งเขียวตัน)"; detail = "แรงซื้อคุมตลาดเบ็ดเสร็จ"
        else: pattern_name = "Big Bearish Candle (แท่งแดงตัน)"; detail = "แรงขายคุมตลาดเบ็ดเสร็จ (Panic Sell)"
    elif body < (total_range * 0.1): pattern_name = "Doji (โดจิ)"; detail = "ตลาดเกิดความลังเล (Indecision)"
    return pattern_name, color, detail, is_big

def arrow_html(change): return "" if change is None else ("<span style='color:#16a34a;font-weight:600'>▲</span>" if change > 0 else "<span style='color:#dc2626;font-weight:600'>▼</span>")
def format_volume(vol): return f"{vol/1_000_000_000:.2f}B" if vol >= 1e9 else (f"{vol/1_000_000:.2f}M" if vol >= 1e6 else (f"{vol/1_000:.2f}K" if vol >= 1e3 else f"{vol:,.0f}"))
def custom_metric_html(label, value, status_text, color_status, icon_svg):
    color_code = "#16a34a" if color_status == "green" else ("#dc2626" if color_status == "red" else "#a3a3a3")
    return f"""<div style="margin-bottom: 15px;"><div style="display: flex; align-items: baseline; gap: 10px; margin-bottom: 5px;"><div style="font-size: 18px; font-weight: 700; opacity: 0.9; color: var(--text-color); white-space: nowrap;">{label}</div><div style="font-size: 24px; font-weight: 700; color: var(--text-color);">{value}</div></div><div style="display: flex; align-items: start; gap: 6px; font-size: 15px; font-weight: 600; color: {color_code}; line-height: 1.4;"><div style="margin-top: 3px; min-width: 24px;">{icon_svg}</div><div>{status_text}</div></div></div>"""

def get_rsi_interpretation(rsi): return "N/A" if np.isnan(rsi) else ("Overbought (ระวังแรงขาย)" if rsi >= 70 else ("Bullish (กระทิง)" if rsi >= 55 else ("Sideway/Neutral" if rsi >= 45 else ("Bearish (หมี)" if rsi >= 30 else "Oversold (ระวังเด้งสวน)"))))
def get_adx_interpretation(adx, is_uptrend): return "N/A" if np.isnan(adx) else (f"Super Strong {'ขาขึ้น' if is_uptrend else 'ขาลง'}" if adx >= 50 else (f"Strong {'ขาขึ้น' if is_uptrend else 'ขาลง'}" if adx >= 25 else ("Developing Trend" if adx >= 20 else "Weak/Sideway")))

def analyze_fundamental(info):
    pe = info.get('trailingPE', None); eps_growth = info.get('earningsQuarterlyGrowth', None); score = 0
    if pe: score += 1 if pe < 20 else (-1 if pe > 50 else (-2 if pe < 0 else 0))
    if eps_growth: score += 2 if eps_growth * 100 > 15 else (1 if eps_growth > 0 else -2)
    if score >= 2: return {"status": "Strong Fundamental (งบดี)", "color_class": "fund-good", "summary": "✅ **งบแกร่ง:** กำไรโต/ราคาไม่แพง", "advice": "💎 **ถือยาวได้ (Investable)**", "pe": f"{pe:.2f}" if pe else "N/A", "growth": f"{eps_growth*100:.2f}%" if eps_growth else "N/A"}
    elif score <= -2: return {"status": "Weak Fundamental (งบเน่า)", "color_class": "fund-bad", "summary": "🔴 **งบแย่:** ขาดทุน/ถดถอย", "advice": "⚠️ **เก็งกำไรสั้นๆ (Speculative)**", "pe": f"{pe:.2f}" if pe else "N/A", "growth": f"{eps_growth*100:.2f}%" if eps_growth else "N/A"}
    else: return {"status": "Moderate (งบกลางๆ)", "color_class": "fund-mid", "summary": "⚖️ **งบกลางๆ:** พอไปวัดไปวาได้", "advice": "🔄 **เล่นตามรอบ (Swing Trade)**", "pe": f"{pe:.2f}" if pe else "N/A", "growth": f"{eps_growth*100:.2f}%" if eps_growth else "N/A"}

def find_demand_zones(df, atr_multiplier=0.25):
    zones = []; 
    if len(df) < 20: return zones
    lows = df['Low']; is_swing_low = (lows < lows.shift(1)) & (lows < lows.shift(2)) & (lows < lows.shift(-1)) & (lows < lows.shift(-2)); swing_indices = is_swing_low[is_swing_low].index; current_price = df['Close'].iloc[-1]
    for date in swing_indices:
        if date == df.index[-1] or date == df.index[-2]: continue
        swing_low = df.loc[date, 'Low']; atr = df.loc[date, 'ATR'] if 'ATR' in df.columns else swing_low * 0.02
        top = swing_low + (atr * atr_multiplier); bottom = swing_low
        if (current_price - top) / current_price > 0.20: continue
        future = df.loc[date:][1:]
        if future.empty or (future['Close'] < bottom).any(): continue
        zones.append({'bottom': bottom, 'top': top})
    return zones

def find_supply_zones(df, atr_multiplier=0.25):
    zones = []; 
    if len(df) < 20: return zones
    highs = df['High']; is_swing_high = (highs > highs.shift(1)) & (highs > highs.shift(2)) & (highs > highs.shift(-1)) & (highs > highs.shift(-2)); swing_indices = is_swing_high[is_swing_high].index; current_price = df['Close'].iloc[-1]
    for date in swing_indices:
        if date == df.index[-1] or date == df.index[-2]: continue
        swing_high = df.loc[date, 'High']; atr = df.loc[date, 'ATR'] if 'ATR' in df.columns else swing_high * 0.02
        top = swing_high; bottom = swing_high - (atr * atr_multiplier)
        if (bottom - current_price) / current_price > 0.20: continue
        future = df.loc[date:][1:]
        if future.empty or (future['Close'] > top).any(): continue
        zones.append({'bottom': bottom, 'top': top})
    return zones

@st.cache_data(ttl=60, show_spinner=False)
def get_data_hybrid(symbol, interval, mtf_interval):
    try:
        ticker = yf.Ticker(symbol)
        period_val = "10y" if interval == "1wk" else ("5y" if interval == "1d" else "730d")
        df = ticker.history(period=period_val, interval=interval)
        df_mtf = ticker.history(period="10y", interval=mtf_interval)
        if not df_mtf.empty: df_mtf['EMA200'] = ta.ema(df_mtf['Close'], length=200)
        try: info = ticker.info; cal = ticker.calendar; next_earn = cal.iloc[0, 0].strftime("%Y-%m-%d") if isinstance(cal, pd.DataFrame) else "N/A"
        except: info = {}; next_earn = "N/A"
        
        df_d = ticker.history(period="5d", interval="1d")
        if not df_d.empty: h_p = df_d['Close'].iloc[-1]; h_c = h_p - df_d['Close'].iloc[-2]; h_pct = h_c / df_d['Close'].iloc[-2]
        else: h_p = df['Close'].iloc[-1]; h_c = 0; h_pct = 0
        
        stock_info = {'longName': info.get('longName', symbol), 'marketState': info.get('marketState', 'REGULAR'), 'trailingPE': info.get('trailingPE'), 'earningsQuarterlyGrowth': info.get('earningsQuarterlyGrowth'), 'revenueGrowth': info.get('revenueGrowth'), 'regularMarketPrice': h_p, 'regularMarketChange': h_c, 'regularMarketChangePercent': h_pct, 'dayHigh': df_d['High'].iloc[-1] if not df_d.empty else 0, 'dayLow': df_d['Low'].iloc[-1] if not df_d.empty else 0, 'regularMarketOpen': df_d['Open'].iloc[-1] if not df_d.empty else 0, 'preMarketPrice': info.get('preMarketPrice'), 'preMarketChange': info.get('preMarketChange'), 'postMarketPrice': info.get('postMarketPrice'), 'postMarketChange': info.get('postMarketChange'), 'nextEarnings': next_earn}
        return df, stock_info, df_mtf
    except: return None, None, None

def analyze_volume(row, vol_ma):
    vol = row['Volume']; pct = (vol / vol_ma) * 100 if vol_ma > 0 else 0
    if pct >= 250: return f"💣 สูงมาก/ระเบิด ({pct:.0f}%)", "#7f1d1d"
    elif pct >= 120: return f"🔥 สูง/คึกคัก ({pct:.0f}%)", "#16a34a"
    elif pct <= 70: return f"🌵 ต่ำ/เบาบาง ({pct:.0f}%)", "#f59e0b"
    else: return f"☁️ ปกติ ({pct:.0f}%)", "gray"

# --- 7. AI Brain (Precision EMA + Dynamic Volume Tier) ---
def ai_hybrid_analysis(price, ema20, ema50, ema200, rsi, macd_val, macd_sig, adx, bb_up, bb_low, vol_status, mtf_trend, atr_val, mtf_ema200_val, open_price, high, low, close, obv_val, obv_avg, obv_slope, rolling_min, rolling_max, prev_open, prev_close, vol_now, vol_avg, demand_zones, is_squeeze):
    
    def sf(x): return float(x) if not np.isnan(float(x)) else np.nan
    price = sf(price); ema20 = sf(ema20); ema50 = sf(ema50); ema200 = sf(ema200); atr_val = sf(atr_val)
    
    candle_pattern, candle_color, candle_detail, is_big_candle = analyze_candlestick(open_price, high, low, close)
    is_reversal = "Hammer" in candle_pattern or "Doji" in candle_pattern
    vol_txt, vol_col = analyze_volume({'Volume': vol_now}, vol_avg)
    
    in_zone = False; active_zone = None
    if demand_zones:
        for z in demand_zones:
            if (low <= z['top'] * 1.005) and (high >= z['bottom']): in_zone = True; active_zone = z; break
            
    is_conf = False; conf_msg = ""
    if in_zone:
        if abs(active_zone['bottom'] - ema200) / price < 0.02: is_conf = True; conf_msg = "Zone + EMA 200"
        elif abs(active_zone['bottom'] - ema50) / price < 0.02: is_conf = True; conf_msg = "Zone + EMA 50"

    score = 0; bullish = []; bearish = []
    
    # 1. Structure (Precision Logic for Week)
    is_above_200 = False
    if not np.isnan(ema200):
        if price > ema200: score += 2; is_above_200 = True; bullish.append("ยืนเหนือ EMA 200 (เทรนด์หลักแกร่ง)")
        else: score -= 2; bearish.append("หลุด EMA 200 (เทรนด์หลักขาลง/อ่อนแอ)")
    if not np.isnan(ema50):
        if price > ema50: score += 1; bullish.append("ยืนเหนือ EMA 50 (ระยะกลางดี)")
        else: score -= 1; bearish.append("หลุด EMA 50 (เสียทรงระยะกลาง)")
    if not np.isnan(ema20):
        if price < ema20: score -= 2; bearish.append("หลุด EMA 20 (โมเมนตัมระยะสั้นหาย)") # Penalty -2

    # Bonus: Alignment
    if not np.isnan(ema20) and not np.isnan(ema50) and not np.isnan(ema200):
        if ema20 > ema50 and ema50 > ema200 and price > ema20: score += 1; bullish.append("🚀 Perfect Alignment (20>50>200)")

    # 2. Momentum
    if not np.isnan(macd_val) and not np.isnan(macd_sig):
        if macd_val > macd_sig: bullish.append("MACD ตัดขึ้น (Momentum บวก)")
        else: score -= 1; bearish.append("MACD ตัดลง (Momentum ลบ)")
    if rsi < 30: score += 1; bullish.append(f"RSI Oversold ({rsi:.0f})")
    elif rsi > 70: score -= 1; bearish.append(f"RSI Overbought ({rsi:.0f})")
    if mtf_trend == "Bullish": score += 1; bullish.append("TF ใหญ่เป็นขาขึ้น")
    else: bearish.append("TF ใหญ่เป็นขาลง")

    situation_insight = ""
    
    # 3. Smart OBV & Squeeze
    has_bull_div = False; has_bear_div = False; obv_insight = "Volume Flow ปกติ"
    if not np.isnan(obv_slope):
        if price < ema20 and obv_slope > 0: has_bull_div = True; score += 2; bullish.append("💎 Smart OBV: Bullish Divergence"); obv_insight = "Bullish Divergence (สะสม)"
        elif price > ema20 and obv_slope < 0: has_bear_div = True; score -= 2; bearish.append("⚠️ Smart OBV: Bearish Divergence"); obv_insight = "Bearish Divergence (ระวังทุบ)"
    
    if is_squeeze:
        situation_insight = "💣 **BB Squeeze:** กราฟบีบอัดรุนแรง รอระเบิด!"
        if has_bull_div: score += 1; situation_insight += " (ลุ้นระเบิดขึ้น 🚀)"
        elif has_bear_div: score -= 1; situation_insight += " (ระวังระเบิดลง 🩸)"

    # 4. SMC
    if in_zone:
        if "ต่ำ" in vol_txt or "ปกติ" in vol_txt:
            score += 3; bullish.append(f"🟢 Demand Zone + Volume ปลอดภัย")
            if not is_squeeze: situation_insight = "💎 **Sniper Mode:** เข้าโซนซื้อสวย รอเด้ง"
            if is_reversal: score += 1; bullish.append("🕯️ เจอแท่งเทียนกลับตัวในโซน")
        if is_conf: score += 2; bullish.append(f"⭐ Confluence: {conf_msg}")

    # 5. SAFETY NET (Smart Dynamic Penalty - 4 Tiers)
    if "ระเบิด" in vol_txt and close < open_price: # Tier 4: Crash > 250%
        score -= 10; bearish.append("💀 **Panic Sell:** Volume ระเบิด (หนีตาย!)"); situation_insight = "🩸 **Market Crash:** แรงขายถล่มทลาย ห้ามรับ!"
        bullish = [f for f in bullish if "EMA" not in f] # Wipe EMA score
    elif "คึกคัก" in vol_txt and is_big_candle and close < open_price: # Tier 1-3
        vol_pct = (vol_now / vol_avg) * 100
        # --- The Smart Penalty Logic ---
        if vol_pct >= 200: penalty = 5; sev = "รุนแรงมาก (Severe)" # Tier 3
        elif vol_pct >= 150: penalty = 4; sev = "รุนแรง (Heavy)"   # Tier 2
        else: penalty = 3; sev = "เริ่มผิดปกติ (Moderate)"         # Tier 1
        
        score -= penalty
        bearish.append(f"⚠️ **Selling Pressure:** แรงขาย{sev} (Vol {vol_pct:.0f}%) หัก {penalty} แต้ม")
        
        if score <= -3: situation_insight = "🩸 **Falling Knife:** เสียทรงขาลงชัดเจน (ห้ามรับ)"
        elif score <= -1: situation_insight = "🟠 **Correction:** ย่อตัวแรง (ระวังหลุดแนวรับ)"
        else: situation_insight = "⚠️ **Profit Taking:** แรงขายทำกำไรกดดัน"

    # 6. Status Generation
    if situation_insight == "":
        if score >= 5: situation_insight = "🚀 **Skyrocket:** เทรนด์ขาขึ้นแข็งแกร่ง (Strong Uptrend)"
        elif score >= 3: situation_insight = "🐂 **Uptrend:** เทรนด์ยังดี ย่อตัวน่าสนใจ"
        elif score >= 1: situation_insight = "⚖️ **Sideway:** รอเลือกทาง / พักตัว"
        elif score >= -2: situation_insight = "🐻 **Bearish:** แรงกดดันสูง / ติดแนวต้าน"
        else: situation_insight = "📉 **Downtrend:** ขาลงสมบูรณ์แบบ"

    # GATEKEEPER: EMA 200 Rule
    if not is_above_200 and score >= 5:
        score = 4; situation_insight = "🐂 **Rebound Play:** เล่นเด้งในขาลงใหญ่ (ระวัง EMA 200 กดทับ)"

    if score >= 5: status_col = "green"; title = "🚀 Sniper Entry: จุดซื้อคมกริบ"; st_text = "Aggressive Buy"; adv = f"เทรนด์แข็งแกร่งมาก! รันเทรนด์ได้ยาวๆ SL: {low-(atr_val*0.5):.2f}"
    elif score >= 3: status_col = "green"; title = "🐂 Buy on Dip: ย่อซื้อ"; st_text = "Accumulate"; adv = "ย่อตัวลงมาในจุดที่ได้เปรียบ ทยอยสะสมได้"
    elif score >= 1: status_col = "yellow"; title = "⚖️ Neutral: ไซด์เวย์"; st_text = "Wait & See"; adv = "ตลาดยังไม่เลือกทางชัดเจน รอสัญญาณยืนยัน"
    elif score <= -3: status_col = "red"; title = "🩸 Falling Knife: มีดหล่น"; st_text = "Wait / Cut Loss"; adv = "อันตราย! อย่าเพิ่งรับมีด รอให้ราคาหยุดลงและสร้างฐานใหม่"
    else: status_col = "orange"; title = "🐻 Bearish Pressure: แรงกดดันสูง"; st_text = "Avoid"; adv = "โมเมนตัมเป็นลบ/ติดแนวต้าน ยังไม่คุ้มเสี่ยง"

    sl_v = (active_zone['bottom'] - atr_val*0.5) if in_zone else (price - 2*atr_val)
    tp_v = price + 3*atr_val

    return {"status_color": status_col, "banner_title": title, "strategy": st_text, "context": situation_insight, "bullish_factors": bullish, "bearish_factors": bearish, "sl": sl_v, "tp": tp_v, "holder_advice": adv, "candle_pattern": candle_pattern, "candle_color": candle_color, "candle_detail": candle_detail, "vol_quality_msg": vol_txt, "vol_quality_color": vol_col, "in_demand_zone": in_zone, "confluence_msg": conf_msg, "is_squeeze": is_squeeze, "obv_insight": obv_insight}

# --- 8. Display ---
if submit_btn:
    st.divider()
    with st.spinner(f"AI กำลังประมวลผล {symbol_input}..."):
        df, info, df_mtf = get_data_hybrid(symbol_input, tf_code, mtf_code)
        try: ts = yf.Ticker(symbol_input); df_d = ts.history(period="2y", interval="1d"); df_w = ts.history(period="5y", interval="1wk")
        except: df_d = pd.DataFrame(); df_w = pd.DataFrame()

    if df is not None and not df.empty and len(df) > 20:
        df['EMA20'] = ta.ema(df['Close'], length=20); df['EMA50'] = ta.ema(df['Close'], length=50); df['EMA200'] = ta.ema(df['Close'], length=200)
        df['RSI'] = ta.rsi(df['Close'], length=14); df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        macd = ta.macd(df['Close']); df = pd.concat([df, macd], axis=1)
        bb = ta.bbands(df['Close'], length=20, std=2); 
        if bb is not None: df = pd.concat([df, bb], axis=1); bbu_col = bb.columns[2]; bbl_col = bb.columns[0]
        else: bbu_col = None; bbl_col = None
        df['ADX'] = ta.adx(df['High'], df['Low'], df['Close'], length=14)['ADX_14']
        df['Vol_SMA20'] = ta.sma(df['Volume'], length=20)
        df['OBV'] = ta.obv(df['Close'], df['Volume']); df['OBV_SMA20'] = ta.sma(df['OBV'], length=20); df['OBV_Slope'] = ta.slope(df['OBV'], length=5)
        df['BB_Width'] = (df[bbu_col] - df[bbl_col]) / df['EMA20'] * 100 if bbu_col else 0
        df['BB_Min'] = df['BB_Width'].rolling(20).min(); is_sq = df['BB_Width'].iloc[-1] <= (df['BB_Min'].iloc[-1] * 1.1)

        dz = find_demand_zones(df); sz = find_supply_zones(df)
        last = df.iloc[-1]; price = info.get('regularMarketPrice') or last['Close']
        vol_avg = last['Vol_SMA20'] if not np.isnan(last['Vol_SMA20']) else 1
        
        # Run AI
        rpt = ai_hybrid_analysis(price, last.get('EMA20'), last.get('EMA50'), last.get('EMA200'), last.get('RSI'), last.get('MACD_12_26_9'), last.get('MACDs_12_26_9'), last.get('ADX'), last.get(bbu_col), last.get(bbl_col), "", "", last.get('ATR'), 0, last['Open'], last['High'], last['Low'], last['Close'], last.get('OBV'), last.get('OBV_SMA20'), last.get('OBV_Slope'), 0, 0, 0, 0, last['Volume'], vol_avg, dz, is_sq)

        # Log
        st.session_state['history_log'].insert(0, { "เวลา": datetime.now().strftime("%H:%M"), "หุ้น": symbol_input, "ราคา": f"{price:.2f}", "Score": rpt['status_color'].upper(), "Action": rpt['strategy'] })
        st.session_state['history_log'] = st.session_state['history_log'][:10]

        # UI
        st.image(f"https://financialmodelingprep.com/image-stock/{symbol_input}.png", width=60)
        st.title(f"{info['longName']} ({symbol_input})")
        
        c1, c2 = st.columns(2)
        c1.metric("Price", f"{price:.2f}", f"{info.get('regularMarketChange'):.2f} ({info.get('regularMarketChangePercent'):.2f}%)")
        if "green" in rpt['status_color']: c2.success(f"📈 {rpt['banner_title']}")
        elif "red" in rpt['status_color']: c2.error(f"📉 {rpt['banner_title']}")
        else: c2.warning(f"⚖️ {rpt['banner_title']}")

        # Action Plan Box
        box_fn = st.success if "green" in rpt['status_color'] else (st.error if "red" in rpt['status_color'] else st.warning)
        box_fn(f"""### 📝 แผนการเทรด (Action Plan)\n\n**1. สถานการณ์:** {rpt['context']}\n\n**2. คำแนะนำ:** 👉 **{rpt['strategy']}** : {rpt['holder_advice']}\n\n**3. Setup:** 🛑 SL: {rpt['sl']:.2f} | ✅ TP: {rpt['tp']:.2f}""")

        # Details
        c3, c4 = st.columns([1.5, 2])
        with c3:
            st.markdown("#### 📉 Indicators")
            st.write(f"EMA 20: {last.get('EMA20',0):.2f} | EMA 50: {last.get('EMA50',0):.2f} | EMA 200: {last.get('EMA200',0):.2f}")
            st.write(f"RSI: {last.get('RSI',0):.2f} | Volume: {rpt['vol_quality_msg']}")
            st.markdown("#### 🟢 แนวรับ/ต้าน")
            
            # --- 🛡️ FIXED: Safety EMA Calculation for Week Data ---
            w_ema50 = np.nan; w_ema200 = np.nan
            if not df_stats_week.empty and len(df_stats_week) > 50:
                try: 
                    ema50_s = ta.ema(df_stats_week['Close'], length=50)
                    if ema50_s is not None: w_ema50 = ema50_s.iloc[-1]
                except: pass
            
            if not df_stats_week.empty and len(df_stats_week) > 200:
                try:
                    ema200_s = ta.ema(df_stats_week['Close'], length=200)
                    if ema200_s is not None: w_ema200 = ema200_s.iloc[-1]
                except: pass
            # ----------------------------------------------------

            # === Logic แนวรับเหมือนเดิม แต่ใช้ w_ema50/200 ที่คำนวณแบบ Safe แล้ว ===
            candidates_supp = []
            if not np.isnan(last.get('EMA20')) and last.get('EMA20') < price: candidates_supp.append({'val': last.get('EMA20'), 'label': f"EMA 20 ({tf_label} - ระยะสั้น)"})
            if not np.isnan(last.get('EMA50')) and last.get('EMA50') < price: candidates_supp.append({'val': last.get('EMA50'), 'label': f"EMA 50 ({tf_label})"})
            if not np.isnan(last.get('EMA200')) and last.get('EMA200') < price: candidates_supp.append({'val': last.get('EMA200'), 'label': f"EMA 200 ({tf_label})"})
            
            # Add Day Support
            if not df_stats_day.empty and len(df_stats_day) > 50:
                d_ema50 = ta.ema(df_stats_day['Close'], length=50).iloc[-1]
                if d_ema50 < price: candidates_supp.append({'val': d_ema50, 'label': "EMA 50 (TF Day)"})
            
            # Add Week Support (Safe check)
            if not np.isnan(w_ema50) and w_ema50 < price: candidates_supp.append({'val': w_ema50, 'label': "EMA 50 (TF Week)"})
            if not np.isnan(w_ema200) and w_ema200 < price: candidates_supp.append({'val': w_ema200, 'label': "🛡️ EMA 200 (TF Week - กองทุน)"})

            if dz:
                for z in dz: candidates_supp.append({'val': z['bottom'], 'label': f"Demand Zone [{z['bottom']:.2f}-{z['top']:.2f}]"})
            
            candidates_supp.sort(key=lambda x: x['val'], reverse=True)
            
            # Filter close levels
            final_supp = []
            for i in candidates_supp:
                if not final_supp: final_supp.append(i)
                elif abs(final_supp[-1]['val'] - i['val']) > min_dist: final_supp.append(i)
            
            if final_supp:
                for s in final_supp[:3]: st.write(f"- **{s['val']:.2f}:** {s['label']}")
            else: st.error("🚨 หลุดทุกแนวรับ (All Time Low?)")

            st.markdown("#### 🔴 แนวต้าน")
            # Reuse logic for resistance if needed, or simple list
            if sz: st.write(f"- Supply Zone: {sz[-1]['bottom']:.2f} - {sz[-1]['top']:.2f}")
            else: st.write("- Blue Sky (ไม่มีต้านใกล้ๆ)")
            
        with c4:
            st.markdown("#### 🔍 AI Analysis")
            st.markdown(f"**ทรงกราฟ:** {rpt['candle_pattern']} ({rpt['candle_color']})")
            st.markdown(f"**แรงกดดัน (BB):** {'⚠️ Squeeze' if is_sq else 'Normal'}")
            st.markdown(f"**Smart OBV:** {rpt['obv_insight']}")
            if rpt['bullish_factors']: 
                st.markdown("**✅ ปัจจัยบวก:**")
                for f in rpt['bullish_factors']: st.caption(f"- {f}")
            if rpt['bearish_factors']: 
                st.markdown("**⚠️ ความเสี่ยง:**")
                for f in rpt['bearish_factors']: st.caption(f"- {f}")

        st.markdown("---")
        st.subheader("📜 History Log")
        st.dataframe(pd.DataFrame(st.session_state['history_log']), hide_index=True, use_container_width=True)

    else: st.error("ไม่พบข้อมูลหุ้น")
