from App import db
import uuid
from datetime import datetime, timezone

class Subscriber(db.Model):
    __tablename__ = "subscribers"

    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(32), unique=True, nullable=False)

    country = db.Column(db.String(2), nullable=False)
    postal_code = db.Column(db.String(20), nullable=False)

    location_name = db.Column(db.String(128), nullable=True)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)

    timezone = db.Column(db.String(64), nullable=True)
    last_daily_sent_local_date = db.Column(db.Date, nullable=True)

    is_active = db.Column(db.Boolean, default=True, nullable=False)

    unsubscribe_token = db.Column(
        db.String(64),
        unique=True,
        nullable=False,
        default=lambda: uuid.uuid4().hex
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    last_notified_at = db.Column(db.DateTime(timezone=True), nullable=True)
