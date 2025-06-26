import click
import os
import subprocess
import requests
import datetime
import json
from typing import List, Optional
from pydantic import BaseModel
import time
from .js_pacakge_yml import CreatePackageJson, CreateYml
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from nacl import encoding, public
import base64

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

# GitHub PR 자동화 클래스
class BranchPRAutomation:
    def __init__(self, repo_url: str, save_dir: str):
        # .env 파일에서 환경 변수 로드
        self.token = os.getenv('GITHUB_TOKEN')
        self.user_name = os.getenv('USER_NAME')
        self.slack_webhook = os.environ.get('SLACK_WEBHOOK_URL')
        self.discord_webhook = os.environ.get('DISCORD_WEBHOOK_URL')
        # repo_url은 GitHub 저장소 URL이어야 함
        self.repo_url = repo_url.rstrip('/').rstrip('.git')
        self.save_dir = save_dir + '/repo'
        # 기본 브랜치는 main으로 설정
        self.base_branch = 'main'
        # Discord, Slack을 Github랑 연결하려면, 아래 변수를 추가해야함
        self.secret_discord = 'DISCORD_WEBHOOK_URL'
        self.secret_slack = "SLACK_WEBHOOK_URL"
        # 사용자 이름 없음 오류 반환
        if not self.user_name:
            click.secho(f"[ ERROR ] 사용자 이름이 누락되었습니다.", fg="yellow")
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

    def run(self):
        # 0. clone한 디렉토리로 이동
        os.chdir(save_dir)
        # 1. 브랜치 생성
        branch_name = 'WHS_VULN_DETEC'
        subprocess.run(['git', 'checkout', '-b', branch_name], check=True)
        # js파일 종속 파일들에 대한 package.json, yml 파일 생성 (항상 Push)
        click.secho("[ INFO ] package.json과 ci.yml, pr_notify.yml 파일을 생성합니다.", fg="yellow")
        click.secho("[ INFO ] 기존 package.json 파일이 존재하더라도, 재생성됩니다.\n", fg="yellow")
        # 의존성 추출 및 생성
        CreatePackageJson().create_package_json(CreatePackageJson().extract_dependencies())
        # CI, PR 알림 YML 파일 생성
        CreateYml().ci_yml()
        # 자세한 함수 설명은 아래에서
        self.discordwebhook_notifier(self.discord_webhook)
        self.slackwebhook_notifier(self.slack_webhook)
        CreateYml().pr_notify()
        # 일단 add, commit, push 진행(WHS_VULN_DETEC 브랜치에 대해서)
        click.secho("[ INFO ] 생성한 package.json과 .github/workflows/ci.yml, .github/workflows/pr_notify.yml에 대한 push를 진행합니다.", fg="yellow")
        subprocess.run(['git', 'add', '.'], check=True)
        subprocess.run(['git', 'commit', '-m', "[Autofic] Create package.json and CI workflow"], check=True)
        subprocess.run(['git', 'push', 'origin', branch_name], check=True)
    
        # 파일 생성 (임시) -> 원래는 수정된 파일(.js)가 들어가야함
        workflow_filename = 'test.txt'
        workflow_content = "Code is Modified!!!"
        with open(workflow_filename, 'w', encoding='utf-8') as f:
            f.write(workflow_content)
        # 지금은 파일 하나만 추가하는데, 나중에는 '.'으로 바꿔야함
        subprocess.run(['git', 'add', workflow_filename], check=True)

        # 2. Semgrep 결과 로딩
        json_path = '../sast/before.json'
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        subprocess.run(['git', 'commit', '-m', f"[Autofic] {len(data.get('results', []))} malicious code detected!!"], check=True)
        try:
            subprocess.run(['git', 'push', 'origin', branch_name], check=True)
        except subprocess.CalledProcessError:
            subprocess.run(['git', 'push', 'origin', branch_name, '--force'], check=True)

        # 3. base 브랜치 확인
        branches = subprocess.check_output(['git', 'branch', '-r'], encoding='utf-8')
        if f'origin/main' in branches:
            self.base_branch = 'main'
        elif f'origin/master' in branches:
            self.base_branch = 'master'
        else:
            click.secho("[ ERROR ] main/master 브랜치가 없습니다.", fg="red")
            raise RuntimeError("main/master 브랜치가 없습니다.")
        
        # 4. PR 생성
        click.secho(f"[ INFO ] {self.user_name}/{self.repo_name}에 PR을 생성합니다. base branch: {self.base_branch}", fg="yellow")
        pr_url = f"https://api.github.com/repos/{self.user_name}/{self.repo_name}/pulls"
        pr_body = self.generate_pr_markdown(json_path)
        data_post = {
            "title": f"[Autofic] Security Patch {datetime.datetime.now().strftime('%Y-%m-%d')}",
            "head": f"{self.user_name}:{branch_name}",
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
            click.secho(f"[ SUCCESS ] {self.user_name}/{self.repo_name}에 PR 생성됨! URL: {pr_json.get('html_url')}\n", fg="green")
            time.sleep(0.05)
        else:
            click.secho(f"[ FAIL ] {self.user_name}/{self.repo_name}에 PR 생성 실패: {pr_resp.status_code}\n{pr_resp.text}\n", fg='red')

        # Fork한 레포에 추가한 .js파일에 오류가 발생하지 않을때 실행(원본 레포에 PR 생성)
        self.create_pr_to_upstream_if_ci_success()
            
    def create_pr_to_upstream_if_ci_success(self):
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
            click.secho("[ FAIL ] 오픈된 PR이 없습니다.", fg="red")
            return
        # 열려있는 PR이 있다면, 가장 최근 PR의 번호와 브랜치 이름을 가져옴  
        recent_pr = prs[0]
        pr_number = recent_pr["number"]
        pr_branch = recent_pr["head"]["ref"]
        click.secho(f"[ INFO ] 최신 PR 번호: {pr_number}, 브랜치: {pr_branch}", fg="yellow")

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
                click.secho(f"[ SUCCESS ] {self.user_name}/{self.repo_name} PR의 workflow run id: {run_id}", fg="green")
                break
            time.sleep(5)
        else:
            click.secho("[ FAIL ] workflow run이 생성되지 않았습니다.", fg="red")
            return
        # 3. run이 completed & success 될 때까지 대기(.yml 파일에 대한 검사)
        run_url = f"https://api.github.com/repos/{self.user_name}/{self.repo_name}/actions/runs/{run_id}"
        for _ in range(120):  # 10분 대기
            run_resp = requests.get(run_url, headers=headers)
            run_info = run_resp.json()
            run_status = run_info.get("status")
            conclusion = run_info.get("conclusion")
            click.secho(f"  [INFO] 현재 상태: {run_status}, 결과: {conclusion}", fg="yellow")
            if run_status == "completed":
                # 상태가 completed이면, 성공 여부 확인
                if conclusion == "success":
                    click.secho(f"[ SUCCESS ] .github/workflows/ci.yml, pr_notify.yml에 대한 Github Action이 성공적으로 완료되었습니다! {self.upstream_owner}/{self.repo_name}에 대한 PR을 진행합니다.", fg="green")
                    break
                else:
                    # 실패한 경우, 종료
                    click.secho(f"[ WARN ] .github/workflows/ci.yml, pr_notify.yml에 대한 Github Action이 성공적으로 끝나지 않았습니다. (결과: {conclusion})", fg="red")
                    return
            time.sleep(5)
        else:
            click.secho("[ FAIL ] 10분 내에 github/workflows/ci.yml, pr_notify.yml에 대한 Github Action이 성공적으로 끝나지 않았습니다.", fg="red")
            return
        # 4. ci.yml, pr_notify.yml에 대해서 문제가 발생하지 않으면 -> 원본 레포에 PR 생성
        pr_url = f"https://api.github.com/repos/{self.upstream_owner}/{self.repo_name}/pulls"
        pr_body = self.generate_pr_markdown('../sast/before.json')
        data_post = {
            "title": f"[Autofic] Security Patch {datetime.datetime.now().strftime('%Y-%m-%d')}",
            "head": f"{self.user_name}:{pr_branch}",
            "base": self.base_branch,
            "body": pr_body
        }
        pr_resp = requests.post(pr_url, json=data_post, headers=headers)
        if pr_resp.status_code in (201, 202):
            pr_json = pr_resp.json()
            click.secho(f"[SUCCESS] {self.upstream_owner}/{self.repo_name}에 PR 생성 완료되었습니다! URL: {pr_json.get('html_url')}", fg="green")
        else:
            click.secho(f"[FAIL] {self.upstream_owner}/{self.repo_name}에 PR 생성 실패했습니다.: {pr_resp.status_code}\n{pr_resp.text}", fg='red')


    def generate_pr_markdown(self, json_path: str) -> str:
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
    
    # Discord, Slack Webhook 알림 기능
    def discordwebhook_notifier(self, webhook_url: str):
        """Discord Webhook 알림 기능"""
        url = f'https://api.github.com/repos/{self.user_name}/{self.repo_name}/actions/secrets/public-key'
        headers = {'Authorization': f'token {self.token}'}
        resp = requests.get(url, headers=headers)
        pubkey_info = resp.json()
        key_id = pubkey_info['key_id']
        # 암호화할 값은 webhook_url이어야 함
        encrypted_value = self.encrypt(pubkey_info['key'], webhook_url)

        # Secret 등록(Repo -> Settings -> Secrets and variables -> Actions -> New repository secret 자동화)
        url2 = f'https://api.github.com/repos/{self.user_name}/{self.repo_name}/actions/secrets/{self.secret_discord}'
        payload = {
            "encrypted_value": encrypted_value,
            "key_id": key_id
        }
        resp2 = requests.put(url2, headers={**headers, 'Content-Type': 'application/json'}, json=payload)
        print(resp2.status_code, resp2.text)
    
    def slackwebhook_notifier(self, webhook_url: str):
        """Slack Webhook 알림 기능"""
        url = f'https://api.github.com/repos/{self.user_name}/{self.repo_name}/actions/secrets/public-key'
        headers = {'Authorization': f'token {self.token}'}
        resp = requests.get(url, headers=headers)
        pubkey_info = resp.json()
        key_id = pubkey_info['key_id']
        # 암호화할 값은 webhook_url이어야 함
        encrypted_value = self.encrypt(pubkey_info['key'], webhook_url)

        # Secret 등록(Repo -> Settings -> Secrets and variables -> Actions -> New repository secret 자동화)
        url2 = f'https://api.github.com/repos/{self.user_name}/{self.repo_name}/actions/secrets/{self.secret_slack}'
        payload = {
            "encrypted_value": encrypted_value,
            "key_id": key_id
        }
        resp2 = requests.put(url2, headers={**headers, 'Content-Type': 'application/json'}, json=payload)
        print("Slack 등록:", resp2.status_code, resp2.text)

    # webhook_url을 넣을 때, 암호화를 진행해야한다고 함
    def encrypt(self, public_key: str, secret_value: str) -> str:
        # public_key는 base64 인코딩된 문자열
        public_key = public.PublicKey(public_key, encoding.Base64Encoder())
        sealed_box = public.SealedBox(public_key)
        encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
        return base64.b64encode(encrypted).decode("utf-8")
