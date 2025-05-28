import subprocess

def run_semgrep(repo_path: str, rule: str, output_json: str = "semgrep_output.json"):
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
        
        with open(output_json, 'w', encoding='utf-8') as f:
            f.write(completed.stdout)
        
        return output_json, completed.stderr, completed.returncode
    
    except subprocess.CalledProcessError as err:
        return err.stdout, err.stderr, err.returncode