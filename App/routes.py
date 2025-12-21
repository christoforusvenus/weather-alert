from flask import Blueprint, request, render_template, jsonify
import os
import re
import uuid

import requests
from timezonefinder import TimezoneFinder

from App import db
from App.models import Subscriber
from App.weather_service import check_weather_and_build_sms
from App.send_alerts import send_alerts_job

main = Blueprint("main", __name__)


@main.route("/", methods=["GET"])
def home():
    return "Weather Alert API is running ✅", 200


def normalize_phone(phone: str) -> str:
    if not phone:
        return ""

    phone = re.sub(r"[^\d+]", "", phone)

    if not phone.startswith("+"):
        return ""

    return phone


def create_subscriber(phone: str, country: str, postal_code: str):
    phone = normalize_phone(phone)
    country = (country or "").strip().upper()
    postal_code = (postal_code or "").strip()

    if not phone:
        return (
            None,
            "Please enter phone number in international format, e.g. +49 1234 5678 90",
            400,
        )
    if not country or not postal_code:
        return None, "Missing required fields", 400

    existing = Subscriber.query.filter_by(phone=phone).first()
    if existing and existing.is_active:
        return None, "Phone number already subscribed", 409

    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return None, "OPENWEATHER_API_KEY is not set", 500

    # Geocoding via OpenWeather ZIP endpoint
    geo_url = "https://api.openweathermap.org/geo/1.0/zip"
    params = {"zip": f"{postal_code},{country}", "appid": api_key}

    try:
        geo_resp = requests.get(geo_url, params=params, timeout=10)
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()
    except requests.HTTPError:
        return None, "Invalid postal code or country code.", 400
    except requests.RequestException:
        return None, "Geocoding service unavailable. Please try again.", 502
    except ValueError:
        return None, "Geocoding returned invalid JSON.", 502

    lat = geo_data.get("lat")
    lon = geo_data.get("lon")
    location_name = geo_data.get("name")

    if lat is None or lon is None:
        return None, "Geocoding failed! (lat/lon) is missing", 400

    tf = TimezoneFinder()
    tz_name = tf.timezone_at(lat=float(lat), lng=float(lon))

    if existing and not existing.is_active:
        existing.country = country
        existing.postal_code = postal_code
        existing.location_name = location_name
        existing.lat = float(lat)
        existing.lon = float(lon)

        existing.timezone = tz_name
        existing.last_daily_sent_local_date = None

        existing.is_active = True
        existing.unsubscribe_token = uuid.uuid4().hex
        existing.last_notified_at = None

        db.session.commit()
        return existing, None, 200

    subscriber = Subscriber(
        phone=phone,
        country=country,
        postal_code=postal_code,
        location_name=location_name,
        lat=float(lat),
        lon=float(lon),
        timezone=tz_name,
        last_daily_sent_local_date=None,
    )

    db.session.add(subscriber)
    db.session.commit()
    return subscriber, None, 201


@main.route("/subscribe-form", methods=["GET", "POST"])
def subscribe_form():
    if request.method == "GET":
        return render_template("subscribe.html")

    phone = request.form.get("phone", "")
    country = request.form.get("country", "")
    postal_code = request.form.get("postal_code", "")

    sub, err, status = create_subscriber(phone, country, postal_code)
    if err or sub is None:
        return render_template("subscribe.html", error=err or "Subscribe failed"), status

    loc = sub.location_name or "your area"
    return render_template(
        "subscribe.html",
        success=(
            f"✅ Subscribed successfully! Your postal code is in {loc}. "
            "You will receive a daily alert at 06:00 (local time) if bad weather is expected."
        ),
    ), status


@main.route("/unsubscribe/<token>", methods=["GET"])
def unsubscribe(token):
    sub = Subscriber.query.filter_by(unsubscribe_token=token).first()

    if not sub:
        return render_template(
            "unsubscribe.html",
            error="Invalid or expired unsubscribe link.",
        ), 404

    if not sub.is_active:
        return render_template(
            "unsubscribe.html",
            info="You are already unsubscribed.",
        ), 200

    sub.is_active = False
    db.session.commit()

    return render_template(
        "unsubscribe.html",
        success=True,
        phone=sub.phone,
    ), 200


@main.route("/preview/<int:subscriber_id>", methods=["GET"])
def preview(subscriber_id):
    sub = Subscriber.query.get(subscriber_id)
    if not sub:
        return jsonify({"error": "Subscriber not found"}), 404

    sms_text = check_weather_and_build_sms(
        lat=sub.lat,
        lon=sub.lon,
        country=sub.country,
        postal_code=sub.postal_code,
    )

    return jsonify(
        {
            "subscriber_id": sub.id,
            "country": sub.country,
            "postal_code": sub.postal_code,
            "location_name": sub.location_name,
            "lat": sub.lat,
            "lon": sub.lon,
            "timezone": sub.timezone,
            "sms_preview": sms_text,
        }
    ), 200


@main.route("/admin/run-alerts", methods=["POST"])
def admin_run_alerts():
    token = request.headers.get("X-Admin-Token")
    admin_token = os.getenv("ADMIN_TOKEN")

    if not admin_token or token != admin_token:
        return jsonify({"error": "unauthorized"}), 401

    stats = send_alerts_job()
    return jsonify({"ok": True, "stats": stats}), 200
