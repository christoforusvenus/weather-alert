import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from App import db
from App.models import Subscriber
from App.weather_service import check_weather_and_build_sms
from App.sms_service import send_sms


WINDOW_MINUTES = int(os.getenv("SEND_WINDOW_MINUTES", "15"))
TARGET_HOUR = int(os.getenv("DAILY_SEND_HOUR_LOCAL", "6"))


def send_alerts_job(limit: int | None = None) -> dict:
    q = Subscriber.query.filter_by(is_active=True).order_by(Subscriber.id.asc())
    if limit:
        q = q.limit(limit)

    subs = q.all()

    stats = {"checked": 0, "alerted": 0, "skipped": 0, "errors": 0}
    now_utc = datetime.now(timezone.utc)

    base_url = os.getenv("BASE_URL", "http://127.0.0.1:5000")

    for s in subs:
        stats["checked"] += 1

        try:
            if not getattr(s, "timezone", None):
                stats["skipped"] += 1
                continue

            try:
                tz = ZoneInfo(s.timezone)
            except Exception:
                stats["skipped"] += 1
                continue

            now_local = now_utc.astimezone(tz)

            if not (
                now_local.hour == TARGET_HOUR
                and now_local.minute < WINDOW_MINUTES
            ):
                stats["skipped"] += 1
                continue

            today_local = now_local.date()
            if getattr(s, "last_daily_sent_local_date", None) == today_local:
                stats["skipped"] += 1
                continue

            sms_text = check_weather_and_build_sms(
                lat=s.lat,
                lon=s.lon,
                country=s.country,
                postal_code=s.postal_code,
            )

            if not sms_text:
                stats["skipped"] += 1
                continue

            unsubscribe_url = f"{base_url}/unsubscribe/{s.unsubscribe_token}"
            full_msg = sms_text + f"\n\nUnsubscribe: {unsubscribe_url}"

            msg_sid = send_sms(to=s.phone, body=full_msg)
            print(
                f"[SENT] id={s.id} phone={s.phone} tz={s.timezone} "
                f"local={now_local} sid={msg_sid}"
            )

            s.last_daily_sent_local_date = today_local
            s.last_notified_at = now_utc
            stats["alerted"] += 1

        except Exception as e:
            stats["errors"] += 1
            print(f"[ERROR] id={s.id} phone={s.phone} err={e}")

    db.session.commit()
    return stats
