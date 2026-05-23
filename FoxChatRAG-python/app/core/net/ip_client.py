import requests
from fastapi import Request
from loguru import logger


async def get_read_ip(request: Request):
    x_forwarded_for = request.headers.get("X-Forwarded-For")

    if x_forwarded_for:
        real_ip = x_forwarded_for.split(",")[0].strip()
        return real_ip

    return request.client.host


async def get_current_location(ip: str) -> dict:
    localtion = {
        "location":"未知",
        "lat": "0",
        "lon": "0",
    }

    if ip :
        ip_info_url = f"http://ip-api.com/json/{ip}?lang=zh-CN"
    else :
        ip_info_url = f"http://ip-api.com/json/?lang=zh-CN"


    res: dict = requests.get(ip_info_url, timeout=8).json()

    try:
        localtion["location"] = f"{res.get('country')} - {res.get('regionName')} - {res.get('city')}"
        localtion["lat"] = res.get("lat")
        localtion["lon"] = res.get("lon")
    except RuntimeError as e:
        return localtion

    logger.debug(f"获取到位置消息:{localtion}")

    return localtion

async def get_weather(lat: float, lon: float) -> dict:
    weather = {
        "temperature": "未知",
        "windspeed": "未知",
    }

    weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    logger.debug(f"天气请求发出：{weather_url}")
    weather_resp = requests.get(weather_url, timeout=5).json()

    try:
        current_weather = weather_resp.get("current_weather")

        weather["temperature"] = current_weather.get("temperature")
        weather["windspeed"] = current_weather.get("windspeed")
    except RuntimeError as e:
        return weather

    return weather