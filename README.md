# 🇰🇷 정부지원사업 텔레그램 알림 봇 (Korea Startup Bot)

이 봇은 기업마당(Bizinfo)과 K-Startup의 공고 정보를 수집하여 사용자에게 맞춤형 알림을 제공하고, AI(OpenAI)를 활용해 공고 내용을 요약해주는 텔레그램 챗봇입니다.

## 주요 기능

1.  **공고 검색**: 키워드 기반으로 최신 지원사업 공고를 검색합니다.
2.  **조건 필터링**: 지역, 분야, 대상 등 원하는 조건을 설정할 수 있습니다.
3.  **AI 공고 요약**: OpenAI GPT-4o-mini 모델을 사용하여 복잡한 공고 내용을 3줄로 요약해줍니다.
4.  **자동 알림**: 1시간마다 새로운 공고를 체크하여 사용자가 설정한 조건에 맞는 공고가 올라오면 푸시 알림을 보냅니다.
5.  **사용자 친화적 UX**: 인라인 키보드 버튼을 활용하여 간편하게 조작할 수 있습니다.

## 기술 스택

*   **Language**: Python 3.11+
*   **Library**: `python-telegram-bot`, `requests`, `openai`, `apscheduler`
*   **Database**: SQLite (사용자 설정 및 알림 기록 저장)
*   **Deployment**: Railway (Procfile 지원)

## 설치 및 실행 방법

### 1. 로컬 실행

1.  저장소를 클론하거나 소스 코드를 다운로드합니다.
2.  필요한 라이브러리를 설치합니다:
    ```bash
    pip install -r requirements.txt
    ```
3.  `.env.example` 파일을 `.env`로 복사하고 API 키를 입력합니다:
    *   `TELEGRAM_BOT_TOKEN`: 텔레그램 BotFather에게 받은 토큰
    *   `BIZINFO_API_KEY`: 기업마당 API 키
    *   `KSTARTUP_API_KEY`: K-Startup API 키
    *   `OPENAI_API_KEY`: OpenAI API 키
4.  봇을 실행합니다:
    ```bash
    python main.py
    ```

### 2. Railway 배포 방법

1.  GitHub 저장소에 코드를 푸시합니다.
2.  [Railway](https://railway.app/)에서 `New Project` -> `Deploy from GitHub repo`를 선택합니다.
3.  `Variables` 탭에서 `.env` 파일에 있는 모든 환경변수를 추가합니다.
4.  Railway가 `Procfile`을 감지하여 자동으로 `worker` 프로세스를 실행합니다.

## 주의사항

*   SQLite 데이터베이스 파일(`bot_database.db`)은 로컬 또는 Railway의 볼륨 마운트 기능을 사용하지 않으면 재배포 시 초기화될 수 있습니다. (영구 저장이 필요한 경우 외부 DB 연동 권장)
*   API 호출 제한(Rate Limit)을 준수하기 위해 스케줄러 주기를 적절히 조절하십시오.
