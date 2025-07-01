import json
from datetime import datetime, timedelta
import os

class DashboardBuilder:
    def __init__(self, log_path=None, dashboard_path=None):
        base_dir = os.path.dirname(__file__)
        self.log_path = os.path.abspath(log_path or os.path.join(base_dir, 'log.json'))
        self.dashboard_path = os.path.abspath(dashboard_path or os.path.join(base_dir, 'dashboard_data.json'))

    def load_log_data(self):
        with open(self.log_path, encoding="utf-8") as f:
            return json.load(f)

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
        print(f"dashboard_data.json 생성 완료")

    def run(self):
        try:
            logs = self.load_log_data()
            dashboard_data = self.build_dashboard_data(logs)
            self.save_dashboard_data(dashboard_data)
        except Exception as e:
            print(f"[ERROR] Dashboard generation failed: {e}")

if __name__ == "__main__":
    builder = DashboardBuilder()
    builder.run()

