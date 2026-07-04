import os
import requests
import xml.etree.ElementTree as ET
import datetime
import urllib.parse  # 🔍 한글 검색어를 컴퓨터용 주소로 안전하게 변환하기 위해 추가했습니다.

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
            error_msg = res.get("message", "알 수 없는 오류")
            return f"❌ 날씨 오류 ({response.status_code}): {error_msg}\n(가입 직후라면 API 키 활성화에 최대 2시간이 걸립니다.)"
    except Exception as e:
        return f"❌ 날씨 시스템 예외 발생: {str(e)}"

def get_category_news(keyword, limit=5):
    """구글 뉴스에서 특정 키워드를 검색하여 상위 기사 5개를 가져옵니다."""
    # 한글 검색어가 깨지지 않도록 주소창 인코딩을 적용합니다.
    encoded_keyword = urllib.parse.quote(keyword)
    url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=ko&gl=KR&ceid=KR:ko"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        res = requests.get(url, headers=headers)
        root = ET.fromstring(res.content)
        items = root.findall(".//item")[:limit]
        
        news_list = []
        for i, item in enumerate(items, 1):
            title = item.find("title").text
            link = item.find("link").text
            news_list.append(f"{i}. <a href='{link}'>{title}</a>")
        return news_list
    except Exception as e:
        return [f"❌ 뉴스 로딩 오류 ({keyword}): {str(e)}"]

def get_all_news_briefing():
    """정치, 경제, 미국, 태국 뉴스 섹션을 하나로 합칩니다."""
    # 원하시는 키워드 리스트와 타이틀입니다.
    categories = {
        "🏛️ 정치 뉴스 TOP 5": "정치",
        "📈 경제 뉴스 TOP 5": "경제",
        "🇺🇸 미국 소식 TOP 5": "미국",
        "🇹🇭 태국 소식 TOP 5": "태국"
    }
    
    total_briefing = []
    for title, keyword in categories.items():
        news_items = get_category_news(keyword)
        # 각 카테고리 제목 아래에 5개의 기사를 줄바꿈으로 이어 붙입니다.
        section_text = f"<b>{title}</b>\n" + "\n".join(news_items)
        total_briefing.append(section_text)
        
    # 각 카테고리 사이를 두 칸씩 띄워서 구분해 줍니다.
    return "\n\n".join(total_briefing)

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
    CITY = os.environ.get("CITY", "Bangkok")

    # 데이터 수집 (새로운 뉴스 브리핑 함수 호출)
    current_time = get_current_time()
    weather_info = get_weather(WEATHER_API_KEY, CITY)
    news_briefing = get_all_news_briefing()
    
    # 메시지 조합 및 발송
    message = f"☀️ <b>Good Morning! 아침 브리핑</b> ☀️\n📅 <b>일시:</b> {current_time}\n\n{weather_info}\n\n{news_briefing}"
    send_telegram(TELEGRAM_TOKEN, CHAT_ID, message)
