import os
import re
import json
import time
import datetime
import requests
import subprocess
from pydantic import BaseModel
from typing import List, Optional
import click

# Pydantic 모델 정의(트리 구조임!)
# VulnerabilityReport
# ├── VulnerabilityItem
# │   ├── VulnerabilityExtra
# │   │   ├── VulnerabilityMeta

# 취약점 분류/정보/레퍼런스 메타데이터 서브트리
class VulnerabilityMeta(BaseModel):
    vulnerability_class: Optional[List[str]] = []
    cwe: Optional[List[str]] = []
    references: Optional[List[str]] = []
# 메시지/심각도/메타데이터(VulnerabilityMeta)
class VulnerabilityExtra(BaseModel):
    message: Optional[str] = ""
    severity: Optional[str] = "UNKNOWN"
    metadata: Optional[VulnerabilityMeta] = VulnerabilityMeta()
# 파일 경로/시작위치, 종료위치(dict)/VulnerabilityExtra
class VulnerabilityItem(BaseModel):
    path: Optional[str] = "Unknown"
    start: Optional[dict] = {}
    end: Optional[dict] = {}
    extra: Optional[VulnerabilityExtra] = VulnerabilityExtra()
# 전체 취약점 리포트(최상위 디렉토리)
class VulnerabilityReport(BaseModel):
    results: List[VulnerabilityItem] = []

class PRProcedure:
    def __init__(self, base_branch: str, repo_name: str,
                 upstream_owner: str, save_dir: str, repo_url: str, token: str, user_name: str):
        self.branch_name = f'WHS_VULN_DETEC_{1}'
        self.base_branch = base_branch
        self.repo_name = repo_name
        self.upstream_owner = upstream_owner
        self.save_dir = save_dir
        self.repo_url = repo_url
        self.token = token
        self.user_name = user_name
        
    def post_init(self):
        if not self.user_name:
            raise RuntimeError
        if self.repo_url.startswith("https://github.com/"):
            parts = self.repo_url[len("https://github.com/"):].split('/')
            if len(parts) >= 2:
                # 원래 repo owner, repo_name 추출
                self.upstream_owner, self.repo_name = parts[:2]
            else:
                raise RuntimeError("Invalid repo URL")
        else:
            raise RuntimeError("Not a github.com URL")
    
    def mv_workdir(self, save_dir: str = None):
        # 0. clone한 디렉토리로 이동
        os.chdir(save_dir or self.save_dir)
    
    def check_branch_exists(self):
        # 1. 원격 브랜치 목록 조회
        branches = subprocess.check_output(['git', 'branch', '-r'], encoding='utf-8')
        # 2. WHS_VULN_DETEC_N 패턴 숫자 추출
        prefix = "origin/WHS_VULN_DETEC_"
        nums = [
            int(m.group(1))
            for m in re.finditer(rf"{re.escape(prefix)}(\d+)", branches)
        ]
        if nums:
            next_num = max(nums) + 1
        else:
            next_num = 1
        self.branch_name = f'WHS_VULN_DETEC_{next_num}'
        # 3. 브랜치 생성
        subprocess.run(['git', 'checkout', '-b', self.branch_name], check=True)
    
    def change_files(self):
        # 파일 생성 (임시) -> 원래는 수정된 파일(.js)가 들어가야함
        workflow_filename = 'test.txt'
        workflow_content = "Codes is Modified!!!"
        with open(workflow_filename, 'w', encoding='utf-8') as f:
            f.write(workflow_content)
        # 지금은 파일 하나만 추가하는데, 나중에는 '.'으로 바꿔야함
        subprocess.run(['git', 'add', workflow_filename], check=True)

        # 2. Semgrep 결과 로딩
        self.json_path = '../sast/before.json'
        with open(self.json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        subprocess.run(['git', 'commit', '-m', f"[Autofic] {len(data.get('results', []))} malicious code detected!!"], check=True)
        try:
            subprocess.run(['git', 'push', 'origin', self.branch_name], check=True)
            print(f"[SUCCESS] 브랜치 {self.branch_name}에 푸시 완료")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] 푸시 실패: {e}")
            return False
    
    def current_main_branch(self):
        # 3. base 브랜치 확인
        branches = subprocess.check_output(['git', 'branch', '-r'], encoding='utf-8')
        if f'origin/main' in branches:
            self.base_branch = 'main'
        elif f'origin/master' in branches:
            self.base_branch = 'master'
        else:
            self.base_branch = branches[0].split('/')[-1]
            
    def generate_pr(self):
        # 4. PR 생성
        print(f"[INFO] {self.user_name}/{self.repo_name}에 PR을 생성합니다. base branch: {self.base_branch}")
        pr_url = f"https://api.github.com/repos/{self.user_name}/{self.repo_name}/pulls"
        pr_body = self.generate_markdown(self.json_path)
        data_post = {
            "title": f"[Autofic] Security Patch {datetime.datetime.now().strftime('%Y-%m-%d')}",
            "head": f"{self.user_name}:{self.branch_name}",
            "base": self.base_branch,
            "body": pr_body
        }
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github+json"
        }
        pr_resp = requests.post(pr_url, json=data_post, headers=headers)
        if pr_resp.status_code in (201, 202):
            pr_json = pr_resp.json()
            print(f"[SUCCESS] {self.user_name}/{self.repo_name}에 PR 생성 완료! URL: {pr_json.get('html_url')}")
            time.sleep(0.05)
            return True
        else:
            print(f"[ERROR] PR 생성 실패: {pr_resp.status_code}\n{pr_resp.text}")
            return False
    
    def create_pr_to_upstream(self):
        """내 fork에 PR 올린 뒤 CI 성공하면, 자동으로 upstream(원본) PR을 생성"""
        # 1. 내 fork repo의 최신 PR 번호 찾기
        prs_url = f"https://api.github.com/repos/{self.user_name}/{self.repo_name}/pulls"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github+json"
        }
        prs_resp = requests.get(prs_url, headers=headers, params={"state": "open", "per_page": 1, "sort": "created", "direction": "desc"})
        prs = prs_resp.json()
        if not prs:
            return
        # 열려있는 PR이 있다면, 가장 최근 PR의 번호와 브랜치 이름을 가져옴  
        recent_pr = prs[0]
        pr_number = recent_pr["number"]
        pr_branch = recent_pr["head"]["ref"]

        # 2. 해당 PR의 Actions run_id 찾기
        runs_url = f"https://api.github.com/repos/{self.user_name}/{self.repo_name}/actions/runs"
        run_id = None
        for _ in range(60):  # 5분 대기
            runs_resp = requests.get(runs_url, headers=headers, params={"event": "pull_request", "per_page": 20})
            runs = runs_resp.json().get("workflow_runs", [])
            for run in runs:
                pr_list = run.get("pull_requests", [])
                if any(pr.get("number") == pr_number for pr in pr_list):
                    run_id = run["id"]
                    break
            if run_id:
                break
            time.sleep(5)
        else:
            return
        # 3. run이 completed & success 될 때까지 대기(.yml 파일에 대한 검사)
        run_url = f"https://api.github.com/repos/{self.user_name}/{self.repo_name}/actions/runs/{run_id}"
        for _ in range(120):  # 10분 대기
            run_resp = requests.get(run_url, headers=headers)
            run_info = run_resp.json()
            run_status = run_info.get("status")
            conclusion = run_info.get("conclusion")
            if run_status == "completed":
                # 상태가 completed이면, 성공 여부 확인
                if conclusion == "success":
                    break
                else:
                    return
            time.sleep(5)
        else:
            return
            
        # 4. ci.yml, pr_notify.yml에 대해서 문제가 발생하지 않으면 -> 원본 레포에 PR 생성
        pr_url = f"https://api.github.com/repos/{self.upstream_owner}/{self.repo_name}/pulls"
        pr_body = self.generate_markdown('../sast/before.json')
        data_post = {
            "title": f"[Autofic] Security Patch {datetime.datetime.now().strftime('%Y-%m-%d')}",
            "head": f"{self.user_name}:{pr_branch}",
            "base": self.base_branch,
            "body": pr_body
        }
        pr_resp = requests.post(pr_url, json=data_post, headers=headers)
        if pr_resp.status_code in (201, 202):
            pr_json = pr_resp.json()
        else:
            return
            
    def generate_markdown(self, json_path: str) -> str:
        with open(json_path, 'r', encoding='utf-8') as f:
            try:
                data = VulnerabilityReport.parse_raw(f.read())
            except Exception:
                f.seek(0)
                data_dict = json.load(f)
                data = VulnerabilityReport(**data_dict)
        md = []
        md.append("## 🛠️ Security Patch Summary\n")
        for idx, item in enumerate(data.results, 1):
            path = item.path.split('/')[-1] or "Unknown"
            start_line = item.start.get("line", "?") if item.start else "?"
            start_col = item.start.get("col", "?") if item.start else "?"
            end_col = item.end.get("col", "?") if item.end else "?"
            extra = item.extra or VulnerabilityExtra()
            message = extra.message or ""
            severity = extra.severity or "UNKNOWN"
            meta = extra.metadata or VulnerabilityMeta()
            vuln_type = ", ".join(meta.vulnerability_class or [])
            cwe = ", ".join(meta.cwe or [])
            ref_link = meta.references[0] if meta.references else ""
            md.append(f"### {idx}. {vuln_type or cwe or 'N/A'} Detected\n")
            md.append(f"- **File:** {path}")
            md.append(f"- **Line:** {start_line} (col {start_col}~{end_col})")
            md.append(f"- **Severity:** {severity}")
            md.append(f"- **Message:** {message}")
            if ref_link:
                md.append(f"- **Reference:** {ref_link}")
        md.append("\n### 💉 Fix Details\n")
        md.append("All vulnerable code paths have been refactored to use parameterized queries or input sanitization as recommended in the references above. Please refer to the diff for exact code changes.\n")
        md.append("---\n")
        return "\n".join(md)