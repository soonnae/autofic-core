import requests
import os

class LogManager:
    def __init__(self):
        """
        서버 생성: https://autofic_log-server.com
        """
        self.api_base_url = (os.getenv('LOG_API_URL')).rstrip('/')

    def get_logs(self):
        """
        서버로 부터 log.json 가져오기 
        """
        url = f"{self.api_base_url}/log.json"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

    def save_logs(self, logs):
        """
        전체 log.json 덮어쓰기
        """
        url = f"{self.api_base_url}/log.json"
        response = requests.put(url, json=logs)
        response.raise_for_status()
        return response.json()

    def add_pr_log(self, date, repo, pr_number):
        """
        PR 기록
        """
        url = f"{self.api_base_url}/add_pr"
        payload = {
            "date": date,
            "repo": repo,
            "pr_number": pr_number
        }
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    def add_repo_status(self, name, url_, vulnerabilities):
        """
        repo 상태 기록
        """
        url = f"{self.api_base_url}/add_repo_status"
        payload = {
            "name": name,
            "url": url_,
            "vulnerabilities": vulnerabilities
        }
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
