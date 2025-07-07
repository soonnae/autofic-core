import requests
import json
from datetime import datetime, timedelta
import os

class DashboardBuilder:
    def __init__(self, api_url, dashboard_path=None):
        self.api_url = api_url.rstrip('/')
        base_dir = os.path.dirname(__file__)
        self.dashboard_path = os.path.abspath(
            dashboard_path or os.path.join(base_dir, 'dashboard_data.json')
        )

    def load_log_data(self):
        print(f"[INFO] Fetching log from {self.api_url}/log.json")
        response = requests.get(f"{self.api_url}/log.json")
        response.raise_for_status()
        return response.json()

    def build_dashboard_data(self, logs):
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)

        pr_daily = sum(1 for p in logs.get("prs", []) if p["date"] == str(today))
        pr_weekly = sum(1 for p in logs.get("prs", []) if datetime.fromisoformat(p["date"]).date() >= week_ago)
        pr_total = len(logs.get("prs", []))

        return {
            "prCount": {
                "total": pr_total,
                "daily": pr_daily,
                "weekly": pr_weekly
            },
            "repos": logs.get("repos", [])
        }

    def save_dashboard_data(self, dashboard_data):
        with open(self.dashboard_path, "w", encoding="utf-8") as f:
            json.dump(dashboard_data, f, ensure_ascii=False, indent=2)
        print(f"[INFO] dashboard_data.json 생성 완료 → {self.dashboard_path}")

    def run(self):
        try:
            logs = self.load_log_data()
            dashboard_data = self.build_dashboard_data(logs)
            self.save_dashboard_data(dashboard_data)
        except Exception as e:
            print(f"[ERROR] Dashboard generation failed: {e}")

if __name__ == "__main__":
    api_url = os.getenv("LOG_API_URL")
    builder = DashboardBuilder(api_url)
    builder.run()

