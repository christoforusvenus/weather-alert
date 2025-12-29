import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import requests

FORCE_SEND_ALERT = os.getenv("FORCE_SEND_ALERT", "false").lower() == "true"


FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"


def is_bad_weather(weather_id: int) -> bool:
    return (
        200 <= weather_id < 300  # Thunderstorm
        or 300 <= weather_id < 400  # Drizzle
        or 500 <= weather_id < 600  # Rain
        or 600 <= weather_id < 700  # Snow
    )


def normalize_type(weather_id: int) -> str:
    if 200 <= weather_id < 300:
        return "Thunderstorm"
    if 300 <= weather_id < 400:
        return "Drizzle"
    if 500 <= weather_id < 600:
        return "Rain"
    if 600 <= weather_id < 700:
        return "Snow"
    return "Other"


def fetch_forecast(lat: float, lon: float) -> dict:
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENWEATHER_API_KEY is not set")

    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric",
    }

    try:
        resp = requests.get(FORECAST_URL, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        raise RuntimeError(f"OpenWeather request failed: {e}") from e


def collect_bad_weather_times(forecast_data: dict, hours: int = 24) -> Dict[str, List[str]]:
    now_utc = datetime.now(timezone.utc)
    limit_utc = now_utc + timedelta(hours=hours)

    tz_offset_sec = int(forecast_data.get("city", {}).get("timezone", 0))

    events: Dict[str, List[str]] = defaultdict(list)

    for entry in forecast_data.get("list", []):
        dt_raw = entry.get("dt")
        if dt_raw is None:
            continue

        t_utc = datetime.fromtimestamp(int(dt_raw), tz=timezone.utc)
        if t_utc > limit_utc:
            break

        t_local = t_utc + timedelta(seconds=tz_offset_sec)
        hhmm = t_local.strftime("%H:%M")

        for w in entry.get("weather", []):
            wid = w.get("id")
            if wid is None:
                continue

            wid_int = int(wid)
            if is_bad_weather(wid_int):
                wtype = normalize_type(wid_int)
                if hhmm not in events[wtype]:
                    events[wtype].append(hhmm)

    for k in events:
        events[k].sort()

    return dict(events)


def _limit_times(times: List[str], max_items: int = 4) -> str:
    if len(times) <= max_items:
        return ", ".join(times)
    return ", ".join(times[:max_items]) + " (+more)"


def build_sms(country: str, postal_code: str, events: Dict[str, List[str]]) -> str:
    country = (country or "").upper().strip()

    labels = []
    if "Thunderstorm" in events:
        labels.append("Storm")
    if "Snow" in events:
        labels.append("Snow")
    if "Rain" in events:
        labels.append("Rain")
    if "Drizzle" in events:
        labels.append("Drizzle")

    if not labels:
        return (
            f"TEST ALERT ({country_norm}-{postal_code})\n"
            "Dummy message to test Twilio + scheduler + DB flow."
        )

    types = ", ".join(labels)
    return (
        f"⚠️ Weather alert ({country}-{postal_code})\n"
        f"{types} expected today.\n"
        "Be prepared."
    )



def check_weather_and_build_sms(
    lat: float,
    lon: float,
    country: str,
    postal_code: str,
    hours: int = 24,
) -> Optional[str]:

    # ✅ Dummy / testing mode: always send a test SMS (even if weather is fine)
    if FORCE_SEND_ALERT:
        country_norm = (country or "").upper().strip()
        return (
            f"🧪 TEST ALERT ({country_norm}-{postal_code})\n"
            f"This is a dummy message to test Twilio + scheduler + DB flow ✅"
        )

    forecast = fetch_forecast(lat, lon)
    events = collect_bad_weather_times(forecast, hours=hours)

    if not events:
        return None

    return build_sms(country, postal_code, events)

