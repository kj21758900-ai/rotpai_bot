import os
import requests
import xml.etree.ElementTree as ET
import datetime  # 📅 날짜와 시간을 계산하기 위해 추가된 모듈입니다.

def get_current_time():
    """방콕 시간(UTC+7) 기준으로 현재 날짜와 시간을 한글 포맷으로 가져옵니다."""
    # GitHub 서버는 기본적으로 영국 표준시(UTC)를 쓰기 때문에, 시차(+7시간)를 강제로 더해줍니다.
    # 만약 한국 시간으로 바꾸고 싶다면 아래의 hours=7을 hours=9로 변경하시면 됩니다.
    tz_local = datetime.timezone(datetime.timedelta(hours=7))
    now = datetime.datetime.now(tz_local)
    
    # 요일을 한글로 예쁘게 바꾸기 위한 리스트입니다.
    weekdays = ['월', '화', '수', '목', '금', '토', '일']
    weekday_kr = weekdays[now.weekday()]
    
    # 2026년 07월 05일 (일) 07:00 같은 형태로 글자를 만들어 줍니다.
    return now.strftime(f"%Y년 %m월 %d일 ({weekday_kr}) %H:%M")

def get_weather(api_key, city="Bangkok"):
    """OpenWeatherMap API를 호출하여 현재 날씨를 가져옵니다."""
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=kr"
    try:
        res = requests.get(url).json()
        if res.get("cod") == 200:
            weather_desc = res["weather"][0]["description"]
            temp = res["main"]["temp"]
            humidity = res["main"]["humidity"]
            return f"📍 <b>{city} 날씨</b>: {weather_desc}\n🌡️ 기온: {temp}°C | 💧 습도: {humidity}%"
        return "❌ 날씨 데이터를 불러오지 못했습니다. (도시명 또는 API 키 확인 필요)"
    except Exception as e:
        return f"❌ 날씨 로딩 오류: {str(e)}"

def get_news():
    """구글 뉴스 RSS 피드를 파싱하여 주요 뉴스 5개를 가져옵니다."""
    url = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
    try:
        res = requests.get(url)
        root = ET.fromstring(res.text)
        items = root.findall(".//item")[:5]
        
        news_list = []
        for i, item in enumerate(items, 1):
            title = item.find("title").text
            link = item.find("link").text
            news_list.append(f"{i}. <a href='{link}'>{title}</a>")
        return "📰 <b>주요 뉴스 브리핑</b>\n" + "\n\n".join(news_list)
    except Exception as e:
        return f"❌ 뉴스 로딩 오류: {str(e)}"

def send_telegram(token, chat_id, text):
    """결과 메시지를 HTML 포맷으로 텔레그램에 전송합니다."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    requests.post(url, json=payload)

if __name__ == "__main__":
    # 보안 요소를 시스템 환경변수(GitHub Secrets)로부터 안전하게 읽어옵니다.
    TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
    CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
    WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")
    CITY = os.environ.get("CITY", "Bangkok")

    # 1. 오늘 날짜/시간 생성
    current_time = get_current_time()
    
    # 2. 데이터 수집
    weather_info = get_weather(WEATHER_API_KEY, CITY)
    news_info = get_news()
    
    # 3. 메시지 조합 (제목 바로 밑에 📅 일시 정보를 추가했습니다.)
    message = f"☀️ <b>Good Morning! 아침 브리핑</b> ☀️\n📅 <b>일시:</b> {current_time}\n\n{weather_info}\n\n{news_info}"
    
    # 4. 텔레그램 발송
    send_telegram(TELEGRAM_TOKEN, CHAT_ID, message)
