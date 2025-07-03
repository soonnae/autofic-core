from flask import Flask, request, jsonify, send_file
import os
import json

app = Flask(__name__)

LOG_PATH = 'log.json'

# log.json 없으면 기본 생성
if not os.path.exists(LOG_PATH):
    with open(LOG_PATH, 'w') as f:
        json.dump({"prs": [], "repos": []}, f, indent=2)

def load_log():
    with open(LOG_PATH, encoding='utf-8') as f:
        return json.load(f)

def save_log(data):
    with open(LOG_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 클라이언트 전체 로그 가져옴
@app.route('/log.json', methods=['GET'])
def get_log():
    return send_file(LOG_PATH)

# 로그 전체 덮어씀
@app.route('/log.json', methods=['PUT'])
def put_log():
    data = request.get_json()
    save_log(data)
    return jsonify({"status": "ok"})

# 로그 초기화 
@app.route('/reset_log', methods=['POST'])
def reset_log():
    """
    로그 초기화 토큰 인증 
    token = request.headers.get('Authorization')
    if token != os.getenv('ADMIN_TOKEN'):
        return jsonify({"error": "Unauthorized"}), 401
    empty_log = {"prs": [], "repos": []}
    save_log(empty_log)
    return jsonify({"status": "reset"})
    """
    empty_log = {"prs": [], "repos": []}
    save_log(empty_log)
    return jsonify({"status": "reset"})

# PR 기록 추가 
@app.route('/add_pr', methods=['POST'])
def add_pr():
    new_pr = request.get_json()
    logs = load_log()
    if "prs" not in logs:
        logs["prs"] = []
    logs["prs"].append(new_pr)
    save_log(logs)
    return jsonify({"status": "added", "pr": new_pr})

# repo 상태 기록 추가
@app.route('/add_repo_status', methods=['POST'])
def add_repo_status():
    new_repo = request.get_json()
    logs = load_log()
    if "repos" not in logs:
        logs["repos"] = []
    # 동일 이름 repo 덮어쓰기
    logs["repos"] = [r for r in logs["repos"] if r["name"] != new_repo["name"]]
    logs["repos"].append(new_repo)
    save_log(logs)
    return jsonify({"status": "added", "repo": new_repo})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
