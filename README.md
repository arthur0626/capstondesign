# Capstone Design Django Project

이 프로젝트는 Django를 기반으로 한 웹 애플리케이션입니다.

---

## 🔧 해결 방법 요약

### ✅ 1. 환경변수 변경 (PYTHONIOENCODING 설정)

Python이 한글 인코딩 관련 오류를 일으킬 경우, 콘솔 인코딩을 명시적으로 설정하여 문제를 회피할 수 있습니다.

CMD 또는 PowerShell에서 아래 명령을 먼저 입력하세요:

```bash
set PYTHONIOENCODING=utf-8
```

그 후 Django 서버를 실행합니다:

```bash
python manage.py runserver localhost:8000
```
### ✅ 2. 환경 변수 설정

이제 같은 터미널 세션 내에서 실행하는 모든 명령에 이 환경 변수가 적용됩니다. Replicate Python 클라이언트는 이 값을 자동으로 사용합니다.

```bash
set REPLICATE_API_TOKEN=여기에_당신의_API_토큰_입력
```

📂 프로젝트 구조
```bash
capstondesign/
│
├── capstondesign/       # Django 프로젝트 폴더
├── firstapp/            # 생성한 앱 폴더
├── manage.py            # Django 관리 명령어 진입점
├── db.sqlite3           # SQLite DB (로컬 테스트용)
├── .venv/               # Python 가상환경 폴더
└── README.md            # 이 설명 파일
```

⚙️ 개발 환경
* Python 3.12.x
* Django 4.x 이상
* SQLite (기본 DB)
* Windows 10/11

✨ 기타 팁

* 가상환경 생성 및 Django 설치는 다음 명령으로 진행하세요:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install django
```
