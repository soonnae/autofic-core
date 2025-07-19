import os
import requests
from dotenv import load_dotenv

load_dotenv()

log_url = os.getenv("LOG_API_URL")
token = os.getenv("GITHUB_TOKEN")

class GitHubChecker:
    def __init__(self, token):
        self.token = token

    def is_approved(self, owner, repo, pr_number):
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github+json"
        }
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            return resp.json().get("merged", False)
        return False

if __name__ == "__main__":
    log_data = requests.get(f"{log_url}/log.json").json()
    checker = GitHubChecker(token)

    for pr in log_data.get("prs", []):
        if pr.get("approved") is True:
            continue
        pr_number = pr.get("pr_number")
        owner = pr.get("owner")
        repo = pr.get("repo")

        print(f"[INFO] Checking PR #{pr_number} for {owner}/{repo}...")

        if checker.is_approved(owner, repo, pr_number):
            print(f"[✓] PR #{pr_number} is merged! Updating log...")
            requests.post(f"{log_url}/update_approval", json={
                "pr_number": pr_number,
                "approved": True
            })
