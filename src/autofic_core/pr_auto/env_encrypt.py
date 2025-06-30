import base64
import requests
from nacl import public, encoding

class EnvEncrypy:
    def __init__(self, user_name, repo_name, token):
        self.user_name = user_name
        self.repo_name = repo_name
        self.token = token
        
    # Webhook 시크릿 등록 기능
    def webhook_secret_notifier(self, secret_name: str, webhook_url: str):
        """GitHub Actions Secret에 Webhook 등록"""
        url = f'https://api.github.com/repos/{self.user_name}/{self.repo_name}/actions/secrets/public-key'
        headers = {'Authorization': f'token {self.token}'}
        resp = requests.get(url, headers=headers)
        pubkey_info = resp.json()

        # KeyError 방지 (이전 답변 참고)
        if 'key_id' not in pubkey_info or 'key' not in pubkey_info:
            print(f"[ERROR] Invalid public key info: {pubkey_info}")
            return

        key_id = pubkey_info['key_id']
        encrypted_value = self.encrypt(pubkey_info['key'], webhook_url)

        # Secret 등록
        url2 = f'https://api.github.com/repos/{self.user_name}/{self.repo_name}/actions/secrets/{secret_name}'
        payload = {
            "encrypted_value": encrypted_value,
            "key_id": key_id
        }
        resp2 = requests.put(url2, headers={**headers, 'Content-Type': 'application/json'}, json=payload)
        print(f"Secret 등록: {secret_name}, {resp2.status_code}, {resp2.text}")

    def encrypt(self, public_key: str, secret_value: str) -> str:
        public_key = public.PublicKey(public_key, encoding.Base64Encoder())
        sealed_box = public.SealedBox(public_key)
        encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
        return base64.b64encode(encrypted).decode("utf-8")