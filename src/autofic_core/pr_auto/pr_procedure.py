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

"""Contains their functional aliases.
"""
import os
import re
import json
import time
import datetime
import requests
import subprocess
from typing import List, Optional
from collections import defaultdict
from autofic_core.sast.snippet import BaseSnippet
from autofic_core.sast.semgrep.preprocessor import SemgrepPreprocessor
from autofic_core.sast.codeql.preprocessor import CodeQLPreprocessor
from autofic_core.sast.snykcode.preprocessor import SnykCodePreprocessor

class PRProcedure:
    """
    Handles all modules required for the pull request workflow.
    
    Responsibilities include:
    - Branch management
    - File changes and commit operations
    - Pull request generation to both fork and upstream repositories
    - CI status monitoring and validation
    - Generating PR markdown summaries from vulnerability reports
    """

    def __init__(self, base_branch: str, repo_name: str,
                upstream_owner: str, save_dir: str, repo_url: str, token: str, user_name: str, json_path: str, tool: Optional[str] = None):
        """
        Initialize PRProcedure with repository and user configuration.

        :param base_branch: The default base branch for PRs (e.g., 'WHS_VULN_DETEC_1', 'WHS_VULN_DETEC_2')
        :param repo_name: The name of the repository
        :param upstream_owner: The original (upstream) repository owner
        :param save_dir: Local directory for repository operations
        :param repo_url: Repository URL
        :param token: GitHub authentication token
        :param user_name: GitHub username (forked owner)
        """
        self.branch_name = f'WHS_VULN_DETEC_{1}'
        self.base_branch = base_branch
        self.repo_name = repo_name
        self.upstream_owner = upstream_owner
        self.save_dir = save_dir
        self.repo_url = repo_url
        self.token = token
        self.user_name = user_name
        self.json_path = json_path
        self.tool = tool
        
    def post_init(self):
        """
        Post-initialization: Extracts the repo owner and name from the URL if needed.
        Raises RuntimeError for invalid configuration (if user_name not exist in .env).
        """
        if not self.user_name:
            raise RuntimeError
        if self.repo_url.startswith("https://github.com/"):
            parts = self.repo_url[len("https://github.com/"):].split('/')
            if len(parts) >= 2:
                # Extract original repo owner and name
                self.upstream_owner, self.repo_name = parts[:2]
            else:
                raise RuntimeError("Invalid repo URL")
        else:
            raise RuntimeError("Not a github.com URL")
    
    def mv_workdir(self, save_dir: str = None):
        """
        Move the working directory to the repository clone directory.
        """
        os.chdir(save_dir or self.save_dir)
    
    def check_branch_exists(self):
        """
        Checks for existing branches with 'WHS_VULN_DETEC_N' pattern, used by regular expression.
        Determines next available number, creates and checks out new branch.
        """
        branches = subprocess.check_output(['git', 'branch', '-r'], encoding='utf-8')
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
        subprocess.run(['git', 'checkout', '-b', self.branch_name], check=True)
        
    def change_files(self):
        """
        Stages all modified files and commits with a summary message based on vulnerability scan results.
        Pushes the branch to the forked repository.
        """
        with open('../sast/merged_snippets.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.vulnerabilities = len(data)
        
        # Stage all modified/created files except ignored ones
        subprocess.run(['git', 'add', '--all'], check=True)

        # Remove common directories from staging
        ignore_paths = [
            '.codeql-db', '.codeql-results', 'node_modules', '.github', 
            '.snyk', 'snyk_result.sarif.json', '.eslintcache', 'eslint_tmp_env', '.DS_Store'
        ]
        for path in ignore_paths:
            if os.path.exists(path):
                subprocess.run(['git', 'reset', '-q', path], check=False)
        
        commit_message = f"[Autofic] {self.vulnerabilities} malicious code detected!!"
        subprocess.run(['git', 'commit', '-m', commit_message], check=True)

        try:
            subprocess.run(['git', 'push', 'origin', self.branch_name], check=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def current_main_branch(self):
        """
        Determines the main branch name ('main', 'master', or other).
        Basic branch is almost both main and master.
        But if both branche not exist, specify first branch.
        """
        branches = subprocess.check_output(['git', 'branch', '-r'], encoding='utf-8')
        if f'origin/main' in branches:
            self.base_branch = 'main'
        elif f'origin/master' in branches:
            self.base_branch = 'master'
        else:
            self.base_branch = branches[0].split('/')[-1]
            
    def generate_pr(self) -> str:
        """
        Creates a pull request on the fork repository.
        Uses vulnerability scan results (by semgrep) to generate a detailed PR body.
        If llm_generator implemented, then pr_body will add llm_result.
        """
        print(f"[INFO] Creating PR on {self.user_name}/{self.repo_name}. base branch: {self.base_branch}")
        pr_url = f"https://api.github.com/repos/{self.user_name}/{self.repo_name}/pulls"
        if self.tool == "semgrep":
            snippets = SemgrepPreprocessor.preprocess(self.json_path)
        elif self.tool == "codeql":
            snippets = CodeQLPreprocessor.preprocess(self.json_path)
        elif self.tool == "snykcode":
            snippets = SnykCodePreprocessor.preprocess(self.json_path)
        else:
            raise ValueError(f"Unknown tool: {self.tool}")
        pr_body = self.generate_markdown(snippets)
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
            time.sleep(0.05)
            return True
        else:
            return False
    
    def create_pr(self):
        """
        After PR is opened on fork, waits for CI to pass and then automatically creates a PR to the upstream repository.
        """
        # Step 1. Find latest open PR on fork
        prs_url = f"https://api.github.com/repos/{self.user_name}/{self.repo_name}/pulls"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github+json"
        }
        prs_resp = requests.get(prs_url, headers=headers, params={"state": "open", "per_page": 1, "sort": "created", "direction": "desc"})
        prs = prs_resp.json()
        if not prs:
            return
        recent_pr = prs[0]
        pr_number = recent_pr["number"]
        self.pr_branch = recent_pr["head"]["ref"]

        # Step 2. Find Actions run_id for that PR
        runs_url = f"https://api.github.com/repos/{self.user_name}/{self.repo_name}/actions/runs"
        run_id = None
        for _ in range(60):  # Wait up to 5 minutes
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

        # Step 3. Wait until the workflow run completes successfully
        run_url = f"https://api.github.com/repos/{self.user_name}/{self.repo_name}/actions/runs/{run_id}"
        for _ in range(120):  # Wait up to 10 minutes
            run_resp = requests.get(run_url, headers=headers)
            run_info = run_resp.json()
            run_status = run_info.get("status")
            conclusion = run_info.get("conclusion") # This code block will judge whether pr to upstream repo
            if run_status == "completed":
                if conclusion == "success":
                    break
                else:
                    return
            time.sleep(5)
        else:
            return
        
        # Step 4. If all checks pass('success'), create PR to upstream/original repository
        pr_url = f"https://api.github.com/repos/{self.upstream_owner}/{self.repo_name}/pulls"
        if self.tool == "semgrep":
            snippets = SemgrepPreprocessor.preprocess(self.json_path)
        elif self.tool == "codeql":
            snippets = CodeQLPreprocessor.preprocess(self.json_path)
        elif self.tool == "snykcode":
            snippets = SnykCodePreprocessor.preprocess(self.json_path)
        pr_body = self.generate_markdown(snippets) 
        data_post = {
            "title": f"[Autofic] Security Patch {datetime.datetime.now().strftime('%Y-%m-%d')}",
            "head": f"{self.user_name}:{self.pr_branch}",
            "base": self.base_branch,
            "body": pr_body
        }
        pr_resp = requests.post(pr_url, json=data_post, headers=headers)
        if pr_resp.status_code in (201, 202):
            pr_json = pr_resp.json()
            return pr_number            
        else:
            return

    def generate_markdown(self, snippets: List[BaseSnippet]) -> str:
        def extract_fix_suggestion(md_path: str) -> str:
            """ Extracts the fix suggestion from a markdown file.
            Assumes the fix suggestion is under a section"""
            try:
                with open(md_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    pattern = r'3\.\s*\**개선\s*방안\**\s*:?[\n\r]+(.*?)(?=\n\s*\d+\.\s|\Z)'
                    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
                    if match:
                        return match.group(1).strip()
            except Exception:
                pass
            return "Fix suggestion not found."

        grouped_by_file = defaultdict(list)
        for item in snippets:
            filename = os.path.basename(item.path or "Unknown")
            grouped_by_file[filename].append(item)

        md = ["## 🛠️ Security Patch Summary\n"]
        if not grouped_by_file:
            md.append("No vulnerabilities detected. No changes made.\n")
            return "\n".join(md)

        file_idx = 1
        for filename, items in grouped_by_file.items():
            md.append(f"### 🗂️ {file_idx}. `{filename}`")
            min_line = min(item.start_line for item in items)
            max_line = max(item.end_line for item in items)
            file_lines = f"{min_line} ~ {max_line}"
            md.append(f"- #️⃣ **Lines**: {file_lines}")

            for vuln_idx, item in enumerate(items, 1):
                vuln = item.vulnerability_class[0] if item.vulnerability_class else "N/A"
                md.append(f"\n #### {file_idx}-{vuln_idx}. [Vulnerability] {vuln}")
                md.append(f"- 🛡️ Severity: {item.severity}")
                if item.cwe:
                    md.append(f"- 🔖 {', '.join(item.cwe)}")
                if item.references:
                    for ref in item.references:
                        md.append(f"- 🔗 Reference: {ref}")
                md.append(f"- ✍️ Message: {item.message.strip()}")

                for eachname in os.listdir('../llm'):
                    if filename in eachname and str(item.start_line) in eachname:
                        md.append(f"- **🤖 How to fix :**")
                        md_path = os.path.join('../llm', eachname)
                        fix_text = extract_fix_suggestion(md_path)
                        fix_lines = fix_text.strip().splitlines()
                        for line_fix in fix_lines:
                            line_fix = line_fix.strip()
                            if line_fix.startswith("-"):
                                md.append(f"  {line_fix}")
                            else:
                                md.append(f"  - {line_fix}")
                        break

            file_idx += 1

        md.append("\n### 💉 Fix Details\n")
        md.append("All vulnerable code paths have been refactored to use parameterized queries or input sanitization as recommended in the references above. Please refer to the diff for exact code changes.\n")
        md.append("---\n")
        return "\n".join(md)

    def generate_log_data(self, pr_number):
        today = datetime.date.today().isoformat()
        pr_creation_data = {
            "date": today,
            "repo": f"{self.user_name}/{self.repo_name}",
            "pr_number": pr_number,
        }
        repo_status_data = {
            "name": self.repo_name,
            "repo_url": f"https://github.com/{self.upstream_owner}/{self.repo_name}",
            "vulnerabilities": getattr(self, 'vulnerabilities', 0)
        }
        return pr_creation_data, repo_status_data    

    def contains_all(self, text, *keywords):
        """ Check if all keywords are present in the text."""
        return all(k in text for k in keywords)

