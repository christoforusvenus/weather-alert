import os
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException


def send_sms(to: str, body: str) -> str:
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_FROM_NUMBER")

    if not sid or not token or not from_number:
        raise RuntimeError(
            "Twilio env missing: TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_FROM_NUMBER"
        )

    client = Client(sid, token)

    try:
        msg = client.messages.create(
            to=to,
            from_=from_number,
            body=body,
        )
        return msg.sid
    except TwilioRestException as e:
        # helpful error for trial / invalid number / permissions
        raise RuntimeError(f"Twilio failed: {e.msg} (code={e.code})") from e
