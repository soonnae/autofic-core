import subprocess

class Ci_Automate:
    def __init__(self):
        self.REPO_URLS = [
            'https://github.com/inyeongjang/corner4'
        ]
    def run_autofic(self, repo_url):
        print(f"\n[RUN] {repo_url}")
        cmd = [
            'python', '-m', 'autofic_core.cli',
            '--repo', repo_url,
            '--save-dir', 'downloaded_folder',
            '--sast',
            '--rule', 'p/javascript'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return

    def main(self):
        for repo_url in self.REPO_URLS:
            try:
                self.run_autofic(repo_url)
            except Exception as e:
                print(f"[ERROR] {repo_url}: {e}")

if __name__ == "__main__":
    Ci_Automate().main()
