import click
import os
import shutil
import subprocess
import requests
import datetime
import json
from typing import List, Optional
from pydantic import BaseModel

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
    def __init__(self, repo_url: str, token: str):
        self.repo_url = repo_url
        self.token = token

    def run(self):
        # 1. Repo info 파싱
        repo_url = self.repo_url.rstrip('/').rstrip('.git')
        if repo_url.startswith("https://github.com/"):
            parts = repo_url[len("https://github.com/"):].split('/')
            if len(parts) >= 2:
                upstream_owner, name = parts[:2]
            else:
                raise RuntimeError("Invalid repo URL")
        else:
            raise RuntimeError("Not a github.com URL")

        my_username = os.getenv('USER_NAME')
        if not my_username:
            click.secho(f"[ ERROR ] 사용자 이름이 누락되었습니다.", fg="yellow")
            raise RuntimeError

        # 2. 기존 디렉토리 삭제
        if os.path.exists(name):
            shutil.rmtree(name)
        clone_url = f"https://github.com/{my_username}/{name}.git"
        subprocess.run(['git', 'clone', clone_url], check=True)
        os.chdir(name)

        # 3. 브랜치 생성
        branch_name = 'WHS_VULN_DETEC'
        subprocess.run(['git', 'checkout', '-b', branch_name], check=True)

        # 4. 파일 생성 (임시)
        workflow_filename = 'test.txt'
        workflow_content = "Code is Modified!!!"
        wf_dir = os.path.join('test')
        os.makedirs(wf_dir, exist_ok=True)
        wf_path = os.path.join(wf_dir, workflow_filename)
        with open(wf_path, 'w', encoding='utf-8') as f:
            f.write(workflow_content)

        subprocess.run(['git', 'add', wf_path], check=True)

        # 5. Semgrep JSON 로딩
        json_path = '../artifacts/semgrep/before.json'
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        subprocess.run(['git', 'commit', '-m', f"[Autofic] {len(data.get('results', []))} malicious code detected!!"], check=True)

        try:
            subprocess.run(['git', 'push', 'origin', branch_name], check=True)
        except subprocess.CalledProcessError:
            subprocess.run(['git', 'push', 'origin', branch_name, '--force'], check=True)

        # 6. base 브랜치 확인
        branches = subprocess.check_output(['git', 'branch', '-r'], encoding='utf-8')
        if f'origin/main' in branches:
            base_branch = 'main'
        elif f'origin/master' in branches:
            base_branch = 'master'
        else:
            click.secho("[ ERROR ] main/master 브랜치가 없습니다.", fg="red")
            raise RuntimeError("main/master 브랜치가 없습니다.")

        click.secho(f"[ INFO ] PR을 생성합니다. base branch: {base_branch}", fg="cyan")

        pr_url = f"https://api.github.com/repos/{upstream_owner}/{name}/pulls"
        pr_body = self.generate_pr_markdown(json_path)
        data_post = {
            "title": f"[Autofic] Security Patch {datetime.datetime.now().strftime('%Y-%m-%d')}",
            "head": f"{my_username}:{branch_name}",
            "base": base_branch,
            "body": pr_body
        }
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github+json"
        }
        pr_resp = requests.post(pr_url, json=data_post, headers=headers)
        if pr_resp.status_code in (201, 202):
            pr_json = pr_resp.json()
            click.secho(f"[SUCCESS] PR 생성됨! URL: {pr_json.get('html_url')}", fg="green")
        else:
            click.secho(f"[FAIL] PR 생성 실패: {pr_resp.status_code}\n{pr_resp.text}", fg='red')

        os.chdir('..')

    @staticmethod
    def generate_pr_markdown(json_path: str) -> str:
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
            path = item.path or "Unknown"
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