import os
import requests
import datetime
import math
import yfinance as yf

# ⚙️ 마라톤 프로그램이 시작하는 '월요일' 날짜를 적어주세요 (주차 계산용)
# 예: 2026년 7월 6일 월요일부터 시작하는 스케줄인 경우
PLAN_START_DATE = datetime.date(2026, 7, 6)

def get_current_time():
    """방콕 시간(UTC+7) 기준으로 현재 날짜와 시간을 한글 포맷으로 가져옵니다."""
    tz_local = datetime.timezone(datetime.timedelta(hours=7))
    now = datetime.datetime.now(tz_local)
    weekdays = ['월', '화', '수', '목', '금', '토', '일']
    weekday_kr = weekdays[now.weekday()]
    return now.strftime(f"%Y년 %m월 %d일 ({weekday_kr}) %H:%M")

def get_today_training():
    """깃허브에 업로드된 marathon_plan.md 파일에서 오늘 자 훈련 일정과 근거를 파싱합니다."""
    file_path = "marathon_plan.md"
    if not os.path.exists(file_path):
        return "🏃‍♂️ <b>오늘의 마라톤 훈련 일정:</b>\n  ℹ️ <code>marathon_plan.md</code> 파일이 저장소에 없습니다. 파일을 업로드하시면 내일 아침부터 훈련 일정을 읽어옵니다."
    
    tz_local = datetime.timezone(datetime.timedelta(hours=7))
    now = datetime.datetime.now(tz_local)
    today_date = now.date()
    
    # 검색 키워드 1: 날짜 포맷 (예: "7월 5일" 또는 "07월 05일")
    date_key_1 = f"{now.month}월 {now.day}일"
    date_key_2 = f"{now.month:02d}월 {now.day:02d}일"
    
    # 검색 키워드 2: 주차 및 요일 포맷 (예: "1주차" -> "일요일")
    weekdays_full = ['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일']
    weekdays_short = ['(월)', '(화)', '(수)', '(목)', '(금)', '(토)', '(일)']
    current_weekday_full = weekdays_full[today_date.weekday()]
    current_weekday_short = weekdays_short[today_date.weekday()]
    
    days_elapsed = (today_date - PLAN_START_DATE).days
    current_week = (days_elapsed // 7) + 1
    week_key = f"{current_week}주차"
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        target_lines = []
        found = False
        
        # 1차 시도: 텍스트 안에서 직접적인 오늘 날짜(예: 7월 5일)를 찾아 파싱
        for i, line in enumerate(lines):
            if date_key_1 in line or date_key_2 in line:
                found = True
                target_lines.append(line.strip())
                for next_line in lines[i+1:]:
                    # 다음 날짜 헤더나 대분류(#)를 만나면 종료
                    if ("월" in next_line and "일" in next_line) or next_line.startswith("#"):
                        break
                    target_lines.append(next_line.strip())
                break
                
        # 2차 시도: 날짜로 못 찾은 경우 주차별 요일(예: 1주차 -> 일요일)을 찾아 파싱
        if not found and days_elapsed >= 0:
            inside_correct_week = False
            for i, line in enumerate(lines):
                # 해당 주차 섹션 진입 확인
                if week_key in line and ("#" in line or "**" in line):
                    inside_correct_week = True
                    continue
                # 다음 주차를 만나면 주차 섹션 탈출
                if inside_correct_week and f"{current_week+1}주차" in line:
                    break
                    
                if inside_correct_week:
                    # 해당 주차 안에서 오늘 요일이 매칭되는지 확인
                    if current_weekday_full in line or current_weekday_short in line or f"**{current_weekday_full[0]}**" in line:
                        found = True
                        target_lines.append(f"📅 <b>{week_key} {current_weekday_full} 훈련 계획</b>")
                        target_lines.append(line.strip())
                        for next_line in lines[i+1:]:
                            # 다음 요일이나 다음 주차, 혹은 대분류를 만나면 종료
                            if any(w in next_line for w in weekdays_full) or "주차" in next_line or next_line.startswith("#"):
                                break
                            target_lines.append(next_line.strip())
                        break

        if found:
            # 빈 줄 정돈 및 가독성 확보
            clean_text = "\n".join([l for l in target_lines if l])
            return f"🏃‍♂️ <b>오늘의 마라톤 훈련 계획 & 근거</b>\n\n{clean_text}"
        else:
            return f"🏃‍♂️ <b>오늘의 마라톤 훈련 계획:</b>\n  ℹ️ <code>marathon_plan.md</code> 파일에서 오늘 자 일정({now.month}/{now.day} 또는 {week_key} {current_weekday_full})을 찾지 못했습니다. 형식을 확인해 주세요."
            
    except Exception as e:
        return f"🏃‍♂️ <b>오늘의 마라톤 훈련 계획:</b>\n  ❌ 파일 파싱 중 오류 발생: {str(e)}"

def get_running_guide(temp, humidity):
    """현재 기온과 습도를 기반으로 체감 온도(Apparent Temp)를 계산하여 러닝 가이드를 제안합니다."""
    try:
        e = (humidity / 100) * 6.105 * math.exp((17.27 * temp) / (237.7 + temp))
        apparent_temp = temp + 0.33 * e - 4.0
        
        if apparent_temp < 26:
            guide = "🟢 훈련하기 좋은 쾌적한 체감 온도입니다. 빌드업이나 포인트 훈련을 추천합니다!"
        elif apparent_temp < 31:
            guide = "🟡 체감 온도가 다소 높습니다. 훈련 중 충분히 수분을 섭취하세요."
        elif apparent_temp < 36:
            guide = "🟠 습도가 높아 지치기 쉽습니다. 계획보다 페이스를 10~15초 낮추고 조깅 위주로 훈련하세요."
        else:
            guide = "🔴 열사병 위험이 높은 무더위입니다. 가급적 실내 트레드밀 훈련을 권장합니다."
            
        return f"🏃‍♂️ <b>실시간 러닝 지수 (체감 {apparent_temp:.1f}°C):</b>\n  {guide}"
    except:
        return "🏃‍♂️ <b>실시간 러닝 지수:</b> 기상 데이터 기반 가이드 생성 실패"

def get_air_quality(api_key, lat, lon):
    """현재 동네의 미세먼지(AQI) 상태를 가져옵니다."""
    url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={api_key.strip()}"
    try:
        res = requests.get(url).json()
        aqi = res['list'][0]['main']['aqi']
        aqi_map = {
            1: "🟢 좋음 (야외 훈련 최적!)",
            2: "🟡 보통 (무난한 대기질)",
            3: "🟠 민감군 주의",
            4: "🔴 나쁨 (야외 운동 자제)",
            5: "💀 매우 나쁨"
        }
        return aqi_map.get(aqi, "⏳ 정보 확인 불가")
    except:
        return "⏳ 정보 확인 불가"

def get_financial_snapshots():
    """요청하신 환율 정보(바트화, 달러화) 및 미국 나스닥 종합 지수 마감을 가져옵니다."""
    tickers = {
        "💵 바트/원 환율": "THBKRW=X",
        "🇺🇸 원/달러 환율": "USDKRW=X",
        "📈 나스닥 종합": "^IXIC"
    }
    
    fin_lines = ["📊 <b>글로벌 금융 스냅샷</b>"]
    try:
        for name, ticker_symbol in tickers.items():
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="2d")
            if len(hist) < 2:
                continue
            
            current_val = hist['Close'].iloc[-1]
            prev_val = hist['Close'].iloc[-2]
            change = current_val - prev_val
            pct = (change / prev_val) * 100
            sign = "🔺" if change > 0 else "🔻" if change < 0 else "🔹"
            
            if "환율" in name:
                fin_lines.append(f"  • {name}: <b>{current_val:.2f}원</b> ({sign} {abs(change):.2f}원)")
            else:
                fin_lines.append(f"  • {name}: <b>{current_val:,.2f}</b> ({sign} {pct:.2f}%)")
        return "\n".join(fin_lines)
    except:
        return "⏳ 금융 데이터 로딩 지연 (주말 또는 서버 일시 오류)"

def get_hyper_local_weather(api_key, lat, lon, custom_name=None):
    """지정한 좌표 기반 초정밀 예보 및 우산 리마인더 기능을 수행합니다."""
    if not api_key:
        return "❌ 날씨 API 키 미설정", ""
    
    url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key.strip()}&units=metric&lang=kr"
    try:
        response = requests.get(url)
        res = response.json()
        
        if response.status_code != 200:
            return "❌ 날씨 데이터 로드 실패", ""
        
        forecast_list = res.get("list", [])[:8]
        location_name = custom_name.strip() if custom_name and custom_name.strip() else res.get("city", {}).get("name", "내 위치")
        
        current_desc = forecast_list[0]["weather"][0]["description"]
        current_temp = forecast_list[0]["main"]["temp"]
        humidity = forecast_list[0]["main"]["humidity"]
        
        temps = [item["main"]["temp"] for item in forecast_list]
        max_temp = max(temps)
        min_temp = min(temps)
        
        timezone_offset = res["city"]["timezone"]
        pop_morning, pop_afternoon, pop_evening = "0%", "0%", "0%"
        max_pop = 0
        
        for item in forecast_list:
            local_timestamp = item["dt"] + timezone_offset
            local_dt = datetime.datetime.fromtimestamp(local_timestamp, tz=datetime.timezone.utc)
            local_hour = local_dt.hour
            pop_val = int(item.get('pop', 0) * 100)
            pop_percent = f"{pop_val}%"
            
            if pop_val > max_pop:
                max_pop = pop_val
            
            if 6 <= local_hour <= 9:
                pop_morning = pop_percent
            elif 12 <= local_hour <= 15:
                pop_afternoon = pop_percent
            elif 18 <= local_hour <= 21:
                pop_evening = pop_percent

        if current_desc == "실 비":
            current_desc = "이슬비(실비)"

        umbrella_reminder = ""
        if max_pop >= 60:
            umbrella_reminder = "🚨 <b>[알림] 오늘 비 예보가 있습니다! 외출 시 우산을 꼭 챙기세요.</b>\n\n"

        weather_text = (
            f"📍 <b>{location_name} 날씨:</b> {current_desc}\n"
            f"🌡️ <b>기온:</b> {current_temp}°C (최고 <b>{max_temp}°C</b> / 최저 <b>{min_temp}°C</b>)\n"
            f"💧 <b>습도:</b> {humidity}%\n"
            f"🌧️ <b>시간대별 비 올 확률:</b>\n"
            f"  • 아침 (07시 전후): {pop_morning}\n"
            f"  • 점심 (13시 전후): ${pop_afternoon}\n"
            f"  • 저녁 (19시 전후): ${pop_evening}\n\n"
            f"{get_running_guide(current_temp, humidity)}"
        )
        return weather_text, umbrella_reminder

    except Exception as e:
        return f"❌ 날씨 시스템 예외: {str(e)}", ""

def send_telegram(token, chat_id, text):
    """결과 메시지를 HTML 포맷으로 텔레그램에 전송합니다."""
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token.strip()}/sendMessage"
    payload = {
        "chat_id": chat_id.strip(),
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    requests.post(url, json=payload)

if __name__ == "__main__":
    TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
    CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
    WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")
    
    LAT = os.environ.get("WEATHER_LAT", "13.7563")
    LON = os.environ.get("WEATHER_LON", "100.5018")
    WEATHER_NAME = os.environ.get("WEATHER_NAME")

    # 데이터 순차 취합
    current_time = get_current_time()
    training_info = get_today_training()
    weather_info, umbrella_alert = get_hyper_local_weather(WEATHER_API_KEY, LAT, LON, WEATHER_NAME)
    air_info = get_air_quality(WEATHER_API_KEY, LAT, LON)
    finance_info = get_financial_snapshots()
    
    #종합 메시지 빌드
    message = (
        f"☀️ <b>Good Morning! 아침 브리핑</b> ☀️\n"
        f"📅 <b>일시:</b> {current_time}\n\n"
        f"{training_info}\n\n"
        f"{umbrella_alert}"
        f"{weather_info}\n"
        f"😷 <b>대기질(미세먼지):</b> {air_info}\n\n"
        f"{finance_info}"
    )
    
    send_telegram(TELEGRAM_TOKEN, CHAT_ID, message)
