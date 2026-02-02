# --- 8. Display Execution ---

if submit_btn:
    st.divider()
    st.markdown("""<style>body { overflow: auto !important; }</style>""", unsafe_allow_html=True)
    with st.spinner(f"AI กำลังสแกนหา Demand/Supply Zone และประมวลผล {symbol_input}..."):
        # 1. Main Data
        df, info, df_mtf = get_data_hybrid(symbol_input, tf_code, mtf_code)
        
        # 2. Safety Net Data (Week/Day)
        try:
            ticker_stats = yf.Ticker(symbol_input)
            df_stats_day = ticker_stats.history(period="2y", interval="1d")
            df_stats_week = ticker_stats.history(period="5y", interval="1wk")
        except:
            df_stats_day = pd.DataFrame(); df_stats_week = pd.DataFrame()

    if df is not None and not df.empty and len(df) > 20: 
        # Indicators
        df['EMA20'] = ta.ema(df['Close'], length=20)
        df['EMA50'] = ta.ema(df['Close'], length=50)
        df['EMA200'] = ta.ema(df['Close'], length=200)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        macd = ta.macd(df['Close']); df = pd.concat([df, macd], axis=1)
        bbands = ta.bbands(df['Close'], length=20, std=2)
        if bbands is not None and len(bbands.columns) >= 3:
            bbl_col_name, bbu_col_name = bbands.columns[0], bbands.columns[2]
            df = pd.concat([df, bbands], axis=1)
        else: bbl_col_name, bbu_col_name = None, None
        adx = ta.adx(df['High'], df['Low'], df['Close'], length=14); df = pd.concat([df, adx], axis=1)
        df['Vol_SMA20'] = ta.sma(df['Volume'], length=20)
        
        # --- 🌟 ADDED: OBV & Rolling Logic ---
        df['OBV'] = ta.obv(df['Close'], df['Volume'])
        df['OBV_SMA20'] = ta.sma(df['OBV'], length=20)
        df['OBV_Slope'] = ta.slope(df['OBV'], length=5) 
        df['Rolling_Min'] = df['Low'].rolling(window=20).min()
        df['Rolling_Max'] = df['High'].rolling(window=20).max()
        
        # --- 🌟 ADDED: Relative BB Squeeze Logic ---
        # คำนวณ Bandwidth
        if bbu_col_name and bbl_col_name and 'EMA20' in df.columns:
            df['BB_Width'] = (df[bbu_col_name] - df[bbl_col_name]) / df['EMA20'] * 100
            # หาค่า Bandwidth ที่แคบที่สุดในรอบ 20 วัน
            df['BB_Width_Min20'] = df['BB_Width'].rolling(window=20).min()
            # เช็คว่าปัจจุบันแคบใกล้เคียงจุดต่ำสุดไหม (Relative Squeeze)
            is_squeeze = df['BB_Width'].iloc[-1] <= (df['BB_Width_Min20'].iloc[-1] * 1.1) # ยอมให้กว้างกว่าจุดต่ำสุดได้ 10%
        else:
            is_squeeze = False

        # Find Zones
        demand_zones = find_demand_zones(df, atr_multiplier=0.25)
        supply_zones = find_supply_zones(df, atr_multiplier=0.25) # NEW for Resistance
        
        last = df.iloc[-1]
        price = info.get('regularMarketPrice') if info.get('regularMarketPrice') else last['Close']
        rsi = last['RSI'] if 'RSI' in last else np.nan
        atr = last['ATR'] if 'ATR' in last else np.nan
        ema20 = last['EMA20'] if 'EMA20' in last else np.nan
        ema50 = last['EMA50'] if 'EMA50' in last else np.nan
        ema200 = last['EMA200'] if 'EMA200' in last else np.nan
        vol_now = last['Volume']
        open_p = last['Open']; high_p = last['High']; low_p = last['Low']; close_p = last['Close']
        try: macd_val, macd_signal = last['MACD_12_26_9'], last['MACDs_12_26_9']
        except: macd_val, macd_signal = np.nan, np.nan
        try: adx_val = last['ADX_14']
        except: adx_val = np.nan
        if bbu_col_name and bbl_col_name: bb_upper, bb_lower = last[bbu_col_name], last[bbl_col_name]
        else: bb_upper, bb_lower = price * 1.05, price * 0.95
        vol_status, vol_color = analyze_volume(last, last['Vol_SMA20'])
        
        try: obv_val = last['OBV']; obv_avg = last['OBV_SMA20']
        except: obv_val = np.nan; obv_avg = np.nan
        obv_slope_val = last.get('OBV_Slope', np.nan)
        rolling_min_val = last.get('Rolling_Min', np.nan)
        rolling_max_val = last.get('Rolling_Max', np.nan)

        mtf_trend = "Sideway"; mtf_ema200_val = 0
        if df_mtf is not None and not df_mtf.empty:
            if 'EMA200' not in df_mtf.columns: df_mtf['EMA200'] = ta.ema(df_mtf['Close'], length=200)
            if len(df_mtf) > 200 and not pd.isna(df_mtf['EMA200'].iloc[-1]):
                mtf_ema200_val = df_mtf['EMA200'].iloc[-1]
                if df_mtf['Close'].iloc[-1] > mtf_ema200_val: mtf_trend = "Bullish"
                else: mtf_trend = "Bearish"
        
        try: prev_open = df['Open'].iloc[-2]; prev_close = df['Close'].iloc[-2]; vol_avg = last['Vol_SMA20']
        except: prev_open = 0; prev_close = 0; vol_avg = 1

        ai_report = ai_hybrid_analysis(price, ema20, ema50, ema200, rsi, macd_val, macd_signal, adx_val, bb_upper, bb_lower, 
                                       vol_status, mtf_trend, atr, mtf_ema200_val,
                                       open_p, high_p, low_p, close_p, obv_val, obv_avg,
                                       obv_slope_val, rolling_min_val, rolling_max_val,
                                       prev_open, prev_close, vol_now, vol_avg, demand_zones, is_squeeze)

        # Log
        current_time = datetime.now().strftime("%H:%M:%S")
        log_entry = { "เวลา": current_time, "หุ้น": symbol_input, "ราคา": f"{price:.2f}", "Score": f"{ai_report['status_color'].upper()}", "คำแนะนำ": ai_report['banner_title'].split(':')[0], "Action": ai_report['strategy'] }
        st.session_state['history_log'].insert(0, log_entry)
        if len(st.session_state['history_log']) > 10: st.session_state['history_log'] = st.session_state['history_log'][:10]

        # DISPLAY
        logo_url = f"https://financialmodelingprep.com/image-stock/{symbol_input}.png"
        fallback_url = "https://cdn-icons-png.flaticon.com/512/720/720453.png"
        icon_html = f"""<img src="{logo_url}" onerror="this.onerror=null; this.src='{fallback_url}';" style="height: 50px; width: 50px; border-radius: 50%; vertical-align: middle; margin-right: 10px; object-fit: contain; background-color: white; border: 1px solid #e0e0e0; padding: 2px;">"""
        st.markdown(f"<h2 style='text-align: center; margin-top: -15px; margin-bottom: 25px;'>{icon_html} {info['longName']} ({symbol_input})</h2>", unsafe_allow_html=True)

        m_state = info.get('marketState', '').upper()
        if m_state == "REGULAR": st_msg = "🟢 **Market Open:** Real-time Analysis"; st_bg = "#dcfce7"; st_color = "#166534"
        elif m_state in ["PRE", "PREPRE"]: st_msg = "🟠 **Pre-Market:** Pending Open"; st_bg = "#ffedd5"; st_color = "#9a3412"
        elif m_state in ["POST", "POSTPOST"]: st_msg = "🌙 **Post-Market:** Closed"; st_bg = "#e0e7ff"; st_color = "#3730a3"
        else: st_msg = "🔴 **Market Closed**"; st_bg = "#fee2e2"; st_color = "#991b1b"
        st.markdown(f"""<div style="text-align: center; margin-bottom: 20px;"><div style="background-color: {st_bg}; color: {st_color}; padding: 8px 20px; border-radius: 30px; font-size: 0.95rem; font-weight: 600; display: inline-block;">{st_msg}</div></div>""", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            reg_price, reg_chg = info.get('regularMarketPrice'), info.get('regularMarketChange')
            if reg_price and reg_chg: prev_c = reg_price - reg_chg; reg_pct = (reg_chg / prev_c) * 100 if prev_c != 0 else 0.0
            else: reg_pct = 0.0
            color_text = "#16a34a" if reg_chg and reg_chg > 0 else "#dc2626"; bg_color = "#e8f5ec" if reg_chg and reg_chg > 0 else "#fee2e2"
            st.markdown(f"""<div style="margin-bottom:5px; display: flex; align-items: center; gap: 15px; flex-wrap: wrap;"><div style="font-size:40px; font-weight:600; line-height: 1;">{reg_price:,.2f} <span style="font-size: 20px; color: #6b7280; font-weight: 400;">USD</span></div><div style="display:inline-flex; align-items:center; gap:6px; background:{bg_color}; color:{color_text}; padding:4px 12px; border-radius:999px; font-size:18px; font-weight:500;">{arrow_html(reg_chg)} {reg_chg:+.2f} ({reg_pct:.2f}%)</div></div>""", unsafe_allow_html=True)
            def make_pill(change, percent): color = "#16a34a" if change >= 0 else "#dc2626"; bg = "#e8f5ec" if change >= 0 else "#fee2e2"; arrow = "▲" if change >= 0 else "▼"; return f'<span style="background:{bg}; color:{color}; padding: 2px 8px; border-radius: 10px; font-size: 12px; font-weight: 600; margin-left: 8px;">{arrow} {change:+.2f} ({percent:.2f}%)</span>'
            ohlc_html = ""; 
            if m_state != "REGULAR": 
                d_open = info.get('regularMarketOpen'); d_high = info.get('dayHigh'); d_low = info.get('dayLow'); d_close = info.get('regularMarketPrice')
                if d_open: day_chg = info.get('regularMarketChange', 0); val_color = "#16a34a" if day_chg >= 0 else "#dc2626"; ohlc_html = f"""<div style="font-size: 12px; font-weight: 600; margin-bottom: 5px; font-family: 'Source Sans Pro', sans-serif; white-space: nowrap; overflow-x: auto;"><span style="margin-right: 5px; opacity: 0.7;">O</span><span style="color: {val_color}; margin-right: 12px;">{d_open:.2f}</span><span style="margin-right: 5px; opacity: 0.7;">H</span><span style="color: {val_color}; margin-right: 12px;">{d_high:.2f}</span><span style="margin-right: 5px; opacity: 0.7;">L</span><span style="color: {val_color}; margin-right: 12px;">{d_low:.2f}</span><span style="margin-right: 5px; opacity: 0.7;">C</span><span style="color: {val_color};">{d_close:.2f}</span></div>"""
            pre_post_html = ""
            if info.get('preMarketPrice') and info.get('preMarketChange'): p = info.get('preMarketPrice'); c = info.get('preMarketChange'); prev_p = p - c; pct = (c / prev_p) * 100 if prev_p != 0 else 0; pre_post_html += f'<div style="margin-bottom: 6px; font-size: 12px;">☀️ Pre: <b>{p:.2f}</b> {make_pill(c, pct)}</div>'
            if info.get('postMarketPrice') and info.get('postMarketChange'): p = info.get('postMarketPrice'); c = info.get('postMarketChange'); prev_p = p - c; pct = (c / prev_p) * 100 if prev_p != 0 else 0; pre_post_html += f'<div style="margin-bottom: 6px; font-size: 12px;">🌙 Post: <b>{p:.2f}</b> {make_pill(c, pct)}</div>'
            if ohlc_html or pre_post_html: st.markdown(f'<div style="margin-top: -5px; margin-bottom: 15px;">{ohlc_html}{pre_post_html}</div>', unsafe_allow_html=True)

        if tf_code == "1h": tf_label = "TF Hour"
        elif tf_code == "1wk": tf_label = "TF Week"
        else: tf_label = "TF Day"
        st_color = ai_report["status_color"]
        main_status = ai_report["banner_title"]
        if st_color == "green": c2.success(f"📈 {main_status}\n\n**{tf_label}**")
        elif st_color == "red": c2.error(f"📉 {main_status}\n\n**{tf_label}**")
        else: c2.warning(f"⚖️ {main_status}\n\n**{tf_label}**")

        c3, c4 = st.columns(2)
        icon_flat_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="#a3a3a3"><circle cx="12" cy="12" r="10"/></svg>"""
        
        with c3:
            rsi_str = f"{rsi:.2f}" if not np.isnan(rsi) else "N/A"; rsi_text = get_rsi_interpretation(rsi)
            st.markdown(custom_metric_html("⚡ RSI (14)", rsi_str, rsi_text, "gray", icon_flat_svg), unsafe_allow_html=True)
        with c4:
            adx_disp = float(adx_val) if not np.isnan(adx_val) else np.nan
            is_uptrend = price >= ema200 if not np.isnan(ema200) else True
            adx_text = get_adx_interpretation(adx_disp, is_uptrend)
            adx_str = f"{adx_disp:.2f}" if not np.isnan(adx_disp) else "N/A"
            st.markdown(custom_metric_html("💪 ADX Strength", adx_str, adx_text, "gray", icon_flat_svg), unsafe_allow_html=True)
        
        st.write("") 
        c_ema, c_ai = st.columns([1.5, 2])
        with c_ema:
            st.subheader("📉 Technical Indicators")
            vol_str = format_volume(vol_now)
            e20_s = f"{ema20:.2f}" if not np.isnan(ema20) else "N/A"
            e50_s = f"{ema50:.2f}" if not np.isnan(ema50) else "N/A"
            e200_s = f"{ema200:.2f}" if not np.isnan(ema200) else "N/A"
            atr_pct = (atr / price) * 100 if not np.isnan(atr) and price > 0 else 0; atr_s = f"{atr:.2f} ({atr_pct:.1f}%)" if not np.isnan(atr) else "N/A"
            
            # --- 🔥 ADDED: BB Display Here ---
            bb_s = f"{bb_upper:.2f} / {bb_lower:.2f}" if not np.isnan(bb_upper) else "N/A"
            # -------------------------------

            st.markdown(f"""<div style='background-color: var(--secondary-background-color); padding: 15px; border-radius: 10px; font-size: 0.95rem;'><div style='display:flex; justify-content:space-between; margin-bottom:5px; border-bottom:1px solid #ddd; font-weight:bold;'><span>Indicator</span> <span>Value</span></div><div style='display:flex; justify-content:space-between;'><span>EMA 20</span> <span>{e20_s}</span></div><div style='display:flex; justify-content:space-between;'><span>EMA 50</span> <span>{e50_s}</span></div><div style='display:flex; justify-content:space-between;'><span>EMA 200</span> <span>{e200_s}</span></div><div style='display:flex; justify-content:space-between;'><span>Volume ({vol_str})</span> <span style='color:{ai_report['vol_quality_color']}'>{ai_report['vol_quality_msg']}</span></div><div style='display:flex; justify-content:space-between;'><span>ATR</span> <span>{atr_s}</span></div><div style='display:flex; justify-content:space-between;'><span>BB (Up/Low)</span> <span>{bb_s}</span></div></div>""", unsafe_allow_html=True)
            
            # --- DISTANCE FILTER SETTINGS (TUNED) ---
            if tf_code == "1h": min_dist = atr * 1.0 
            elif tf_code == "1wk": min_dist = atr * 2.0 
            else: min_dist = atr * 1.5 

            st.subheader("🚧 Key Levels")
            
            # === PART 1: SUPPORTS ===
            candidates_supp = []
            if not np.isnan(ema20) and ema20 < price: candidates_supp.append({'val': ema20, 'label': f"EMA 20 ({tf_label} - ระยะสั้น)"})
            if not np.isnan(ema50) and ema50 < price: candidates_supp.append({'val': ema50, 'label': f"EMA 50 ({tf_label})"})
            if not np.isnan(ema200) and ema200 < price: candidates_supp.append({'val': ema200, 'label': f"EMA 200 ({tf_label} - Trend Support)"})
            if not np.isnan(bb_lower) and bb_lower < price: candidates_supp.append({'val': bb_lower, 'label': f"BB Lower ({tf_label} - แนวรับผันผวน)"})

            if not df_stats_day.empty:
                d_ema50 = ta.ema(df_stats_day['Close'], length=50).iloc[-1]
                d_ema200 = ta.ema(df_stats_day['Close'], length=200).iloc[-1]
                if d_ema50 < price: candidates_supp.append({'val': d_ema50, 'label': "EMA 50 (TF Day - รับระยะกลาง)"})
                if d_ema200 < price: candidates_supp.append({'val': d_ema200, 'label': "🛡️ EMA 200 (TF Day - รับใหญ่รายวัน)"})
                low_60d = df_stats_day['Low'].tail(60).min()
                if low_60d < price: candidates_supp.append({'val': low_60d, 'label': "📉 Low 60d (ฐานสั้น)"})

            if not df_stats_week.empty:
                w_ema50 = ta.ema(df_stats_week['Close'], length=50).iloc[-1]
                w_ema200 = ta.ema(df_stats_week['Close'], length=200).iloc[-1]
                if w_ema50 < price: candidates_supp.append({'val': w_ema50, 'label': "EMA 50 (TF Week - รับระยะยาว)"})
                if w_ema200 < price: candidates_supp.append({'val': w_ema200, 'label': "🛡️ EMA 200 (TF Week - รับระดับกองทุน)"})

            if demand_zones:
                for z in demand_zones: candidates_supp.append({'val': z['bottom'], 'label': f"Demand Zone [{z['bottom']:.2f}-{z['top']:.2f}]"})

            candidates_supp.sort(key=lambda x: x['val'], reverse=True) # High -> Low for Support

            merged_supp = []
            skip_next = False
            for i in range(len(candidates_supp)):
                if skip_next: skip_next = False; continue
                current = candidates_supp[i]
                if i < len(candidates_supp) - 1:
                    next_item = candidates_supp[i+1]
                    if (current['val'] - next_item['val']) / current['val'] < 0.01: 
                        new_label = f"⭐ Confluence Zone ({current['label']} + {next_item['label']})"
                        merged_supp.append({'val': current['val'], 'label': new_label})
                        skip_next = True
                        continue
                merged_supp.append(current)

            final_show_supp = []
            for item in merged_supp:
                if (price - item['val']) / price > 0.30 and "EMA 200 (TF Week" not in item['label']: continue
                is_vip = "EMA 200" in item['label'] or "EMA 50 (TF Week" in item['label'] or "52-Week" in item['label']
                if not final_show_supp: final_show_supp.append(item)
                else:
                    last_item = final_show_supp[-1]
                    dist = abs(last_item['val'] - item['val'])
                    if is_vip or dist >= min_dist:
                        final_show_supp.append(item)

            st.markdown("#### 🟢 แนวรับ"); 
            if final_show_supp: 
                for item in final_show_supp[:4]: st.write(f"- **{item['val']:.2f} :** {item['label']}")
            else: st.error("🚨 ราคาหลุดทุกแนวรับสำคัญ! (All Time Low?)")

            # === PART 2: RESISTANCES ===
            candidates_res = []
            if not np.isnan(ema20) and ema20 > price: candidates_res.append({'val': ema20, 'label': f"EMA 20 ({tf_label} - ต้านสั้น)"})
            if not np.isnan(ema50) and ema50 > price: candidates_res.append({'val': ema50, 'label': f"EMA 50 ({tf_label})"})
            if not np.isnan(ema200) and ema200 > price: candidates_res.append({'val': ema200, 'label': f"EMA 200 ({tf_label} - ต้านใหญ่)"})
            if not np.isnan(bb_upper) and bb_upper > price: candidates_res.append({'val': bb_upper, 'label': f"BB Upper ({tf_label} - เพดาน)"})
            
            if not df_stats_day.empty:
                d_ema50 = ta.ema(df_stats_day['Close'], length=50).iloc[-1]
                if d_ema50 > price: candidates_res.append({'val': d_ema50, 'label': "EMA 50 (TF Day)"})
                high_60d = df_stats_day['High'].tail(60).max()
                if high_60d > price: candidates_res.append({'val': high_60d, 'label': "🏔️ High 60d (ดอย 3 เดือน)"})

            if not df_stats_week.empty:
                w_ema50 = ta.ema(df_stats_week['Close'], length=50).iloc[-1]
                w_ema200 = ta.ema(df_stats_week['Close'], length=200).iloc[-1]
                if w_ema50 > price: candidates_res.append({'val': w_ema50, 'label': "EMA 50 (TF Week - ต้านระยะยาว)"})
                if w_ema200 > price: candidates_res.append({'val': w_ema200, 'label': "🛡️ EMA 200 (TF Week - ต้านระดับกองทุน)"})
                
            if supply_zones:
                for z in supply_zones: candidates_res.append({'val': z['top'], 'label': f"Supply Zone [{z['bottom']:.2f}-{z['top']:.2f}]"})

            candidates_res.sort(key=lambda x: x['val'])

            merged_res = []
            skip_next = False
            for i in range(len(candidates_res)):
                if skip_next: skip_next = False; continue
                current = candidates_res[i]
                if i < len(candidates_res) - 1:
                    next_item = candidates_res[i+1]
                    if (next_item['val'] - current['val']) / current['val'] < 0.01:
                        new_label = f"⭐ Confluence Zone ({current['label']} + {next_item['label']})"
                        merged_res.append({'val': current['val'], 'label': new_label})
                        skip_next = True
                        continue
                merged_res.append(current)

            final_show_res = []
            for item in merged_res:
                if (item['val'] - price) / price > 0.30 and "EMA 200 (TF Week" not in item['label']: continue
                is_vip = "EMA 200" in item['label'] or "EMA 50 (TF Week" in item['label']
                if not final_show_res: final_show_res.append(item)
                else:
                    last_item = final_show_res[-1]
                    dist = abs(item['val'] - last_item['val'])
                    if is_vip or dist >= min_dist:
                        final_show_res.append(item)

            st.markdown("#### 🔴 แนวต้าน"); 
            if final_show_res: 
                for item in final_show_res[:4]: st.write(f"- **{item['val']:.2f} :** {item['label']}")
            else: st.write("- N/A (Blue Sky)")

        with c_ai:
            st.subheader("🔬 Price Action X-Ray")
            
            sq_col = "#f97316" if ai_report['is_squeeze'] else "#0369a1"
            sq_txt = "⚠️ Squeeze (อัดอั้นรอระเบิด)" if ai_report['is_squeeze'] else "Normal (ปกติ)"
            vol_q_col = ai_report['vol_quality_color']
            vol_txt = ai_report['vol_quality_msg']
            obv_col = "#22c55e" if "Bullish" in ai_report['obv_insight'] else ("#ef4444" if "Bearish" in ai_report['obv_insight'] else "#6b7280")
            dz_status = "✅ อยู่ในโซน (In Zone)" if ai_report['in_demand_zone'] else "❌ นอกโซน (รอราคา)"
            
            st.markdown(f"""
            <div class='xray-box'>
                <div class='xray-title'>🕯️ Deep Insight</div>
                <div class='xray-item'><span>ทรงกราฟ:</span> <span style='font-weight:bold;'>{ai_report['candle_pattern']}</span></div>
                <div class='xray-item'><span>สถานะ:</span> <span>{ai_report['candle_color']}</span></div>
                <div class='xray-item'><span>รายละเอียด:</span> <span style='font-style:italic;'>{ai_report['candle_detail']}</span></div>
                <hr style='margin: 8px 0; opacity: 0.3;'>
                <div class='xray-item'><span>🔥 ความผันผวน (BB):</span> <span style='color:{sq_col}; font-weight:bold;'>{sq_txt}</span></div>
                <div class='xray-item'><span>📊 คุณภาพ Volume:</span> <span style='color:{vol_q_col}; font-weight:bold;'>{vol_txt}</span></div>
                <div class='xray-item'><span>🌊 รายใหญ่ (OBV):</span> <span style='color:{obv_col}; font-weight:bold;'>{ai_report['obv_insight']}</span></div>
                <div class='xray-item'><span>🎯 Demand Zone:</span> <span style='font-weight:bold;'>{dz_status}</span></div>
            </div>
            """, unsafe_allow_html=True)
            
            st.subheader("🤖 AI STRATEGY (Hybrid)")
            color_map = {"green": {"bg": "#dcfce7", "border": "#22c55e", "text": "#14532d"}, "red": {"bg": "#fee2e2", "border": "#ef4444", "text": "#7f1d1d"}, "orange": {"bg": "#ffedd5", "border": "#f97316", "text": "#7c2d12"}, "yellow": {"bg": "#fef9c3", "border": "#eab308", "text": "#713f12"}}
            c_theme = color_map.get(ai_report['status_color'], color_map["yellow"])
            st.markdown(f"""<div style="background-color: {c_theme['bg']}; border-left: 6px solid {c_theme['border']}; padding: 20px; border-radius: 10px; margin-bottom: 20px;"><h2 style="color: {c_theme['text']}; margin:0 0 10px 0; font-size: 28px;">{ai_report['banner_title']}</h2><h3 style="color: {c_theme['text']}; margin:0 0 15px 0; font-size: 20px; opacity: 0.9;">{ai_report['strategy']}</h3><p style="color: {c_theme['text']}; font-size: 16px; margin:0; line-height: 1.6;"><b>💡 Insight:</b> {ai_report['context']}</p></div>""", unsafe_allow_html=True)
            with st.chat_message("assistant"):
                if ai_report['bullish_factors']: 
                    st.markdown("**🟢 ปัจจัยบวก:**")
                    for r in ai_report['bullish_factors']: st.write(f"- {r}")
                if ai_report['bearish_factors']: 
                    st.markdown("**🔴 ปัจจัยลบ/ความเสี่ยง:**")
                    for w in ai_report['bearish_factors']: st.write(f"- {w}")
                
                st.markdown("---")
                if "green" in ai_report['status_color']: box_type = st.success
                elif "red" in ai_report['status_color']: box_type = st.error
                else: box_type = st.warning
                
                box_type(f"""
                ### 📝 บทสรุปและคำแนะนำ (Action Plan)
                
                **1. สถานการณ์ (Context):** {ai_report['context']}
                
                **2. คำแนะนำ (Action):** 👉 **{ai_report['strategy']}** : {ai_report['holder_advice']}
                
                **3. แผนการเทรด (Setup):** 🛑 **Stop Loss (หนี):** {ai_report['sl']:.2f}  |  ✅ **Take Profit (เป้า):** {ai_report['tp']:.2f}
                """)

        st.write(""); st.markdown("""<div class='disclaimer-box'>⚠️ <b>หมายเหตุ:</b> ข้อมูลนี้มาจากการวิเคราะห์ทางเทคนิคด้วยระบบ AI เพื่อประกอบการตัดสินใจเท่านั้น</div>""", unsafe_allow_html=True); st.divider()
        st.subheader("📜 History Log")
        if st.session_state['history_log']: st.dataframe(pd.DataFrame(st.session_state['history_log']), use_container_width=True, hide_index=True)

    else: st.error("ไม่พบข้อมูลหุ้น หรือข้อมูลไม่เพียงพอสำหรับคำนวณ Swing Low")
