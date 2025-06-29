import subprocess
import os

REPO_URLS = [
    "https://github.com/markedjs/marked.git",
    "https://github.com/validatorjs/validator.js.git",
    "https://github.com/vercel/serve.git",
    "https://github.com/http-party/http-server.git",
    "https://github.com/expressjs/express.git",
]

def run_autofic(repo_url):
    print(f"\n[RUN] {repo_url}")
    cmd = [
        'python', '-m', 'autofic_core.cli',
        '--repo', repo_url,
        '--save-dir', 'downloaded_folder',
        '--sast',
        '--rule', 'p/javascript'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print("[STDOUT]", result.stdout)
    print("[STDERR]", result.stderr)
    if result.returncode != 0:
        print(f"[FAIL] {repo_url} (exit code {result.returncode})")

def main():
    for repo_url in REPO_URLS:
        try:
            run_autofic(repo_url)
        except Exception as e:
            print(f"[ERROR] {repo_url}: {e}")

if __name__ == "__main__":
    main()
