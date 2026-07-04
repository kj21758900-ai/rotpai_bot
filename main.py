import os
import requests
import xml.etree.ElementTree as ET

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
    # 🔒 보안 요소를 시스템 환경변수(GitHub Secrets)로부터 안전하게 읽어옵니다.
    TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
    CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
    WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")
    
    # 기본 도시 설정 (원하는 도시 영문명으로 변경 가능)
    CITY = os.environ.get("CITY", "Bangkok")

    # 정보 수집 및 전송
    weather_info = get_weather(WEATHER_API_KEY, CITY)
    news_info = get_news()
    
    message = f"☀️ <b>Good Morning! 아침 브리핑</b> ☀️\n\n{weather_info}\n\n{news_info}"
    send_telegram(TELEGRAM_TOKEN, CHAT_ID, message)
