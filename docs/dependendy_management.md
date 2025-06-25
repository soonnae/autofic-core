## 📦 pip 의존성 관리 가이드

### ✅ 가상환경 사용하기 (venv)

모든 작업은 가상환경 안에서 진행해주세요!
각자 다른 시스템 설정으로 인한 충돌을 방지할 수 있습니다.

### 📥 의존성 설치

```
pip install -r requirements.txt
```
> 🔁 프로젝트 클론 후 또는 .env 등 환경 구성 후에 꼭 실행하세요.

### 🆕 라이브러리 설치 시 주의

새 패키지를 설치했다면 requirements.txt에 반영해주세요. 

```
pip install some-library
pip freeze > requirements.txt
```

> ⚠️ `pip freeze > requirements.txt`는 현재 가상환경의 모든 패키지를 덮어씁니다.<br> 
>         새 패키지만 반영하려면 아래처럼 일부만 추출해서 추가하세요. 
```
pip freeze | grep some-library >> requirements.txt
```