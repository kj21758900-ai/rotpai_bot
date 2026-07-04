import os
import requests
import datetime
import yfinance as yf

def get_current_time():
    """방콕 시간(UTC+7) 기준으로 현재 날짜와 시간을 한글 포맷으로 가져옵니다."""
    tz_local = datetime.timezone(datetime.timedelta(hours=7))
    now = datetime.datetime.now(tz_local)
    weekdays = ['월', '화', '수', '목', '금', '토', '일']
    weekday_kr = weekdays[now.weekday()]
    return now.strftime(f"%Y년 %m월 %d일 ({weekday_kr}) %H:%M")

def get_air_quality(api_key, lat, lon):
    """OpenWeatherMap 대기오염 API를 호출하여 현재 동네의 미세먼지(AQI) 상태를 가져옵니다."""
    url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={api_key.strip()}"
    try:
        res = requests.get(url).json()
        aqi = res['list'][0]['main']['aqi']
        # OpenWeatherMap AQI 기준: 1(좋음) ~ 5(매우나쁨)
        aqi_map = {
            1: "🟢 좋음 (야외 훈련 최적! 🏃‍♂️)",
            2: "🟡 보통 (무난한 대기질)",
            3: "🟠 민감군 주의 (마스크 착용 고려)",
            4: "🔴 나쁨 (야외 운동 자제 요망)",
            5: "💀 매우 나쁨 (외출을 삼가세요)"
        }
        return aqi_map.get(aqi, "⏳ 대기질 정보 확인 불가")
    except:
        return "⏳ 대기질 정보 확인 불가"

def get_financial_snapshot():
    """야후 파이낸스를 통해 전날 미국 나스닥 마감 지수와 현재 바트/원 환율을 가져옵니다."""
    try:
        # 1. 바트 -> 원화 환율 조회 (최근 2일 데이터를 가져와 변동폭 계산)
        thb_krw_ticker = yf.Ticker("THBKRW=X")
        thb_krw_hist = thb_krw_ticker.history(period="2d")
        current_rate = thb_krw_hist['Close'].iloc[-1]
        prev_rate = thb_krw_hist['Close'].iloc[-2]
        rate_change = current_rate - prev_rate
        rate_sign = "🔺" if rate_change > 0 else "🔻" if rate_change < 0 else "🔹"
        
        # 2. 미국 나스닥 종합지수 조회
        nasdaq_ticker = yf.Ticker("^IXIC")
        nasdaq_hist = nasdaq_ticker.history(period="2d")
        current_nasdaq = nasdaq_hist['Close'].iloc[-1]
        prev_nasdaq = nasdaq_hist['Close'].iloc[-2]
        nasdaq_change = current_nasdaq - prev_nasdaq
        nasdaq_pct = (nasdaq_change / prev_nasdaq) * 100
        nasdaq_sign = "🔺" if nasdaq_change > 0 else "🔻" if nasdaq_change < 0 else "🔹"

        fin_text = (
            f"💵 <b>바트/원 환율:</b> 1 THB = {current_rate:.2f}원 ({rate_sign} {abs(rate_change):.2f}원)\n"
            f"🇺🇸 <b>미국 나스닥 마감:</b> {current_nasdaq:,.2f} ({nasdaq_sign} {nasdaq_pct:.2f}%)"
        )
        return fin_text
    except Exception as e:
        return "⏳ 금융 데이터 로딩 지연 (주말 또는 서버 일시 오류)"

def get_hyper_local_weather(api_key, lat, lon, custom_name=None):
    """지정한 위도/경도 좌표 기반 초정밀 예보 및 우산 리마인더 기능을 수행합니다."""
    if not api_key:
        return "❌ 날씨 API 키가 설정되지 않았습니다.", ""
    
    url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key.strip()}&units=metric&lang=kr"
    try:
        response = requests.get(url)
        res = response.json()
        
        if response.status_code != 200:
            return f"❌ 날씨 오류 ({response.status_code})", ""
        
        forecast_list = res.get("list", [])[:8]
        if not forecast_list:
            return "❌ 예보 데이터를 파싱할 수 없습니다.", ""
        
        location_name = custom_name.strip() if custom_name and custom_name.strip() else res.get("city", {}).get("name", "내 위치")
        
        current_desc = forecast_list[0]["weather"][0]["description"]
        current_temp = forecast_list[0]["main"]["temp"]
        humidity = forecast_list[0]["main"]["humidity"]
        
        temps = [item["main"]["temp"] for item in forecast_list]
        max_temp = max(temps)
        min_temp = min(temps)
        
        timezone_offset = res["city"]["timezone"]
        pop_morning, pop_afternoon, pop_evening = "0%", "0%", "0%"
        max_pop = 0 # 오늘 하루 최고 강수확률 체크용
        
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

        # 💡 [기능 1] 우산 스마트 리마인더 조건문 (하루 중 비 올 확률이 60% 이상일 때 작동)
        umbrella_reminder = ""
        if max_pop >= 60:
            umbrella_reminder = "🚨 <b>[알림] 오늘 비 예보가 있습니다! 외출 시 우산을 꼭 챙기세요.</b>\n\n"

        weather_text = (
            f"📍 <b>{location_name} 날씨:</b> {current_desc}\n"
            f"🌡️ <b>기온:</b> {current_temp}°C (최고 <b>{max_temp}°C</b> / 最저 <b>{min_temp}°C</b>)\n"
            f"💧 <b>습도:</b> {humidity}%\n"
            f"🌧️ <b>시간대별 비 올 확률:</b>\n"
            f"  • 아침 (07시 전후): {pop_morning}\n"
            f"  • 점심 (13시 전후): {pop_afternoon}\n"
            f"  • 저녁 (19시 전후): {pop_evening}"
        )
        return weather_text, umbrella_reminder

    except Exception as e:
        return f"❌ 날씨 시스템 예외 발생: {str(e)}", ""

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
    # 환경변수 로드
    TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
    CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
    WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")
    
    LAT = os.environ.get("WEATHER_LAT", "13.7563")
    LON = os.environ.get("WEATHER_LON", "100.5018")
    WEATHER_NAME = os.environ.get("WEATHER_NAME")

    # 데이터 수집 및 연동
    current_time = get_current_time()
    weather_info, umbrella_alert = get_hyper_local_weather(WEATHER_API_KEY, LAT, LON, WEATHER_NAME)
    air_info = get_air_quality(WEATHER_API_KEY, LAT, LON)
    finance_info = get_financial_snapshot()
    
    # 📝 전체 메시지 조립
    message = (
        f"☀️ <b>Good Morning! 아침 브리핑</b> ☀️\n"
        f"📅 <b>일시:</b> {current_time}\n\n"
        f"{umbrella_alert}" # 비 올 확률 높을 때만 고개를 드는 알림창
        f"{weather_info}\n"
        f"😷 <b>대기질(미세먼지):</b> {air_info}\n\n"
        f"📊 <b>글로벌 금융 스냅샷</b>\n"
        f"{finance_info}"
    )
    
    send_telegram(TELEGRAM_TOKEN, CHAT_ID, message)
