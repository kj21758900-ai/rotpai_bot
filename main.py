import os
import requests
import datetime
import math
import re
import yfinance as yf

def get_current_time():
    """방콕 시간(UTC+7) 기준으로 현재 날짜와 시간을 한글 포맷으로 가져옵니다."""
    tz_local = datetime.timezone(datetime.timedelta(hours=7))
    now = datetime.datetime.now(tz_local)
    weekdays = ['월', '화', '수', '목', '금', '토', '일']
    weekday_kr = weekdays[now.weekday()]
    return now.strftime(f"%Y년 %m월 %d일 ({weekday_kr}) %H:%M")

def get_today_training():
    """marathon_plan.md 파일에서 오늘 자 테이블 행을 찾아 정확하게 매칭합니다."""
    file_path = "marathon_plan.md"
    if not os.path.exists(file_path):
        return "🏃‍♂️ <b>오늘의 마라톤 훈련 일정:</b>\n  ℹ️ <code>marathon_plan.md</code> 파일이 저장소에 없습니다."
    
    tz_local = datetime.timezone(datetime.timedelta(hours=7))
    now = datetime.datetime.now(tz_local)
    today_date = now.date()
    
    # 텍스트 표 내부에서 검색할 오늘 날짜 패턴들
    patterns = [
        f"{now.month:02d}/{now.day:02d}",
        f"{now.month}/{now.day}",
        f"{now.month:02d}월 {now.day:02d}일",
        f"{now.month}월 {now.day}일"
    ]
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        current_week_header = ""
        found_row = None
        all_program_dates = []
        
        # 파일 전체를 스캔하며 데이터 수집
        for line in lines:
            clean_line = line.strip()
            if not clean_line:
                continue
                
            # 주차 정보를 담은 헤더 라인 기억
            if "주차" in clean_line or clean_line.startswith("#"):
                current_week_header = clean_line.replace("#", "").strip()
            
            # 파일 내에 등장하는 모든 MM/DD 형태의 날짜 수집 (시작일/종료일 판단용)
            date_matches = re.findall(r'(\d{1,2})/(\d{1,2})', clean_line)
            for m in date_matches:
                try:
                    all_program_dates.append(datetime.date(today_date.year, int(m[0]), int(m[1])))
                except ValueError:
                    pass
            
            # 오늘 날짜 패턴 매칭 (단, 기간 범위가 표시된 주차 헤더 행은 매칭에서 제외)
            if any(p in clean_line for p in patterns) and "~" not in clean_line:
                found_row = clean_line
                break
        
        # 1차: 오늘 날짜가 표에 정확히 존재하는 경우
        if found_row:
            if "|" in found_row:
                parts = [p.strip() for p in found_row.split("|") if p.strip()]
            else:
                parts = [p.strip() for re_split in [re.split(r'\s{2,}', found_row)] for p in re_split if p.strip()]
            
            if len(parts) >= 3:
                col1, col2 = parts[0], parts[1]
                content = " ".join(parts[2:])
                if "/" in col2:
                    formatted_training = f"📅 <b>{col2} ({col1})</b>\n🏃‍♂️ <b>훈련 내용:</b> {content}"
                else:
                    formatted_training = f"📅 <b>{col1} ({col2})</b>\n🏃‍♂️ <b>훈련 내용:</b> {content}"
            else:
                formatted_training = f"🏃‍♂️ <b>훈련 내용:</b> {found_row.replace('|', ' ').strip()}"
            
            output = ["🏃‍♂️ <b>오늘의 마라톤 훈련 계획 & 근거</b>\n"]
            if current_week_header:
                output.append(f"📋 <b>{current_week_header}</b>")
            output.append(formatted_training)
            return "\n".join(output)
        
        # 2차 예외 처리: 오늘 날짜가 표에 없는 경우 (예측 구동을 차단하고 팩트 체크)
        if all_program_dates:
            all_program_dates.sort()
            min_date = all_program_dates[0]
            max_date = all_program_dates[-1]
            
            # 오늘이 첫 훈련 시작일보다 이전인 경우
            if today_date < min_date:
                return f"🏃‍♂️ <b>오늘의 마라톤 훈련 계획:</b>\n  ℹ️ 아직 정식 훈련 프로그램 시작 전입니다. 첫 훈련은 <b>{min_date.strftime('%m/%d')}</b>에 시작됩니다! 오늘은 목표 달성을 위한 에너지를 충전하며 편안히 휴식하세요."
            # 오늘이 프로그램 전체 종료일보다 이후인 경우
            elif today_date > max_date:
                return "🏃‍♂️ <b>오늘의 마라톤 훈련 계획:</b>\n  ℹ️ 프로그램에 편성된 모든 훈련 일정이 완료되었습니다. 대회 승리를 응원합니다!"
        
        # 프로그램 기간 내에 있지만 오늘 날짜 행이 명시되지 않은 경우 (보통 표에서 제외된 휴식일)
        return "🏃‍♂️ <b>오늘의 마라톤 훈련 계획:</b>\n  ☀️ 오늘은 훈련 계획표에 일정이 없는 <b>공식 휴식일(Rest Day)</b>입니다. 냉철한 레이스 준비를 위해 신체 회복과 스트레칭에 집중하세요."
            
    except Exception as e:
        return f"🏃‍♂️ <b>오늘의 마라톤 훈련 계획:</b>\n  ❌ 파일 파싱 중 오류 발생: {str(e)}"

def get_running_guide(temp, humidity):
    """현재 기온과 습도를 기반으로 체감 온도를 계산하여 러닝 가이드를 제안합니다."""
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
    """환율 정보(바트화, 달러화) 및 미국 나스닥 종합 지수 마감을 가져옵니다."""
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
            f"  • 점심 (13시 전후): {pop_afternoon}\n"
            f"  • 저녁 (19시 전후): {pop_evening}\n\n"
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

    current_time = get_current_time()
    training_info = get_today_training()
    weather_info, umbrella_alert = get_hyper_local_weather(WEATHER_API_KEY, LAT, LON, WEATHER_NAME)
    air_info = get_air_quality(WEATHER_API_KEY, LAT, LON)
    finance_info = get_financial_snapshots()
    
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
