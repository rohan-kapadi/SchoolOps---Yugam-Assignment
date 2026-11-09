"""Weather and air quality tools connecting to Open-Meteo APIs."""

from datetime import date as dt_date, datetime
from typing import Any
import httpx

from agent_api.config import (
    AQI_MAX_FORECAST_DAYS,
    CACHE_TTL_AIR_QUALITY,
    CACHE_TTL_FORECAST,
    DEFAULT_HTTP_TIMEOUT,
    OPEN_METEO_AIR_QUALITY_URL,
    OPEN_METEO_FORECAST_URL,
)
from agent_api.tools.cache import ttl_cache


def _format_date(date_val: str | dt_date | datetime) -> tuple[str | None, str | None]:
    """Convert input date to YYYY-MM-DD string and validate.

    Returns (date_str, error_message).
    """
    if isinstance(date_val, (dt_date, datetime)):
        return date_val.strftime("%Y-%m-%d"), None

    if isinstance(date_val, str):
        clean = date_val.strip()
        try:
            parsed = dt_date.fromisoformat(clean)
            return parsed.strftime("%Y-%m-%d"), None
        except ValueError:
            return None, f"Invalid date format '{date_val}'. Expected YYYY-MM-DD."

    return None, f"Unsupported date type: {type(date_val).__name__}"


@ttl_cache(ttl_seconds=CACHE_TTL_FORECAST)
def get_forecast(
    lat: float,
    lon: float,
    date: str | dt_date,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Fetch daily and hourly weather forecast for a location and date.

    Returns max temp, rain probability max, rain sum, and hourly rain.
    """
    date_str, err = _format_date(date)
    if err or not date_str:
        return {"status": "data_unavailable", "reason": err or "Invalid date"}

    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,precipitation_probability_max,precipitation_sum",
        "hourly": "precipitation,precipitation_probability",
        "timezone": "auto",
        "start_date": date_str,
        "end_date": date_str,
    }

    try:
        if client is not None:
            resp = client.get(OPEN_METEO_FORECAST_URL, params=params, timeout=DEFAULT_HTTP_TIMEOUT)
            return _parse_forecast_response(resp, date_str, lat, lon)

        with httpx.Client(timeout=DEFAULT_HTTP_TIMEOUT) as default_client:
            resp = default_client.get(OPEN_METEO_FORECAST_URL, params=params)
            return _parse_forecast_response(resp, date_str, lat, lon)
    except httpx.TimeoutException as exc:
        return {"status": "data_unavailable", "reason": f"Weather API request timed out: {exc}"}
    except httpx.HTTPError as exc:
        return {"status": "data_unavailable", "reason": f"Weather API connection error: {exc}"}
    except Exception as exc:
        return {"status": "data_unavailable", "reason": f"Unexpected weather API error: {exc}"}


def _parse_forecast_response(
    resp: httpx.Response,
    date_str: str,
    lat: float,
    lon: float,
) -> dict[str, Any]:
    """Parse Open-Meteo forecast JSON response into normalized schema."""
    if resp.status_code != 200:
        reason = resp.text
        try:
            err_data = resp.json()
            if isinstance(err_data, dict) and "reason" in err_data:
                reason = err_data["reason"]
        except Exception:
            pass
        return {"status": "data_unavailable", "reason": f"Weather API returned HTTP {resp.status_code}: {reason}"}

    payload = resp.json()
    daily = payload.get("daily", {})
    times = daily.get("time", [])

    if not times or date_str not in times:
        return {"status": "data_unavailable", "reason": f"No forecast data available for {date_str}"}

    idx = times.index(date_str)
    temp_max = daily.get("temperature_2m_max", [None])[idx]
    rain_prob_max = daily.get("precipitation_probability_max", [None])[idx]
    rain_sum = daily.get("precipitation_sum", [None])[idx]

    hourly = payload.get("hourly", {})
    h_times = hourly.get("time", [])
    h_precip = hourly.get("precipitation", [])
    h_prob = hourly.get("precipitation_probability", [])

    hourly_rain = []
    for i, t in enumerate(h_times):
        if str(t).startswith(date_str):
            hourly_rain.append({
                "time": t,
                "precipitation": h_precip[i] if i < len(h_precip) else 0.0,
                "precipitation_probability": h_prob[i] if i < len(h_prob) else 0.0,
            })

    return {
        "status": "ok",
        "data": {
            "date": date_str,
            "latitude": lat,
            "longitude": lon,
            "temperature_2m_max": temp_max,
            "max_temp": temp_max,
            "precipitation_probability_max": rain_prob_max,
            "rain_probability_max": rain_prob_max,
            "precipitation_sum": rain_sum,
            "rain_sum": rain_sum,
            "hourly_rain": hourly_rain,
        },
    }


@ttl_cache(ttl_seconds=CACHE_TTL_AIR_QUALITY)
def get_air_quality(
    lat: float,
    lon: float,
    date: str | dt_date,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Fetch air quality metrics (US AQI and PM2.5) for a location and date.

    Only forecasts up to 7 days ahead. Dates beyond that return data_unavailable.
    """
    date_str, err = _format_date(date)
    if err or not date_str:
        return {"status": "data_unavailable", "reason": err or "Invalid date"}

    # Open-Meteo Air Quality forecasts only ~7 days in advance
    target_dt = dt_date.fromisoformat(date_str)
    today_dt = dt_date.today()
    delta_days = (target_dt - today_dt).days

    if delta_days > AQI_MAX_FORECAST_DAYS:
        return {
            "status": "data_unavailable",
            "reason": (
                f"Air quality forecast is unavailable for dates beyond {AQI_MAX_FORECAST_DAYS} days "
                f"(requested {date_str}, {delta_days} days ahead)"
            ),
        }

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "pm2_5,us_aqi",
        "timezone": "auto",
        "start_date": date_str,
        "end_date": date_str,
    }

    try:
        if client is not None:
            resp = client.get(OPEN_METEO_AIR_QUALITY_URL, params=params, timeout=DEFAULT_HTTP_TIMEOUT)
            return _parse_air_quality_response(resp, date_str, lat, lon)

        with httpx.Client(timeout=DEFAULT_HTTP_TIMEOUT) as default_client:
            resp = default_client.get(OPEN_METEO_AIR_QUALITY_URL, params=params)
            return _parse_air_quality_response(resp, date_str, lat, lon)
    except httpx.TimeoutException as exc:
        return {"status": "data_unavailable", "reason": f"Air Quality API request timed out: {exc}"}
    except httpx.HTTPError as exc:
        return {"status": "data_unavailable", "reason": f"Air Quality API connection error: {exc}"}
    except Exception as exc:
        return {"status": "data_unavailable", "reason": f"Unexpected air quality API error: {exc}"}


def _parse_air_quality_response(
    resp: httpx.Response,
    date_str: str,
    lat: float,
    lon: float,
) -> dict[str, Any]:
    """Parse Open-Meteo air quality response into peak AQI and PM2.5."""
    if resp.status_code != 200:
        reason = resp.text
        try:
            err_data = resp.json()
            if isinstance(err_data, dict) and "reason" in err_data:
                reason = err_data["reason"]
        except Exception:
            pass
        return {"status": "data_unavailable", "reason": f"Air Quality API returned HTTP {resp.status_code}: {reason}"}

    payload = resp.json()
    hourly = payload.get("hourly", {})
    aqi_values = [v for v in hourly.get("us_aqi", []) if v is not None]
    pm2_5_values = [v for v in hourly.get("pm2_5", []) if v is not None]

    if not aqi_values and not pm2_5_values:
        return {"status": "data_unavailable", "reason": f"No air quality measurements available for {date_str}"}

    us_aqi = max(aqi_values) if aqi_values else None
    pm2_5 = max(pm2_5_values) if pm2_5_values else None

    return {
        "status": "ok",
        "data": {
            "date": date_str,
            "latitude": lat,
            "longitude": lon,
            "us_aqi": us_aqi,
            "pm2_5": pm2_5,
        },
    }
