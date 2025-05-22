# ⚙️ AutoFiC 

**LLM을 활용한 취약한 소스코드 수정 솔루션**

<br> 

## 🚀 개발 환경 세팅 

### 1. Python 설치
- [Python 공식 다운로드](https://www.python.org/downloads/)
- **Python 3.8 이상** 설치 권장
- 설치 시 "Add Python to PATH" 옵션 반드시 체크

### 2. Git 설치 및 레포지토리 클론
- [Git 다운로드](https://git-scm.com/downloads)
- 터미널/명령 프롬프트/PowerShell/터미널 앱에서:
    ```
    git clone https://github.com/AutoFiC/autofic-core.git
    cd autofic-core
    ```

### 3. 가상환경(venv) 생성 및 활성화

- Windows (CMD)
    ```
    python -m venv venv
    venv\Scripts\activate
    ```

-  Windows (PowerShell)
    ```
    python -m venv venv
    .\venv\Scripts\activate
    ```

- Windows (Git Bash)
    ```
    python -m venv venv
    source venv/Scripts/activate
    ```

- macOS / Linux (터미널)
    ```
    python3 -m venv venv
    source venv/bin/activate
    ```

> 가상환경이 활성화되면 프롬프트 앞에 `(venv)`가 표시됩니다.

### 4. pip 최신화 (권장) 
```
pip install --upgrade pip
```

### 5. 필수 라이브러리 및 개발 모드 설치
```
pip install -r requirements.txt
pip install -e . 
```

### 6. 환경변수 파일 준비
```
cp .env.example .env
``` 

> `.env` 파일에 본인의 GitHub 토큰, OpenAI API 키 등 필요한 값을 입력하세요.

<br> 

## ⚡ 실행 방법

### 1. CLI 직접 실행

```
python -m autofic_core.cli --repo https://github.com/AutoFiC/autofic-core.git
```

### 2. 명령어로 실행 (개발 모드 설치 후) 

```
autofic-core --repo https://github.com/AutoFiC/autofic-core.git
```

<br> 

## 🧪 테스트 방법

```
pytest tests/ 
``` 

- 모든 테스트가 **passed** 되면 정상 

<br> 

## 📁 주요 파일 설명

| 파일/폴더             | 설명                                      |
|-----------------------|-------------------------------------------|
| src/autofic_core/     | 핵심 기능 Python 소스코드                  |
| tests/                | 테스트 코드                                |
| requirements.txt      | 필수 라이브러리 목록                       |
| pyproject.toml        | 패키지/배포/엔트리포인트 설정              |
| .env.example          | 환경변수 템플릿 (실제 값은 .env에 입력)    |
| .gitignore            | Git에 올리지 않을 파일/폴더 목록           |
| LICENSE               | 오픈소스 라이선스(MIT)           |
| README.md             | 이 문서                                    |

<br> 

## 🤝 Git & GitHub 협업 가이드 

### 👥 협업 규칙

- **가상환경(venv)과 .env 파일은 Git에 올리지 마세요!**
- 기능 추가/수정은 반드시 브랜치 생성 후 Pull Request로 병합
- 코드 리뷰/테스트 통과 후 main 브랜치에 반영

### 1. 기능 개발 시작: 브랜치 생성하고 이동

```
git switch -c feature/내기능이름
```

**🌿 브랜치명 규칙**
- 브랜치명은 아래 형식을 권장합니다.
    - `feature/기능명` (새 기능)
    - `bugfix/이슈번호-설명` (버그 수정)
    - `docs/문서명` (문서)
    - `test/설명` (테스트)
- 예시:
    - `feature/github-api-integration`
    - `bugfix/34-filter-extension-error`
    - `docs/update-readme`

### 2. 코드 수정 → 변경사항 저장 (commit)

```
git add .
git commit -m "Add: GitHub API 연동 기능 추가"
```

**📝 커밋 메시지 규칙**
- 커밋 메시지는 아래 형식을 지켜주세요.
    - `Add: ...` (새 기능)
    - `Fix: ...` (버그 수정)
    - `Update: ...` (기존 코드/문서/설정 변경)
    - `Remove: ...` (삭제)
    - `Refactor: ...` (구조 개선)
    - `Docs: ...` (문서)
    - `Test: ...` (테스트)
    - `Chore: ...` (환경/설정)
- 예시:
    - `Add: SAST 실행 기능 구현`
    - `Fix: 파일 필터링 버그 수정`
    - `Docs: README 업데이트`

### 3. GitHub에 업로드 (push)

```
git push origin feature/github-api-integration
```

### 4. 다른 사람 코드와 충돌 방지 (pull)

```
git pull origin dev
```

> 💡 최신 dev 브랜치 내용을 내 브랜치에 반영

### 5. GitHub에서 Pull Request 만들기

- GitHub에서 Compare & pull request 버튼 클릭
- base는 dev, compare는 내 브랜치인지 확인
- 제목/설명 작성 후 Create pull request

### 6. 팀장이 Merge 완료 후 dev 최신화

```
git switch dev
git pull origin dev
``` 

> 💡 Merge가 끝났다면 dev 브랜치에서도 최신 상태를 유지해야 해요!

> 다음 기능 개발 시 1번부터터 반복합니다. 
