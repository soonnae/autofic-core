import os
import subprocess
import click

# GitHub Actions ci.yml, pr_notify.yml 파일 생성
class AboutYml:
    def __init__(self, start_dir="."):
        self.start_dir = start_dir
        
 # pr_notify.yml 파일 생성
    def create_pr_yml(self):
        workflow_dir = os.path.join(self.start_dir, ".github", "workflows")
        os.makedirs(workflow_dir, exist_ok=True)

        pr_notify_yml_path = os.path.join(workflow_dir, "pr_notify.yml")
        pr_notify_yml_content = """name: PR Notifier

on:
  pull_request:
    types: [opened, reopened, closed]

jobs:
  notify:
    runs-on: ubuntu-latest
    steps:
      - name: Notify Discord
        env:
          DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
        run: |
          curl -H "Content-Type: application/json" \
          -d '{"content": "🔔 Pull Request [${{ github.event.pull_request.title }}](${{ github.event.pull_request.html_url }}) by ${{ github.event.pull_request.user.login }} - ${{ github.event.action }}"}' \
          $DISCORD_WEBHOOK_URL
      - name: Notify Slack
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
        run: |
          curl -H "Content-Type: application/json" \
          -d '{"text": ":bell: Pull Request <${{ github.event.pull_request.html_url }}|${{ github.event.pull_request.title }}> by ${{ github.event.pull_request.user.login }} - ${{ github.event.action }}"}' \
          $SLACK_WEBHOOK_URL
"""
        with open(pr_notify_yml_path, "w", encoding="utf-8") as f:
            f.write(pr_notify_yml_content)
            
    def push_pr_yml(self, user_name, repo_name, token, branch_name):
                # 일단 add, commit, push 진행(WHS_VULN_DETEC 브랜치에 대해서)
        repo_url = f'https://x-access-token:{token}@github.com/{user_name}/{repo_name}.git'
        subprocess.run(['git', 'remote', 'set-url', 'origin', repo_url], check=True)
        click.secho("[ INFO ] 생성한 .github/workflows/pr_notify.yml에 대한 push를 진행합니다.", fg="yellow")
        subprocess.run(['git', 'add', '.github/workflows/pr_notify.yml'], check=True)
        subprocess.run(['git', 'commit', '-m', "[Autofic] Create package.json and CI workflow"], check=True)
        subprocess.run(['git', 'push', 'origin', branch_name], check=True)