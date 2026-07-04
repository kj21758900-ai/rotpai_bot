import os
import requests
import xml.etree.ElementTree as ET
import datetime

def get_current_time():
    """방콕 시간(UTC+7) 기준으로 현재 날짜와 시간을 한글 포맷으로 가져옵니다."""
    tz_local = datetime.timezone(datetime.timedelta(hours=7))
    now = datetime.datetime.now(tz_local)
    weekdays = ['월', '화', '수', '목', '금', '토', '일']
    weekday_kr = weekdays[now.weekday()]
    return now.strftime(f"%Y년 %m월 %d일 ({weekday_kr}) %H:%M")

def get_weather(api_key, city="Bangkok"):
    """OpenWeatherMap API를 호출하여 현재 날씨를 가져옵니다."""
    if not api_key:
        return "❌ 날씨 API 키가 설정되지 않았습니다. GitHub Secrets를 확인해주세요."
    
    # 앞뒤 공백을 제거하고 안전하게 URL을 생성합니다.
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city.strip()}&appid={api_key.strip()}&units=metric&lang=kr"
    try:
        response = requests.get(url)
        res = response.json()
        
        if response.status_code == 200:
            weather_desc = res["weather"][0]["description"]
            temp = res["main"]["temp"]
            humidity = res["main"]["humidity"]
            return f"📍 <b>{city} 날씨</b>: {weather_desc}\n🌡️ 기온: {temp}°C | 💧 습도: {humidity}%"
        else:
            # 💡 서버가 거절한 진짜 이유를 메시지에 출력합니다.
            error_msg = res.get("message", "알 수 없는 오류")
            return f"❌ 날씨 오류 ({response.status_code}): {error_msg}\n(가입 직후라면 API 키 활성화에 최대 2시간이 걸립니다.)"
    except Exception as e:
        return f"❌ 날씨 시스템 예외 발생: {str(e)}"

def get_news():
    """구글 뉴스 RSS 피드를 파싱하여 주요 뉴스 5개를 가져옵니다."""
    url = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
    
    # 🕵️‍♂️ 구글의 차단을 막기 위해 일반 크롬 브라우저인 것처럼 속이는 헤더를 추가합니다.
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        res = requests.get(url, headers=headers)
        
        # 💡 res.text 대신 res.content(바이트)를 사용하여 XML 파싱 오류를 원천 차단합니다.
        root = ET.fromstring(res.content)
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
    if not token or not chat_id:
        print("텔레그램 토큰 또는 ID가 비어있습니다.")
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
    CITY = os.environ.get("CITY", "Bangkok")

    # 데이터 생성 및 전송
    current_time = get_current_time()
    weather_info = get_weather(WEATHER_API_KEY, CITY)
    news_info = get_news()
    
    message = f"☀️ <b>Good Morning! 아침 브리핑</b> ☀️\n📅 <b>일시:</b> {current_time}\n\n{weather_info}\n\n{news_info}"
    send_telegram(TELEGRAM_TOKEN, CHAT_ID, message)
