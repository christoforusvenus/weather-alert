from App import create_app
from App.send_alerts import send_alerts_job

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        stats = send_alerts_job()
        print(stats)
