import os
import requests
import datetime
import re
import yfinance as yf

def get_current_time():
    """방콕 시간(UTC+7) 기준으로 현재 날짜와 시간을 한글 포맷으로 가져옵니다."""
    tz_local = datetime.timezone(datetime.timedelta(hours=7))
    now = datetime.datetime.now(tz_local)
    weekdays = ['월', '화', '수', '목', '금', '토', '일']
    weekday_kr = weekdays[now.weekday()]
    return now.strftime(f"%Y년 %m월 %d일 ({weekday_kr}) %H:%M")

def get_pace_and_rationale(content, week_num):
    """Section 4 및 4-1 데이터를 기반으로 구체적 페이스와 냉철한 생리학적 근거를 매칭합니다."""
    is_early = week_num <= 9
    paces = []
    rationales = []
    
    # 1. 페이스 및 심박 추출 로직
    if "회복조깅" in content or "Z1" in content:
        paces.append("  • 회복조깅(Z1): 7:30/km 이상 (심박 115-135bpm 제한)")
        rationales.append("  • [회복조깅]: 전날 누적된 대사 부산물을 신속히 제거하고, 부상 리스크 없이 모세혈관 밀도를 높여 신체 회복 속도를 극대화합니다.")
        
    if "이지런" in content or "크루" in content or "펀런" in content or "Z2" in content:
        if "6:00-7:00" in content or "크루" in content:
            paces.append("  • 크루 펀런 / 이지런(Z2): 6:00~7:00/km (심박 135-155bpm 안정적 유지)")
        else:
            paces.append("  • 이지런(Z2): 6:00~7:20/km (심박 135-155bpm 안정적 유지)")
        rationales.append("  • [이지런/Z2]: 심실 용적을 확장시켜 1회 박출량을 늘리고 미토콘드리아 수를 증폭함으로써, 부상 없이 강력한 유산소 기초 체력(심폐 베이스)을 다집니다.")
        
    if "템포런" in content or "Z4" in content:
        p_range = "4:55~5:05/km" if is_early else "4:45~4:55/km"
        paces.append(f"  • 템포런 본세트(Z4): {p_range} (심박 168-183bpm 역치 타격)")
        phase_str = "초반부(1-9주)" if is_early else "후반부(10-17주)"
        rationales.append(f"  • [템포런/Z4]: {phase_str} 공식 페이스를 준수합니다. 젖산 역치(Lactate Threshold) 지점을 뒤로 밀어내어, 목표 마라톤 페이스(4:59/km)에서 젖산이 쌓이지 않고 에너지를 지속 공급하는 '피로 저항성'을 개척하기 위함입니다.")
        
    if "인터벌" in content or "Z5" in content:
        if "1000m" in content:
            p_range = "4:15~4:25/km" if is_early else "4:05~4:15/km"
            paces.append(f"  • 1000m 인터벌 세트: {p_range} (회복조깅 90초 고정)")
        elif "800m" in content:
            p_range = "4:05~4:15/km" if is_early else "3:55~4:05/km"
            paces.append(f"  • 800m 인터벌 세트: {p_range} (회복조깅 400m 이동하며 회복)")
        else:
            paces.append("  • 인터벌 세트(Z5): 4:45/km 이하 (최대심박 영역 진입)")
        rationales.append("  • [인터벌/Z5]: 최대산소섭취량(VO2max) 영역을 강하게 자극하여 심폐 엔진 자체의 크기를 확장하고, 무산소 역량과 스피드 지속 능력을 발달시킵니다.")
        
    if "Z3" in content or "MP" in content:
        paces.append("  • 마라톤 존(Z3): 페이스 동결 금지 ❌ 오직 심박 155-168bpm 제한 (목표 범위 5:00~5:30/km)")
        rationales.append("  • [Z3/MP]: 심박을 155-168bpm으로 묶어 에어로빅 디커플링(후반부 심박 치솟음)을 억제하고 에너지 효율성을 극대화하는 진짜 마라톤 체력을 이식하는 과정입니다.")

    # 워밍업 및 쿨다운 가이드 자동 조립
    if "WU" in content:
        paces.insert(0, "  • 워밍업(WU): 6:00~7:20/km (Z2 영역에서 부드럽게 예열)")
        rationales.insert(0, "  • [WU (워밍업)]: 본세트 강도 진입 전 심박수를 점진적으로 올리고 근육 및 관절 유연성을 확보하여 급격한 심폐 피로와 부상을 방지합니다.")
    if "CD" in content:
        paces.append("  • 쿨다운(CD): Z2 페이스 또는 7:30/km 이상으로 아주 가볍게")
        rationales.append("  • [CD (쿨다운)]: 고강도 훈련 후 심박수를 안전하게 떨어뜨리고, 근육 내 쌓인 젖산 등 대사 부산물을 신속히 혈류로 배출시켜 회복을 앞당깁니다.")

    extra = ""
    if paces:
        extra += "\n🎯 <b>구체적 목표 페이스 및 심박 가이드:</b>\n" + "\n".join(paces)
    if rationales:
        extra += "\n\n💡 <b>훈련 거리·페이스별 생리학적 근거 (Sub-3:30 전략):</b>\n" + "\n".join(rationales)
    return extra

def get_today_training(simulated_date=None):
    """marathon_plan.md 파일에서 지정된 날짜의 훈련 정보를 파악하고 정밀 가이드를 구성합니다."""
    tz_local = datetime.timezone(datetime.timedelta(hours=7))
    now = datetime.datetime.now(tz_local)
    
    today_date = simulated_date if simulated_date else now.date()
    
    # ⚙️ [11월 29일 대회 당일 이후 예외 조건 처리]
    if today_date >= datetime.date(2026, 11, 29):
        return "🏃‍♂️ <b>오늘의 마라톤 훈련 계획:</b>\n  ℹ️ 11월 29일 대회 이후 일정입니다. 러닝 훈련 부분은 새로 세팅해야 합니다."

    file_path = "marathon_plan.md"
    if not os.path.exists(file_path):
        return "🏃‍♂️ <b>오늘의 마라톤 훈련 일정:</b>\n  ℹ️ <code>marathon_plan.md</code> 파일이 없습니다."
    
    patterns = [f"{today_date.month:02d}/{today_date.day:02d}", f"{today_date.month}/{today_date.day}"]
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        current_week_header = ""
        week_num = 1
        found_row = None
        all_program_dates = []
        
        for line in lines:
            clean_line = line.strip()
            if not clean_line:
                continue
                
            if "주차" in clean_line or clean_line.startswith("###"):
                current_week_header = clean_line.replace("#", "").strip()
                week_match = re.search(r'(\d+)주차', clean_line)
                if week_match:
                    week_num = int(week_match.group(1))
            
            date_matches = re.findall(r'(\d{1,2})/(\d{1,2})', clean_line)
            for m in date_matches:
                try:
                    all_program_dates.append(datetime.date(today_date.year, int(m[0]), int(m[1])))
                except ValueError:
                    pass
            
            if any(p in clean_line for p in patterns) and "~" not in clean_line:
                if not found_row:
                    found_row = clean_line
        
        if found_row:
            if "|" in found_row:
                parts = [p.strip() for p in found_row.split("|") if p.strip()]
            else:
                parts = [p.strip() for re_split in [re.split(r'\s{2,}', found_row)] for p in re_split if p.strip()]
            
            if len(parts) >= 3:
                col1, col2 = parts[0], parts[1]
                content = " ".join(parts[2:])
                formatted_training = f"📅 <b>{col2} ({col1})</b>\n🏃‍♂️ <b>훈련 내용:</b> {content}"
            else:
                content = found_row.replace('|', ' ').strip()
                formatted_training = f"🏃‍♂️ <b>훈련 내용:</b> {content}"
            
            guide_and_rationale = get_pace_and_rationale(content, week_num)
            
            output = ["🏃‍♂️ <b>오늘의 마라톤 훈련 계획 & 근거</b>\n"]
            if current_week_header:
                output.append(f"📋 <b>{current_week_header}</b>")
            output.append(formatted_training)
            if guide_and_rationale:
                output.append(guide_and_rationale)
            return "\n".join(output)
        
        if all_program_dates:
            all_program_dates.sort()
            if today_date < all_program_dates[0]:
                return f"🏃‍♂️ <b>오늘의 마라톤 훈련 계획:</b>\n  ℹ️ 아직 정식 훈련 프로그램 시작 전입니다. 첫 훈련은 <b>{all_program_dates[0].strftime('%m/%d')}</b>에 시작됩니다!"
            elif today_date > all_program_dates[-1]:
                return "🏃‍♂️ <b>오늘의 마라톤 훈련 계획:</b>\n  ℹ️ 모든 프로그램이 완료되었습니다. 대회를 완벽하게 지배하세요!"
        
        return "🏃‍♂️ <b>오늘의 마라톤 훈련 계획:</b>\n  ☀️ 오늘은 계획표상 명시된 일정이 없는 <b>공식 휴식일(Rest Day)</b>입니다. 철저한 신체 회복과 스트레칭에 전념하십시오."
            
    except Exception as e:
        return f"🏃‍♂️ <b>오늘의 마라톤 훈련 계획:</b>\n  ❌ 파일 파싱 오류: {str(e)}"

def get_air_quality(api_key, lat, lon):
    url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={api_key.strip()}"
    try:
        res = requests.get(url).json()
        aqi = res['list'][0]['main']['aqi']
        aqi_map = {1: "🟢 좋음 (야외 훈련 최적!)", 2: "🟡 보통", 3: "🟠 민감군 주의", 4: "🔴 나쁨", 5: "💀 매우 나쁨"}
        return aqi_map.get(aqi, "⏳ 정보 확인 불가")
    except:
        return "⏳ 정보 확인 불가"

def get_financial_snapshots():
    tickers = {"💵 바트/원 환율": "THBKRW=X", "🇺🇸 원/달러 환율": "USDKRW=X", "📈 나스닥 종합": "^IXIC"}
    fin_lines = ["📊 <b>글로벌 금융 스냅샷</b>"]
    try:
        for name, ticker_symbol in tickers.items():
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="2d")
            if len(hist) < 2: continue
            current_val, prev_val = hist['Close'].iloc[-1], hist['Close'].iloc[-2]
            change = current_val - prev_val
            pct = (change / prev_val) * 100
            sign = "🔺" if change > 0 else "🔻" if change < 0 else "🔹"
            if "환율" in name:
                fin_lines.append(f"  • {name}: <b>{current_val:.2f}원</b> ({sign} {abs(change):.2f}원)")
            else:
                fin_lines.append(f"  • {name}: <b>{current_val:,.2f}</b> ({sign} {pct:.2f}%)")
        return "\n".join(fin_lines)
    except:
        return "⏳ 금융 데이터 로딩 지연"

def get_hyper_local_weather(api_key, lat, lon, custom_name=None):
    if not api_key: return "❌ 날씨 API 키 미설정", ""
    url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key.strip()}&units=metric&lang=kr"
    try:
        response = requests.get(url)
        res = response.json()
        if response.status_code != 200: return "❌ 날씨 데이터 로드 실패", ""
        
        forecast_list = res.get("list", [])[:8]
        location_name = custom_name.strip() if custom_name and custom_name.strip() else res.get("city", {}).get("name", "내 위치")
        current_desc = forecast_list[0]["weather"][0]["description"]
        current_temp = forecast_list[0]["main"]["temp"]
        humidity = forecast_list[0]["main"]["humidity"]
        temps = [item["main"]["temp"] for item in forecast_list]
        
        max_pop = 0
        pop_morning, pop_afternoon, pop_evening = "0%", "0%", "0%"
        timezone_offset = res["city"]["timezone"]
        
        for item in forecast_list:
            local_dt = datetime.datetime.fromtimestamp(item["dt"] + timezone_offset, datetime.timezone.utc)
            pop_val = int(item.get('pop', 0) * 100)
            pop_percent = f"{pop_val}%"
            if pop_val > max_pop: max_pop = pop_val
            if 6 <= local_dt.hour <= 9: pop_morning = pop_percent
            elif 12 <= local_dt.hour <= 15: pop_afternoon = pop_percent
            elif 18 <= local_dt.hour <= 21: pop_evening = pop_percent

        if current_desc == "실 비": current_desc = "이슬비(실비)"
        umbrella_reminder = "🚨 <b>[알림] 오늘 비 예보가 있습니다! 외출 시 우산을 꼭 챙기세요.</b>\n\n" if max_pop >= 60 else ""

        weather_text = (
            f"📍 <b>{location_name} 날씨:</b> {current_desc}\n"
            f"🌡️ <b>기온:</b> {current_temp}°C (최고 <b>{max(temps)}°C</b> / 최저 <b>{min(temps)}°C</b>)\n"
            f"💧 <b>습도:</b> {humidity}%\n"
            f"🌧️ <b>시간대별 비 올 확률:</b>\n"
            f"  • 아침 (07시 전후): {pop_morning}\n"
            f"  • 점심 (13시 전후): {pop_afternoon}\n"
            f"  • 저녁 (19시 전후): {pop_evening}"
        )
        return weather_text, umbrella_reminder
    except Exception as e:
        return f"❌ 날씨 시스템 예외: {str(e)}", ""

def send_telegram(token, chat_id, text):
    if not token or not chat_id:
        print("❌ [오류] 환경 변수 세팅 누락")
        return
    
    url = f"https://api.telegram.org/bot{token.strip()}/sendMessage"
    payload = {
        "chat_id": chat_id.strip(),
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    
    try:
        res = requests.post(url, json=payload)
        if res.status_code != 200:
            print(f"❌ [텔레그램 API 리턴 오류] {res.text}")
        else:
            print("✅ 텔레그램 메시지가 완벽히 발송되었습니다!")
    except Exception as e:
        print(f"❌ [텔레그램 네트워크 오류] {str(e)}")

if __name__ == "__main__":
    TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
    CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
    WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")
    LAT = os.environ.get("WEATHER_LAT", "13.7563")
    LON = os.environ.get("WEATHER_LON", "100.5018")
    WEATHER_NAME = os.environ.get("WEATHER_NAME")

    print("\n🚀 [로그] 순서가 조정된 브리핑을 생성합니다.")

    current_time = get_current_time()
    weather_info, umbrella_alert = get_hyper_local_weather(WEATHER_API_KEY, LAT, LON, WEATHER_NAME)
    air_info = get_air_quality(WEATHER_API_KEY, LAT, LON)
    finance_info = get_financial_snapshots()
    
    # 러닝 정보를 변수에 담아둔 후 맨 마지막에 배치
    training_info = get_today_training()
    
    # 📝 [순서 변경 조정 영역]
    message = (
        f"☀️ <b>Good Morning! 아침 브리핑</b> ☀️\n"
        f"📅 <b>일시:</b> {current_time}\n\n"
        f"{umbrella_alert}"
        f"{weather_info}\n"
        f"😷 <b>대기질(미세먼지):</b> {air_info}\n\n"
        f"{finance_info}\n\n"
        f"-----------------------------------------\n\n"
        f"{training_info}"
    )
    
    send_telegram(TELEGRAM_TOKEN, CHAT_ID, message)
