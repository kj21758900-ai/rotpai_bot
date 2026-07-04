import os
import requests
import xml.etree.ElementTree as ET
import datetime
import urllib.parse

def get_current_time():
    """방콕 시간(UTC+7) 기준으로 현재 날짜와 시간을 한글 포맷으로 가져옵니다."""
    tz_local = datetime.timezone(datetime.timedelta(hours=7))
    now = datetime.datetime.now(tz_local)
    weekdays = ['월', '화', '수', '목', '금', '토', '일']
    weekday_kr = weekdays[now.weekday()]
    return now.strftime(f"%Y년 %m월 %d일 ({weekday_kr}) %H:%M")

def get_weather_forecast(api_key, city="Bangkok"):
    """3시간 단위 예보 API를 호출하여 최고/최저 기온 및 시간대별 강수확률을 가져옵니다."""
    if not api_key:
        return "❌ 날씨 API 키가 설정되지 않았습니다. GitHub Secrets를 확인해주세요."
    
    # 💡 5일/3시간 예보 엔드포인트(forecast)로 변경하여 더 풍부한 데이터를 가져옵니다.
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={city.strip()}&appid={api_key.strip()}&units=metric&lang=kr"
    try:
        response = requests.get(url)
        res = response.json()
        
        if response.status_code != 200:
            error_msg = res.get("message", "알 수 없는 오류")
            return f"❌ 날씨 오류 ({response.status_code}): {error_msg}"
        
        # 앞으로의 예보 목록 중 오늘 하루(다음 24시간인 상위 8개 데이터)를 추출합니다.
        forecast_list = res.get("list", [])[:8]
        if not forecast_list:
            return "❌ 예보 데이터를 파싱할 수 없습니다."
        
        # 1. 현재 상태 및 최고/최저 기온 계산
        current_desc = forecast_list[0]["weather"][0]["description"]
        current_temp = forecast_list[0]["main"]["temp"]
        humidity = forecast_list[0]["main"]["humidity"]
        
        temps = [item["main"]["temp"] for item in forecast_list]
        max_temp = max(temps)
        min_temp = min(temps)
        
        # 2. 도시 고유의 시차(Timezone) 정보를 가져와 현지 시간 기준으로 강수확률 분류
        timezone_offset = res["city"]["timezone"] # 초 단위 시차 (예: 방콕은 25200초)
        
        pop_morning = "0%"
        pop_afternoon = "0%"
        pop_evening = "0%"
        
        for item in forecast_list:
            # UTC 시간에 해당 도시의 시차를 더해 현지 시간 객체로 변환
            local_timestamp = item["dt"] + timezone_offset
            local_dt = datetime.datetime.fromtimestamp(local_timestamp, tz=datetime.timezone.utc)
            local_hour = local_dt.hour
            
            # pop 값은 0~1 사이로 들어오므로 100을 곱해 %로 만듭니다.
            pop_percent = f"{int(item.get('pop', 0) * 100)}%"
            
            # 현지 시간 기준 아침(6~9시), 점심(12~15시), 저녁(18~21시)과 매칭
            if 6 <= local_hour <= 9:
                pop_morning = pop_percent
            elif 12 <= local_hour <= 15:
                pop_afternoon = pop_percent
            elif 18 <= local_hour <= 21:
                pop_evening = pop_percent

        # 3. 텔레그램 메시지 포맷팅
        weather_text = (
            f"📍 <b>{city} 날씨:</b> {current_desc}\n"
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

def get_category_news(keyword, limit=5):
    """구글 뉴스에서 특정 키워드를 검색하여 상위 기사 5개를 가져옵니다."""
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
    categories = {
        "🏛️ 정치 뉴스 TOP 5": "정치",
        "📈 경제 뉴스 TOP 5": "경제",
        "🇺🇸 미국 소식 TOP 5": "미국",
        "🇹🇭 태국 소식 TOP 5": "태국"
    }
    total_briefing = []
    for title, keyword in categories.items():
        news_items = get_category_news(keyword)
        section_text = f"<b>{title}</b>\n" + "\n".join(news_items)
        total_briefing.append(section_text)
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

    # 데이터 수집
    current_time = get_current_time()
    weather_info = get_weather_forecast(WEATHER_API_KEY, CITY)
    news_briefing = get_all_news_briefing()
    
    # 메시지 조합 및 발송
    message = f"☀️ <b>Good Morning! 아침 브리핑</b> ☀️\n📅 <b>일시:</b> {current_time}\n\n{weather_info}\n\n{news_briefing}"
    send_telegram(TELEGRAM_TOKEN, CHAT_ID, message)
