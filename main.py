import os
import requests
import datetime

def get_current_time():
    """방콕 시간(UTC+7) 기준으로 현재 날짜와 시간을 한글 포맷으로 가져옵니다."""
    tz_local = datetime.timezone(datetime.timedelta(hours=7))
    now = datetime.datetime.now(tz_local)
    weekdays = ['월', '화', '수', '목', '금', '토', '일']
    weekday_kr = weekdays[now.weekday()]
    return now.strftime(f"%Y년 %m월 %d일 ({weekday_kr}) %H:%M")

def get_hyper_local_weather(api_key, lat, lon, custom_name=None):
    """지정한 위도(lat)와 경도(lon) 좌표를 기반으로 초정밀 동네 예보를 가져옵니다."""
    if not api_key:
        return "❌ 날씨 API 키가 설정되지 않았습니다. GitHub Secrets를 확인해주세요."
    
    url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key.strip()}&units=metric&lang=kr"
    try:
        response = requests.get(url)
        res = response.json()
        
        if response.status_code != 200:
            error_msg = res.get("message", "알 수 없는 오류")
            return f"❌ 날씨 오류 ({response.status_code}): {error_msg}"
        
        forecast_list = res.get("list", [])[:8]
        if not forecast_list:
            return "❌ 예보 데이터를 파싱할 수 없습니다."
        
        # 💡 사용자가 지정한 이름이 있으면 그것을 쓰고, 없으면 API가 주는 이름을 씁니다.
        if custom_name and custom_name.strip():
            location_name = custom_name.strip()
        else:
            location_name = res.get("city", {}).get("name", "내 위치")
        
        # 현재 상태 및 최고/최저 기온
        current_desc = forecast_list[0]["weather"][0]["description"]
        current_temp = forecast_list[0]["main"]["temp"]
        humidity = forecast_list[0]["main"]["humidity"]
        
        temps = [item["main"]["temp"] for item in forecast_list]
        max_temp = max(temps)
        min_temp = min(temps)
        
        # 시간대별 강수확률 파싱
        timezone_offset = res["city"]["timezone"]
        pop_morning, pop_afternoon, pop_evening = "0%", "0%", "0%"
        
        for item in forecast_list:
            local_timestamp = item["dt"] + timezone_offset
            local_dt = datetime.datetime.fromtimestamp(local_timestamp, tz=datetime.timezone.utc)
            local_hour = local_dt.hour
            pop_percent = f"{int(item.get('pop', 0) * 100)}%"
            
            if 6 <= local_hour <= 9:
                pop_morning = pop_percent
            elif 12 <= local_hour <= 15:
                pop_afternoon = pop_percent
            elif 18 <= local_hour <= 21:
                pop_evening = pop_percent

        if current_desc == "실 비":
            current_desc = "이슬비(실비)"

        weather_text = (
            f"📍 <b>{location_name} 날씨:</b> {current_desc}\n"
            f"🌡️ <b>기온:</b> {current_temp}°C (최고 <b>{max_temp}°C</b> / 최저 <b>{min_temp}°C</b>)\n"
            f"💧 <b>습도:</b> {humidity}%\n"
            f"🌧️ <b>시간대별 비 올 확률:</b>\n"
            f"  • 아침 (07시 전후): {pop_morning}\n"
            f"  • 점심 (13시 전후): {pop_afternoon}\n"
            f"  • 저녁 (19시 전후): {pop_evening}"
        )
        return weather_text

    except Exception as e:
        return f"❌ 날씨 시스템 예외 발생: {str(e)}"

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
    # 💡 원하는 지역명을 설정할 수 있는 환경변수 추가
    WEATHER_NAME = os.environ.get("WEATHER_NAME")

    # 데이터 수집 및 발송
    current_time = get_current_time()
    weather_info = get_hyper_local_weather(WEATHER_API_KEY, LAT, LON, WEATHER_NAME)
    
    message = f"☀️ <b>Good Morning! 아침 브리핑</b> ☀️\n📅 <b>일시:</b> {current_time}\n\n{weather_info}"
    send_telegram(TELEGRAM_TOKEN, CHAT_ID, message)
