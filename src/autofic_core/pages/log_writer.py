# =============================================================================
# Copyright 2025 AutoFiC Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================

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

    def add_repo_status(self, name, repo_url, vulnerabilities):
        """
        repo 상태 기록
        """
        url = f"{self.api_base_url}/add_repo_status"
        payload = {
            "name": name,
            "repo_url": repo_url,
            "vulnerabilities": vulnerabilities
        }
        # "changes" , "sastTool", "rerun" 추가 필요
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
