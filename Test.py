import math
import httpx
import asyncio
import time
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from config import WeatherConfig, EmailConfig

def convert_to_grid(lat, lon):
    # (기존 격자 변환 로직 동일)
    RE = 6371.00877  # 지구 반지름(km)
    GRID = 5.0       # 격자 간격(km)
    SLAT1 = 30.0     # 투영 위도1(degree)
    SLAT2 = 60.0     # 투영 위도2(degree)
    OLON = 126.0     # 기준점 경도(degree)
    OLAT = 38.0      # 기준점 위도(degree)
    XO = 43          # 기준점 X좌표(GRID)
    YO = 136         # 기준점 Y좌표(GRID)

    DEGRAD = math.pi / 180.0
    
    re = RE / GRID
    slat1 = SLAT1 * DEGRAD
    slat2 = SLAT2 * DEGRAD
    olon = OLON * DEGRAD
    olat = OLAT * DEGRAD

    sn = math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(math.pi * 0.25 + slat1 * 0.5)
    sf = math.pow(sf, sn) * math.cos(slat1) / sn
    ro = math.tan(math.pi * 0.25 + olat * 0.5)
    ro = re * sf / math.pow(ro, sn)

    ra = math.tan(math.pi * 0.25 + lat * DEGRAD * 0.5)
    ra = re * sf / math.pow(ra, sn)
    theta = lon * DEGRAD - olon
    if theta > math.pi: theta -= 2.0 * math.pi
    if theta < -math.pi: theta += 2.0 * math.pi
    theta *= sn
    
    nx = math.floor(ra * math.sin(theta) + XO + 0.5)
    ny = math.floor(ro - ra * math.cos(theta) + YO + 0.5)
    return nx, ny

# 물류 거점 리스트
locations = [
    {"name": "부천 물류", "lat": 37.5297, "lon": 126.7756},
    {"name": "파주 물류", "lat": 37.7692, "lon": 126.7941},
    {"name": "남양주 물류", "lat": 37.6573, "lon": 127.3381},
    {"name": "인천 물류", "lat": 37.3942, "lon": 126.7119},
    {"name": "진위 물류", "lat": 37.1161, "lon": 127.0852},
    {"name": "이천 물류", "lat": 37.2484, "lon": 127.4163},
    {"name": "군포 물류", "lat": 37.3309, "lon": 126.9372},
    {"name": "원주 물류", "lat": 37.3711, "lon": 127.8407},
    {"name": "강릉 물류", "lat": 37.7279, "lon": 128.8499},
    {"name": "대전 물류", "lat": 36.3087, "lon": 127.5853},
    {"name": "전주 물류", "lat": 35.9748, "lon": 127.1211},
    {"name": "광주 물류", "lat": 35.2071, "lon": 126.7831},
    {"name": "진천 물류", "lat": 36.8022, "lon": 127.5172},
    {"name": "아산 물류", "lat": 36.8150, "lon": 126.9827},
    {"name": "순천 물류", "lat": 34.8996, "lon": 127.5475},
    {"name": "목포 물류", "lat": 34.8343, "lon": 126.4643},
    {"name": "부산 물류", "lat": 35.3669, "lon": 129.0449},
    {"name": "창원 물류", "lat": 35.3531, "lon": 128.6360},
    {"name": "진주 물류", "lat": 35.0979, "lon": 128.0486},
    {"name": "제주 물류", "lat": 33.5144, "lon": 126.6758},
    {"name": "대구 물류", "lat": 35.7911, "lon": 128.4674},
    {"name": "경주 물류", "lat": 35.9369, "lon": 129.2511},
    {"name": "안동 물류", "lat": 36.5896, "lon": 128.6253},
]

def get_base_time():
    """현재 시각 기준으로 가장 최근에 발표된 예보 기준 시각 반환"""
    now = datetime.now()
    base_times = [2, 5, 8, 11, 14, 17, 20, 23]
    # 발표 후 10분 뒤부터 사용 가능
    current_hour = now.hour if now.minute >= 10 else now.hour - 1
    for t in reversed(base_times):
        if current_hour >= t:
            return f"{t:02d}00"
    # 자정 이전이면 전날 2300 사용
    return "2300"

async def get_tomorrow_forecast_async(client, service_key, lat, lon):
    nx, ny = convert_to_grid(lat, lon)
    now = datetime.now()
    base_time = get_base_time()
    # 23시 기준이면 전날 날짜 사용
    if base_time == "2300" and now.hour < 2:
        base_date = (now - timedelta(days=1)).strftime('%Y%m%d')
    else:
        base_date = now.strftime('%Y%m%d')
    tomorrow = (now + timedelta(days=1)).strftime('%Y%m%d')

    url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
    params = {
        'serviceKey': service_key,
        'pageNo': '1',
        'numOfRows': '1000',
        'dataType': 'JSON',
        'base_date': base_date,
        'base_time': base_time,
        'nx': nx,
        'ny': ny
    }

    try:
        response = await client.get(url, params=params, timeout=20.0)
        res_json = response.json()
        result_code = res_json.get('response', {}).get('header', {}).get('resultCode', '')
        if result_code != '00':
            result_msg = res_json.get('response', {}).get('header', {}).get('resultMsg', '알 수 없는 오류')
            raise ValueError(f"API 오류 [{result_code}]: {result_msg}")
        items = res_json['response']['body']['items']['item']
        tomorrow_data = [item for item in items if item['fcstDate'] == tomorrow]
        return tomorrow_data
    except Exception as e:
        print(f"예보 데이터 수집 오류 ({nx}, {ny}): {e}")
        raise
    
def analyze_tomorrow_safety(forecast_items):
    has_rain = False
    has_snow = False
    max_temp = -99.0
    min_temp = 99.0
    is_black_ice_risk = False
    time_data = {}

    for item in forecast_items:
        time = item['fcstTime']
        cat = item['category']
        raw_val = item['fcstValue']

        if raw_val in ['강수없음', '적설없음']:
            val = 0.0
        else:
            try:
                val = float(raw_val)
            except ValueError:
                val = 0.0
        
        if time not in time_data:
            time_data[time] = {}
        time_data[time][cat] = val

        if cat == 'TMP':
            max_temp = max(max_temp, val)
            min_temp = min(min_temp, val)
        elif cat == 'PTY':
            if val in [1, 2, 4]: has_rain = True
            if val in [2, 3]: has_snow = True
            if val > 0 and min_temp <= 0:
                is_black_ice_risk = True

    max_perceived = -99.0
    min_perceived = 99.0
    current_month = datetime.now().month

    for time, vals in time_data.items():
        T = vals.get('TMP', 0)
        RH = vals.get('REH', 0)
        V = vals.get('WSD', 0) * 3.6

        if 5 <= current_month <= 9:
            tw = T * math.atan(0.151977 * (RH + 8.313659)**0.5) \
                + math.atan(T + RH) - math.atan(RH - 1.676331) \
                + 0.00391838 * (RH**1.5) * math.atan(0.023101 * RH) - 4.686035
            p_temp = -0.2442 + 0.55399 * tw + 0.45535 * T - 0.0022 * (tw**2) + 0.0022 * tw * T + 0.5
            max_perceived = max(max_perceived, p_temp)
        elif current_month >= 11 or current_month <= 3:
            if T <= 0 and V >= 4.8:
                p_temp = 13.12 + 0.6215 * T - 11.37 * (V**0.16) + 0.3965 * T * (V**0.16)
            else:
                p_temp = T
            min_perceived = min(min_perceived, p_temp)

    alerts = []
    status = "정상"
    
    if has_snow:
        alerts.append("❄️ [폭설 대비] 내일 눈 예보가 있습니다. 제설 도구를 점검하세요.")
        status = "주의"
    elif has_rain:
        alerts.append("☔ [우천 대비] 내일 비 예보가 있습니다. 침수 피해에 주의하세요.")
        status = "주의"
    
    if is_black_ice_risk:
        alerts.append("🧊 [빙판길 주의] 도로가 매우 미끄러울 것으로 예상됩니다.")
        status = "경고"
        
    if 5 <= current_month <= 9:
        if max_perceived >= 35:
            alerts.append(f"🔴 [폭염 경고] 체감온도 {max_perceived:.1f}도! 14~17시 옥외작업 중지 권고.")
            status = "경고"
        elif max_perceived >= 33:
            alerts.append(f"🟠 [폭염 주의] 체감온도 {max_perceived:.1f}도! 매 2시간마다 20분 이상 휴식.")
            status = "주의"
        elif max_perceived >= 31:
            alerts.append(f"🟡 [폭염 관심] 체감온도 {max_perceived:.1f}도! 물, 그늘, 휴식 준수.")
            status = "주의"
    elif current_month >= 11 or current_month <= 3:
        if min_temp <= -12 or min_perceived <= -15:
            alerts.append(f"🥶 [한파 대비] 내일 최저 {min_temp}도(체감 {min_perceived:.1f}도)의 강추위!")
            status = "주의"

    return {
        "status": status,
        "max_temp": round(max_temp, 1),
        "min_temp": round(min_temp, 1),
        "max_perceived": round(max_perceived, 1) if max_perceived > -90 else None,
        "min_perceived": round(min_perceived, 1) if min_perceived < 90 else None,
        "alerts": alerts
    }

def send_email_report(report_data, sender_email, app_password, receiver_email):
    """
    JSON 구조의 report_data를 텍스트로 변환하여 발송합니다.
    """
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    subject = f"📢 [전사 안전 통보] {tomorrow} 물류 거점 기상 예보"
    
    report_lines = [f"📅 [{tomorrow}] 전사 물류 거점 안전 예보 보고", "-" * 50]
    
    for item in report_data:
        report_lines.append(f"📍 {item['name']} [{item['status']}]")
        report_lines.append(f"   기온: {item['min_temp']}℃ ~ {item['max_temp']}℃")
        if item['max_perceived']: report_lines.append(f"   최고체감: {item['max_perceived']}℃")
        if item['min_perceived']: report_lines.append(f"   최저체감: {item['min_perceived']}℃")
        
        for alert in item['alerts']:
            report_lines.append(f"   ⚠️ {alert}")
        report_lines.append("-" * 50)

    full_report = "\n".join(report_lines)
    full_report += "\n\n본 메일은 시스템에 의해 자동 발송되었습니다."

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject
    message.attach(MIMEText(full_report, "plain"))
    
    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, app_password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        print("\n📧 보고서가 이메일로 발송되었습니다.")
    except Exception as e:
        print(f"\n❌ 이메일 발송 실패: {e}")

async def process_location(client, semaphore, loc, service_key):
    async with semaphore:
        await asyncio.sleep(0.5)
        print(f"📍 {loc['name']} 분석 중...")
        try:
            forecast = await get_tomorrow_forecast_async(client, service_key, loc['lat'], loc['lon'])
            if forecast:
                analysis = analyze_tomorrow_safety(forecast)
                analysis["name"] = loc['name']
                return analysis
            else:
                return {
                    "name": loc['name'],
                    "status": "오류",
                    "max_temp": None, "min_temp": None,
                    "max_perceived": None, "min_perceived": None,
                    "alerts": ["데이터 없음: 해당 시간대 예보 데이터가 존재하지 않습니다."]
                }
        except Exception as e:
            return {
                "name": loc['name'],
                "status": "오류",
                "max_temp": None, "min_temp": None,
                "max_perceived": None, "min_perceived": None,
                "alerts": [f"데이터 수집 실패: {str(e)}"]
            }

async def run_all_locations_async(service_key, locations):
    semaphore = asyncio.Semaphore(2)
    async with httpx.AsyncClient() as client:
        tasks = [process_location(client, semaphore, loc, service_key) for loc in locations]
        results = await asyncio.gather(*tasks)
    return results

if __name__ == "__main__":
    # --- 환경 변수에서 설정 로드 ---
    MY_SERVICE_KEY = WeatherConfig.SERVICE_KEY
    GMAIL_USER = EmailConfig.GMAIL_USER
    GMAIL_APP_PASSWORD = EmailConfig.GMAIL_APP_PASSWORD
    TEAMS_CHANNEL_EMAIL = EmailConfig.TEAMS_CHANNEL_EMAIL

    if not MY_SERVICE_KEY:
        print("❌ WEATHER_SERVICE_KEY 환경 변수가 설정되지 않았습니다.")
        exit(1)

    # --- 실행 ---
    results_json = asyncio.run(run_all_locations_async(MY_SERVICE_KEY, locations))

    # JSON 데이터 출력 확인 (웹 API에서 반환할 형태)
    import json
    print(json.dumps(results_json, indent=2, ensure_ascii=False))

    # 이메일 발송 (설정되어 있을 경우만)
    if GMAIL_USER and GMAIL_APP_PASSWORD and TEAMS_CHANNEL_EMAIL:
        send_email_report(results_json, GMAIL_USER, GMAIL_APP_PASSWORD, TEAMS_CHANNEL_EMAIL)
    else:
        print("\n⚠️ 이메일 설정이 완료되지 않았습니다.")

    print("\n모든 거점의 날씨 확인 및 분석 데이터 생성이 완료되었습니다.")