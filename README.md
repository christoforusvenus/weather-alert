# 🌦️ Weather Alert SMS Service

A production-style weather alert system that sends **daily SMS notifications** when bad weather is expected in a user’s area.

This project demonstrates backend engineering concepts such as **scheduled jobs, timezone-aware logic, idempotent processing**, external API integration, and deployment on free-tier infrastructure.

---

## 🚀 Features

- 📍 User subscription via simple web form (phone, country, postal code)
- 🌍 Automatic location & timezone detection
- ☁️ Weather forecast check for the next 24 hours
- ⚠️ SMS alerts only when **bad weather** is expected
- 🕕 Alerts sent **once per day at 06:00 local time**
- 🔁 **Idempotent delivery** (no duplicate SMS per day)
- ❌ One-click unsubscribe via secure token
- ⏰ Triggered by an external cron scheduler
- 📦 Deployed on **Render (Web Service + PostgreSQL)**

---

## ⚠️ Bad Weather Criteria

An SMS alert is sent if the forecast includes any of the following conditions within the next 24 hours:

- Thunderstorm
- Snow
- Rain
- Drizzle

Weather conditions are classified using **OpenWeather condition codes** (2xx–6xx).

---

## 🧠 How the System Works

1. User subscribes via `/subscribe-form`
2. Postal code is resolved to latitude & longitude using OpenWeather Geocoding API
3. User timezone is detected automatically
4. An external cron job triggers the backend every 10 minutes
5. At **06:00 local time**, the system:
   - Fetches the weather forecast
   - Checks for bad weather
   - Sends **one SMS per user per day**
6. Users can unsubscribe at any time using a secure link in the SMS

---

## 🔁 Idempotency

The system is **idempotent by design**:

- Each subscriber stores `last_daily_sent_local_date`
- Even though the cron job runs multiple times per day,
  **each user receives at most one SMS per local day**

This prevents duplicate notifications and unnecessary SMS costs.

---

## 🛠️ Tech Stack

- **Backend:** Python, Flask
- **Database:** PostgreSQL (SQLAlchemy)
- **Weather API:** OpenWeather API
- **SMS Provider:** Twilio
- **Scheduler:** cron-job.org
- **Deployment:** Render
- **Timezone Detection:** timezonefinder

---

## 🔔 Twilio Trial Limitation

This project uses **Twilio SMS (Trial Account)**.

Because of Twilio trial restrictions:

- SMS messages can **only be sent to verified phone numbers**
- Messages to unverified or random public numbers are **blocked**
- Each SMS includes the default **"Sent from your Twilio trial account"** prefix
- SMS length is intentionally limited to avoid multi-segment trial errors

To send SMS to any phone number without restrictions, a **paid Twilio account** is required.

---

## 🗄️ Database Notes (Important)

This project uses a **free PostgreSQL instance on Render**.

⚠️ **Expiration Notice**  
The database instance will **expire on January 20, 2026**.

After this date:
- The database will be deleted automatically
- All subscriber data will be lost
- The application itself will continue to run

### Recovery Options
- Upgrade the database to a paid plan on Render  
- Create a new PostgreSQL instance and update `DATABASE_URL`
- Restart the app — tables will be recreated automatically

The system is designed to recover cleanly after a database reset.

---

## 🔐 Environment Variables

Example configuration (`.env.example`):

```env
DATABASE_URL=

OPENWEATHER_API_KEY=

TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=

ADMIN_TOKEN=
BASE_URL=https://your-app.onrender.com

DAILY_SEND_HOUR_LOCAL=6
SEND_WINDOW_MINUTES=15
MAX_SMS_LEN=160
FORCE_SEND_ALERT=false
