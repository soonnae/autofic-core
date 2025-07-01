import json
import os

class LogManager:
    def __init__(self, log_path=None):
        if log_path:
            self.log_path = os.path.abspath(log_path)
        else:
            self.log_path = os.path.join(os.path.dirname(__file__), 'log.json')

    def load(self):
        if os.path.exists(self.log_path):
            with open(self.log_path, "r", encoding="utf-8") as f:
                try:
                    logs = json.load(f)
                except json.JSONDecodeError:
                    logs = {}
        else:
            logs = {}

        logs.setdefault("prs", [])
        logs.setdefault("repos", [])
        return logs

    def save(self, logs):
        with open(self.log_path, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
        print("log.json 업데이트 완료")

    def add_pr_log(self, date, repo, pr_number):
        logs = self.load()
        logs["prs"] = [p for p in logs["prs"] if not (p["pr_number"] == pr_number and p["repo"] == repo)]
        logs["prs"].append({
            "date": date,
            "repo": repo,
            "pr_number": pr_number
        })
        self.save(logs)

    def add_repo_log(self, name, url, vulnerabilities):
        logs = self.load()
        logs["repos"] = [r for r in logs["repos"] if r["name"] != name]
        logs["repos"].append({
            "name": name,
            "url": url,
            "vulnerabilities": vulnerabilities
        })
        self.save(logs)
