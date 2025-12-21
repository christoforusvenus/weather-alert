import os
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException


def send_sms(to: str, body: str) -> str:
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_FROM_NUMBER")

    if not account_sid or not auth_token or not from_number:
        raise RuntimeError(
            "Missing Twilio configuration "
            "(TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_FROM_NUMBER)"
        )

    client = Client(account_sid, auth_token)

    try:
        message = client.messages.create(
            to=to,
            from_=from_number,
            body=body,
        )
        return message.sid

    except TwilioRestException as e:
        raise RuntimeError(
            f"Twilio SMS failed (code={e.code}): {e.msg}"
        ) from e
