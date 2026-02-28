# 게임 VOC 자동 분석 시스템

## 프로젝트 목적

운영 PM 포트폴리오용 게임 VOC 자동 분석 시스템.
Google Play 리뷰를 자동 수집·분석하여 플레이어 불만/요구사항을 구조화된 데이터로 변환하고,
장르 간 VOC 비교가 가능한 CSV 데이터로 저장한다.

---

## 기술 스택

| 구분 | 선택 |
|------|------|
| 언어 | Python 3.11+ |
| 수집 | google-play-scraper (개발자 계정 불필요) |
| AI 분석 | Groq API (llama-3.3-70b-versatile, 무료 티어) |
| 저장 | CSV (data/reviews.csv, GitHub 리포에 누적 커밋) |
| 알림 | Telegram Bot API (일일 브리핑 자동 발송) |
| 자동화 | GitHub Actions (매일 1회, 분석 후 CSV 자동 커밋) |
| 환경 관리 | python-dotenv (.env) |

---

## 분석 대상

| 게임 | 장르 | Google Play 앱 ID |
|------|------|-------------------|
| 리니지M | MMORPG | com.ncsoft.lineagem |
| 브라운더스트2 | 전략 RPG | com.neowizgames.game.browndust2 |

---

## 분석 카테고리

| 카테고리 | 설명 |
|----------|------|
| BM | 과금 구조, 아이템 가격, 확률 관련 불만 |
| 밸런스 | 직업/스킬/PvP 밸런스 이슈 |
| 강화 | 강화 시스템, 확률, 결과 불만 |
| 서버 | 렉, 점검, 서버 안정성, 버그 |
| 운영 | GM 대응, 제재, 공지, 이벤트 운영 |

---

## 프로젝트 구조

```
game-voc-analyzer/
├── CLAUDE.md                  # 이 파일
├── .env                       # API 키 (git 제외)
├── .gitignore
├── requirements.txt
│
├── collector/
│   ├── __init__.py
│   └── playstore.py           # google-play-scraper 수집
│
├── analyzer/
│   ├── __init__.py
│   └── gemini.py              # Gemini API 분석 엔진
│
├── storage/
│   ├── __init__.py
│   └── csv_storage.py         # CSV 누적 저장 (중복 방지)
│
├── reporter/
│   ├── __init__.py
│   └── telegram.py            # 텔레그램 일일 브리핑 발송
│
├── data/
│   └── reviews.csv            # 분석 결과 누적 데이터 (git 추적)
│
├── config.py                  # 게임 설정 (앱 ID, 레이블 등)
├── main.py                    # 진입점 (수집 → 분석 → 저장 → 브리핑)
│
└── .github/
    └── workflows/
        └── daily_run.yml      # GitHub Actions 자동화 + CSV 커밋
```

---

## 데이터 스펙 (data/reviews.csv 컬럼)

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| date | DATE | 수집 날짜 (YYYY-MM-DD) |
| game | STRING | lineage_m / browndust2 |
| genre | STRING | MMORPG / 전략RPG |
| review_id | STRING | 원문 리뷰 ID |
| rating | INTEGER | 별점 1~5 |
| review_text | STRING | 원문 리뷰 내용 |
| category | STRING | BM / 밸런스 / 강화 / 서버 / 운영 |
| sentiment | STRING | 부정 / 중립 / 긍정 |
| summary | STRING | Gemini 요약 (1~2문장) |
| keywords | STRING | 핵심 키워드 (쉼표 구분) |
| priority | INTEGER | 긴급도 1~5 (Gemini 판단) |

---

## 개발 원칙

1. **단순하게 유지한다** - 필요한 기능만 구현. 미래 요구사항을 위한 추상화 금지.
2. **비용 통제** - Gemini 무료 티어 한도 내 운영. 배치 처리로 API 호출 최소화.
3. **재현 가능성** - 동일 입력에 동일 출력. 분석 프롬프트 버전 관리.
4. **민감 정보 보호** - API 키는 .env 및 GitHub Secrets에만 저장.
5. **중복 방지** - review_id 기준으로 이미 분석된 리뷰는 재처리하지 않는다.
6. **실행 우선** - 완벽한 설계보다 동작하는 코드. 리팩터링은 필요할 때만.

---

## .env 필수 항목

```
GROQ_API_KEY=your_groq_api_key
TELEGRAM_BOT_TOKEN=your_bot_token      # 텔레그램 브리핑용
TELEGRAM_CHAT_ID=your_chat_id          # 텔레그램 브리핑용
```

> TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 가 없으면 브리핑을 스킵하고 정상 종료한다.
> GitHub Actions에서는 Repository Secrets에 두 항목을 등록해야 한다.

---

## 실행 방법

```bash
# 의존성 설치
pip install -r requirements.txt

# 전체 파이프라인 실행 (모든 게임, 최근 30일)
python main.py

# 특정 게임만 실행
python main.py --game lineage_m
python main.py --game browndust2

# 수집 기간 지정 (기본값: 30일)
python main.py --days 7       # 최근 7일
python main.py --days 90      # 과거 데이터 소급 수집
```

---

## 주의사항

- Groq 무료 티어: 분당 30회 요청 제한 (llama-3.3-70b-versatile). 배치 처리 시 rate limit 고려.
- google-play-scraper는 비공식 API. Google Play 정책 변경 시 동작 불안정 가능.
- data/reviews.csv는 git에서 추적한다. GitHub Actions가 매일 자동 커밋.
- review_id 기준 중복 체크로 동일 리뷰가 두 번 저장되지 않는다.
