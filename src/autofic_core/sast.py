import subprocess

def run_semgrep(repo_path: str, rule: str):
    cmd = [
        "semgrep",
        "--config", rule,
        "--json",
        "--include", "*.js", 
        "--include", "*.jsx", 
        "--include", "*.mjs",
        repo_path
    ]
    
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', check=True)
        return completed.stdout, completed.stderr, completed.returncode
    
    except subprocess.CalledProcessError as err:
        return err.stdout, err.stderr, err.returncode