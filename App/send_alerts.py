import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from App import db
from App.models import Subscriber
from App.weather_service import check_weather_and_build_sms
from App.sms_service import send_sms


def _env_bool(key: str, default: str = "false") -> bool:
    return os.getenv(key, default).strip().lower() == "true"


def _env_int(key: str, default: str) -> int:
    try:
        return int(os.getenv(key, default))
    except ValueError:
        return int(default)


def send_alerts_job(limit: int | None = None) -> dict:
    window_minutes = _env_int("SEND_WINDOW_MINUTES", "15")
    target_hour = _env_int("DAILY_SEND_HOUR_LOCAL", "6")
    max_sms_len = _env_int("MAX_SMS_LEN", "160")
    force_send = _env_bool("FORCE_SEND_ALERT", "false")

    base_url = os.getenv("BASE_URL", "").strip().rstrip("/")
    if not base_url:
        base_url = "http://127.0.0.1:5000"
    if "127.0.0.1" in base_url or "localhost" in base_url:
        print("[WARN] BASE_URL looks like localhost. Set BASE_URL in Render env.")

    q = Subscriber.query.filter_by(is_active=True).order_by(Subscriber.id.asc())
    if limit:
        q = q.limit(limit)
    subs = q.all()

    stats = {"checked": 0, "alerted": 0, "skipped": 0, "errors": 0}
    now_utc = datetime.now(timezone.utc)

    for s in subs:
        stats["checked"] += 1

        try:
            if not getattr(s, "timezone", None):
                stats["skipped"] += 1
                print(f"[SKIP] id={s.id} reason=no_timezone")
                continue

            try:
                tz = ZoneInfo(s.timezone)
            except Exception:
                stats["skipped"] += 1
                print(f"[SKIP] id={s.id} reason=bad_timezone tz={s.timezone}")
                continue

            now_local = now_utc.astimezone(tz)

            if not force_send:
                in_window = (now_local.hour == target_hour and now_local.minute < window_minutes)
                if not in_window:
                    stats["skipped"] += 1
                    continue

            today_local = now_local.date()
            if getattr(s, "last_daily_sent_local_date", None) == today_local:
                stats["skipped"] += 1
                print(f"[SKIP] id={s.id} reason=already_sent today={today_local}")
                continue

            sms_text = check_weather_and_build_sms(
                lat=s.lat,
                lon=s.lon,
                country=s.country,
                postal_code=s.postal_code,
            )

            if not sms_text:
                stats["skipped"] += 1
                print(f"[SKIP] id={s.id} reason=no_bad_weather")
                continue

            unsub_url = f"{base_url}/u/{s.unsubscribe_token}"
            full_msg = f"{sms_text}\n\nUnsubscribe: {unsub_url}"

            if len(full_msg) > max_sms_len:
                full_msg = full_msg[: max_sms_len - 3] + "..."

            msg_sid = send_sms(to=s.phone, body=full_msg)
            print(
                f"[SENT] id={s.id} phone={s.phone} tz={s.timezone} "
                f"local={now_local.isoformat()} sid={msg_sid}"
            )

            s.last_daily_sent_local_date = today_local
            s.last_notified_at = now_utc
            stats["alerted"] += 1

        except Exception as e:
            stats["errors"] += 1
            print(f"[ERROR] id={getattr(s,'id',None)} phone={getattr(s,'phone',None)} err={e}")

    db.session.commit()
    return stats
