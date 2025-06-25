import os
import re
import json
import click

# 레포 안에 존재하는 JS 파일에서 의존성 패키지 추출 및 package.json 생성
class CreatePackageJson:
    def __init__(self, start_dir="."):
        self.start_dir = start_dir
        self.dependency_set = set()
        self.require_re = re.compile(r'require\(["\']([a-zA-Z0-9@_\-./@]+)["\']\)')
        self.import_re = re.compile(r'import\s+(?:[^"\']+\s+from\s+)?["\']([a-zA-Z0-9@_\-./@]+)["\']')
        self.NODE_BUILTINS = {
            'fs', 'path', 'http', 'https', 'url', 'os', 'querystring', 'stream',
            'events', 'buffer', 'util', 'zlib', 'crypto', 'child_process',
            'readline', 'net', 'tls', 'assert', 'dns', 'vm', 'module', 'tty'
        }
    # 의존성 패키지 추출
    def extract_dependencies(self):
        for root, _, files in os.walk(self.start_dir):
            for file in files:
                if file.endswith(".js"):
                    try:
                        with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                            content = f.read()
                            matches = self.require_re.findall(content) + self.import_re.findall(content)
                            for pkg in matches:
                                if pkg.startswith('.') or pkg.startswith('/'):
                                    continue
                                if pkg.startswith('@'):
                                    base_pkg = '/'.join(pkg.split('/')[:2])
                                else:
                                    base_pkg = pkg.split('/')[0]
                                if base_pkg not in self.NODE_BUILTINS:
                                    self.dependency_set.add(base_pkg)
                    except Exception as e:
                        click.secho(f"[ Fail ] {file} 파일 읽기 실패: {e}", fg="red")
        return sorted(self.dependency_set)

    # 추출된 의존성 패키지로 package.json 생성
    def create_package_json(self, dependencies, name="autogen-js-project"):
        # ⚠️ DB 드라이버 등 강제 추가
        force_include = [
            # DB
            "mysql2", "pg", "sqlite3", "mongodb", "redis",
            # Web/Backend
            "express", "koa", "hapi",
            # Auth/Security
            "jsonwebtoken", "bcrypt", "passport",
            # ORM/ODM
            "sequelize", "mongoose",
            # Test
            "jest", "mocha", "chai", "supertest",
            # Lint/Format
            "eslint", "prettier",
            # Build/Transpile
            "typescript", "babel-cli", "ts-node",
            # Middleware
            "multer", "cors", "body-parser", "morgan",
            # Templating
            "ejs", "pug",
            # Util
            "dotenv", "nodemon", "lodash"
        ]

        # 중복 제거해서 합치기
        all_dependencies = set(dependencies) | set(force_include)
        # package.json 기본 구조
        package = {
            "name": name,
            "version": "1.0.0",
            "description": "",
            "main": "index.js",
            "scripts": {
                "test": "for f in $(find . -type f -name '*.js'); do echo \"[TEST] $f\"; node $f || exit 1; done",
            },
            "dependencies": {pkg: "*" for pkg in sorted(all_dependencies)}
        }
        with open("package.json", "w", encoding="utf-8") as f:
            json.dump(package, f, indent=2)
        click.secho("[ SUCCESS ] package.json 생성 완료 (필수 패키지 자동 포함)", fg='green')

# GitHub Actions ci.yml, pr_notify.yml 파일 생성
class CreateYml:
    def __init__(self, start_dir="."):
        self.start_dir = start_dir
    # ci.yml 파일 생성
    def ci_yml(self):
        # .github/workflows 디렉토리 생성
        workflow_dir = os.path.join(self.start_dir, ".github", "workflows")
        os.makedirs(workflow_dir, exist_ok=True)
        ci_yml_path = os.path.join(workflow_dir, "ci.yml")
        ci_yml_content = """name: Node.js CI

on:
  push:
    branches: [main, master, WHS_VULN_DETEC]
  pull_request:
    branches: [main, master]

jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node-version: [14.x]

    steps:
      - uses: actions/checkout@v2
      - name: Use Node.js ${{ matrix.node-version }}
        uses: actions/setup-node@v1
        with:
          node-version: ${{ matrix.node-version }}
      - name: Install dependencies
        run: npm install
      - name: Build (if present)
        run: npm run build --if-present
      - name: Lint (ignore error)
        run: npm run lint || true

      - name: Test each JS file (excluding node_modules)
        run: |
          set +e
          LOG_ALL="test_results.log"
          LOG_FAIL="test_failed.log"
          > $LOG_ALL
          > $LOG_FAIL
          # node_modules 제외하고 .js 순회
          for f in $(find . -type f -name '*.js' -not -path "./node_modules/*"); do
            echo "===== TEST $f =====" | tee -a $LOG_ALL
            OUT=$(node "$f" 2>&1)
            CODE=$?
            echo "$OUT" >> $LOG_ALL
            if [ $CODE -ne 0 ]; then
              echo "[❌ FAIL] $f" | tee -a $LOG_FAIL
              echo "에러 로그:" >> $LOG_FAIL
              echo "$OUT" >> $LOG_FAIL
              echo "" >> $LOG_FAIL
            else
              echo "[✅ PASS] $f" | tee -a $LOG_ALL
            fi
          done
          echo "테스트 완료." | tee -a $LOG_ALL
          exit 0
        continue-on-error: true

      - name: Upload test logs
        uses: actions/upload-artifact@v4
        with:
          name: test-logs
          path: |
            test_results.log
            test_failed.log
"""
        with open(ci_yml_path, "w", encoding="utf-8") as f:
            f.write(ci_yml_content)
        click.secho(f"[ SUCCESS ] .github/workflows/ci.yml 파일이 생성되었습니다.", fg='green')
    # pr_notify.yml 파일 생성
    def pr_notify(self):
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
        click.secho(f"[ SUCCESS ] .github/workflows/pr_notify.yml 파일이 생성되었습니다.", fg='green')