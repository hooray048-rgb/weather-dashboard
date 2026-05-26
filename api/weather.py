from flask import Blueprint, jsonify
import asyncio
import threading
from Test import run_all_locations_async, locations
from config import WeatherConfig
from datetime import datetime

weather_bp = Blueprint('weather', __name__, url_prefix='/api/weather')

_cache = {"data": None, "timestamp": None, "refreshing": False}
CACHE_TTL_SECONDS = 300  # 5분


def _do_refresh(service_key):
    try:
        results = asyncio.run(run_all_locations_async(service_key, locations))
        success_count = sum(1 for r in results if r.get("status") != "오류")
        if success_count >= len(results) // 2:
            _cache["data"] = results
            _cache["timestamp"] = datetime.now()
    finally:
        _cache["refreshing"] = False


def get_cached_results(service_key):
    now = datetime.now()
    is_fresh = (
        _cache["data"] is not None
        and _cache["timestamp"] is not None
        and (now - _cache["timestamp"]).total_seconds() < CACHE_TTL_SECONDS
    )
    if is_fresh:
        return _cache["data"]

    # 캐시가 없으면 동기 대기, 있지만 만료됐으면 백그라운드 갱신
    if _cache["data"] is None:
        _do_refresh(service_key)
        return _cache["data"] or []
    else:
        if not _cache["refreshing"]:
            _cache["refreshing"] = True
            threading.Thread(target=_do_refresh, args=(service_key,), daemon=True).start()
        return _cache["data"]

def format_weather_response(raw_data, location_info):
    """API 응답 데이터를 프론트엔드 형식으로 변환"""
    # 상태에서 조건 추론
    status = raw_data.get('status', '오류')
    alerts = raw_data.get('alerts', [])

    condition = '맑음'
    if any('눈' in alert for alert in alerts):
        condition = '눈'
    elif any('비' in alert or '강수' in alert for alert in alerts):
        condition = '비'
    elif any('구름' in alert for alert in alerts):
        condition = '흐림'

    temp = raw_data.get('max_temp')
    if temp is None:
        temp = 'N/A'
    else:
        temp = round((raw_data.get('max_temp', 0) + raw_data.get('min_temp', 0)) / 2, 1)

    return {
        "location": {
            "name": raw_data.get("name", "알 수 없는 거점"),
            "latitude": location_info.get('lat'),
            "longitude": location_info.get('lon')
        },
        "weather": {
            "temperature": temp,
            "condition": condition,
            "humidity": "N/A",
            "wind_speed": "N/A",
            "precipitation": 0
        },
        "timestamp": datetime.now().isoformat(),
        "raw_data": raw_data
    }

@weather_bp.route('/all', methods=['GET'])
def get_all_weather():
    """모든 물류 거점의 날씨 정보 조회"""
    service_key = WeatherConfig.SERVICE_KEY

    if not service_key:
        return jsonify({
            "error": "WEATHER_SERVICE_KEY 환경 변수가 설정되지 않았습니다."
        }), 500

    try:
        results = get_cached_results(service_key)

        # 각 결과를 프론트엔드 형식으로 변환
        formatted_results = []
        for raw_result in results:
            # location_name으로 원본 위치 정보 찾기
            location_info = next(
                (loc for loc in locations if loc['name'] == raw_result.get('name')),
                {'lat': 0, 'lon': 0}
            )
            formatted_result = format_weather_response(raw_result, location_info)
            formatted_results.append(formatted_result)

        return jsonify({
            "success": True,
            "data": formatted_results,
            "count": len(formatted_results)
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@weather_bp.route('/<location_name>', methods=['GET'])
def get_location_weather(location_name):
    """특정 거점의 날씨 정보 조회"""
    service_key = WeatherConfig.SERVICE_KEY

    if not service_key:
        return jsonify({
            "error": "WEATHER_SERVICE_KEY 환경 변수가 설정되지 않았습니다."
        }), 500

    # 거점 찾기
    location = next((loc for loc in locations if loc['name'] == location_name), None)
    if not location:
        return jsonify({
            "error": f"'{location_name}' 거점을 찾을 수 없습니다.",
            "available_locations": [loc['name'] for loc in locations]
        }), 404

    try:
        from Test import process_location
        import asyncio

        async def get_single_location():
            from asyncio import Semaphore
            semaphore = Semaphore(1)
            import httpx
            async with httpx.AsyncClient() as client:
                result = await process_location(client, semaphore, location, service_key)
            return result

        raw_result = asyncio.run(get_single_location())
        return jsonify({
            "success": True,
            "data": format_weather_response(raw_result, location)
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
