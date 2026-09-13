# VOC 자동분석 프레임워크 (도메인: game, health)

## 프로젝트 목적

운영 PM 포트폴리오용 VOC 자동분석 프레임워크.
Google Play 리뷰를 자동 수집·분석하여 사용자 불만/요구사항을 구조화된 데이터로 변환하고,
도메인·앱 간 VOC 비교가 가능한 CSV 데이터로 저장한다.

수집·분석·저장·브리핑 백엔드 로직은 도메인 공통으로 재사용하고, 카테고리·앱 목록·수집 채널처럼
도메인마다 달라지는 값은 config에서 주입한다. game(리니지M, 브라운더스트2)에서 시작해
health(삼성헬스)를 두 번째 사례로 추가했으며, 세 번째 도메인이 언제든 추가될 수 있다는
전제로 설계한다.

---

## 기술 스택

| 구분 | 선택 |
|------|------|
| 언어 | Python 3.11+ |
| 수집 | google-play-scraper (개발자 계정 불필요) |
| AI 분석 | Groq API (모델은 .env의 `GROQ_MODEL`로 관리, 기본값 `openai/gpt-oss-120b`, 무료 티어) |
| 저장 | CSV (data/reviews.csv, GitHub 리포에 누적 커밋) |
| 알림 | Telegram Bot API (일일 브리핑 자동 발송) |
| 자동화 | GitHub Actions (매일 1회, 분석 후 CSV 자동 커밋) |
| 환경 관리 | python-dotenv (.env) |

---

## 도메인 구성

| 도메인 | 앱 | 장르/분류 | 앱 ID (Google Play) |
|--------|-----|-----------|----------------------|
| game | 리니지M | MMORPG | com.ncsoft.lineagem |
| game | 브라운더스트2 | 전략 RPG | com.neowizgames.game.browndust2 |
| health | 삼성헬스 | 헬스케어 | com.sec.android.app.shealth |

> 새 앱/도메인 추가 시 이 표와 `config.py`의 도메인 설정만 갱신하면 된다. game/health 전용
> 가정은 코드에 하드코딩하지 않고, 세 번째 도메인 추가를 항상 염두에 둔다.

---

## 도메인별 분석 카테고리

### game

| 카테고리 | 설명 |
|----------|------|
| BM | 과금 구조, 아이템 가격, 확률 관련 불만 |
| 밸런스 | 직업/스킬/PvP 밸런스 이슈 |
| 강화 | 강화 시스템, 확률, 결과 불만 |
| 서버 | 렉, 점검, 서버 안정성, 버그 |
| 운영 | GM 대응, 제재, 공지, 이벤트 운영 |

### health

| 카테고리 | 설명 |
|----------|------|
| 데이터정확도 | 앱이 정상 동작하는 상태에서 측정값(걸음수·심박수·거리·수면 등 실제 수치)이 부정확하게 나오는 경우 |
| 앱안정성 | 기기 간 연동/동기화 실패, 크래시, 로그인·로그아웃 문제 등 기능 자체가 정상 동작하지 않는 경우 |
| UX/UI | 사용성, 화면 구성, 접근성 관련 불만 |
| 구독과금 | 프리미엄 구독, 결제, 환불 관련 불만 |
| 알림개인정보 | 알림 과다/누락, 개인정보·건강데이터 처리 우려 |
| 운영대응 | CS 응대, 업데이트 공지, 정책 변경 대응 |

> 카테고리 목록은 도메인별로 `config.py`(`DOMAINS[domain]["categories"]`, 이름→설명 매핑)에서
> 정의한다. 분석 엔진은 카테고리 집합과 설명을 코드에 하드코딩하지 않고 config에서 주입받아
> 프롬프트에 그대로 반영한다.
>
> **데이터정확도 vs 앱안정성 경계**: 워치↔폰 등 기기 간 연동/동기화 실패는 "기능이 정상
> 동작하지 않는 문제"로 보고 앱안정성으로 분류한다. 측정값 자체의 오차(예: 거리·심박수
> 수치가 실제와 다름)만 데이터정확도로 분류한다.

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
├── config.py                  # 도메인별 설정 (앱 ID, 카테고리, 레이블 등)
├── main.py                    # 진입점 (수집 → 분석 → 저장 → 브리핑)
├── migrate_add_domain.py      # data/reviews.csv에 domain 컬럼 추가 (1회성, 재실행 안전)
├── generate_dashboard.py      # docs/index.html(랜딩) + docs/{domain}/index.html 생성 (Chart.js)
│
├── docs/
│   ├── index.html             # 랜딩 페이지 (도메인 카드, 자동 생성, git 추적)
│   ├── game/index.html        # 게임 대시보드 (자동 생성, git 추적)
│   └── health/index.html      # 헬스 대시보드 (자동 생성, git 추적)
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
| domain | STRING | game / health |
| app | STRING | 앱 식별자 (예: lineage_m, browndust2, samsung_health) — 기존 `game` 컬럼을 이름만 변경 |
| genre | STRING | 장르/서비스 분류 (예: MMORPG, 전략RPG, 헬스케어) |
| review_id | STRING | 원문 리뷰 ID (고유성은 `(domain, review_id)` 조합 기준 — 도메인이 다르면 review_id가 우연히 같아도 별개 리뷰로 취급) |
| rating | INTEGER | 별점 1~5 |
| review_text | STRING | 원문 리뷰 내용 |
| category | STRING | 도메인별 카테고리 (도메인별 분석 카테고리 참고) |
| sentiment | STRING | 부정 / 중립 / 긍정 |
| summary | STRING | AI 요약 (1~2문장) |
| keywords | STRING | 핵심 키워드 (쉼표 구분) |
| priority | INTEGER | 긴급도 1~5 (AI 판단) |

### 기존 CSV 마이그레이션 (game 전용 → domain 포함)

1. **완료** `domain` 컬럼 추가 — `migrate_add_domain.py`가 기존 모든 행에 `domain=game` 값을
   채운다 (기존 데이터는 전부 game 도메인). 이미 `domain` 컬럼이 있으면 스킵하는 안전한
   재실행 가능 스크립트이며, 실행 전 `data/reviews.csv.bak`으로 원본을 백업한다.
   `storage/csv_storage.py`의 중복 체크도 `(domain, review_id)` 조합 기준으로 바뀌었다.
2. **미완료** `game` 컬럼명을 `app`으로 rename (값은 그대로 유지: `lineage_m`, `browndust2`,
   `samsung_health`). 아직 코드가 `game` 컬럼명을 그대로 참조하므로(수집기/저장소/리포터),
   rename 시 세 곳을 함께 고쳐야 한다.
3. `genre` 컬럼은 그대로 유지한다 — 의미를 "도메인 불문 장르/서비스 분류"로 넓혀 재사용한다
   (health 행은 `헬스케어`로 채워져 있다).
4. rename까지 마치면 `pandas`로 CSV를 읽어 컬럼/행 수·중복 `(domain, review_id)` 여부를
   검증하고 커밋한다.

---

## 개발 원칙

1. **단순하게 유지한다** - 필요한 기능만 구현. 미래 요구사항을 위한 추상화 금지.
2. **비용 통제** - Groq 무료 티어 한도 내 운영. 배치 처리로 API 호출 최소화.
3. **재현 가능성** - 동일 입력에 동일 출력. 분석 프롬프트 버전 관리.
4. **민감 정보 보호** - API 키는 .env 및 GitHub Secrets에만 저장.
5. **중복 방지** - review_id 기준으로 이미 분석된 리뷰는 재처리하지 않는다.
6. **실행 우선** - 완벽한 설계보다 동작하는 코드. 리팩터링은 필요할 때만.
7. **도메인 확장성** - 게임/헬스 전용 가정을 코드에 하드코딩하지 않는다. 카테고리, 앱 목록,
   수집 채널은 항상 config에서 주입하고, 세 번째 도메인이 추가될 수 있다는 전제로 설계한다.
   기존 game 파이프라인을 깨뜨리는 변경은 하지 않는다.

---

## .env 필수 항목

```
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b         # 사용할 Groq 모델 (llama-3.3-70b-versatile은 2026-08-16 폐기됨)
TELEGRAM_BOT_TOKEN=your_bot_token      # 텔레그램 브리핑용
TELEGRAM_CHAT_ID=your_chat_id          # 텔레그램 브리핑용
```

> TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 가 없으면 브리핑을 스킵하고 정상 종료한다.
> 당일 새 리뷰가 없으면 "오늘 새로운 리뷰가 없습니다." 메시지를 발송한다 (파이프라인 중단 없이).
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

## 대시보드 (GitHub Pages)

- `generate_dashboard.py` 실행 시 `docs/index.html`(랜딩) + 도메인별 `docs/{domain}/index.html`을
  `config.DOMAINS`를 순회하며 자동 생성한다. 도메인을 추가해도 이 스크립트는 수정할 필요 없다.
- `docs/index.html` (랜딩): "VOC 자동분석 프레임워크" 소개 + 도메인별 카드(이모지, 앱 목록,
  총 리뷰 수, 위험등급). 카드 클릭 시 해당 도메인 대시보드(`{domain}/index.html`)로 이동.
- `docs/{domain}/index.html` (도메인 대시보드): 위험등급 카드(도메인 내 앱마다 1개) / 일별
  트렌드 / 카테고리·감성 도넛(해당 도메인 카테고리만) / 앱별 카테고리 비교 막대 / 긴급 이슈
  테이블. 상단에 랜딩으로 돌아가는 "← 홈" 링크 포함.
- Chart.js 기반, 외부 의존성 없음 (CDN만 사용)
- GitHub Pages 설정: Settings → Pages → Source: `main` 브랜치, `/docs` 폴더 — **폴더 구조가
  바뀌어도 이 설정은 그대로 둔다.** GitHub Pages는 `/docs` 아래 어떤 하위 폴더의 `index.html`이든
  자동으로 서빙하므로 추가 설정이 필요 없다.
- 기존 링크(`roid-eng.github.io/game-voc-analyzer/`)는 계속 살아있지만, 이제 **바로 게임
  대시보드가 아니라 랜딩 페이지를 보여준다.** 게임 대시보드를 바로 보려면
  `roid-eng.github.io/game-voc-analyzer/game/`으로 이동해야 한다 — README나 포트폴리오 소개
  글에 게임 대시보드로 바로 가는 링크를 박아둔 곳이 있다면 갱신이 필요하다.
- GitHub Actions가 매일 HTML을 재생성 후 커밋 → Pages 자동 갱신 (`daily_run.yml`의 커밋 스텝이
  `docs/` 전체를 add하도록 갱신됨)

---

## 주의사항

- Groq 무료 티어: 분당 30회 요청 제한 (openai/gpt-oss-120b, 분당 토큰 8,000). 배치 처리 시 rate limit 고려.
- **모델 교체 이력**: 2026-08 `llama-3.3-70b-versatile` → `openai/gpt-oss-120b` 마이그레이션. Groq의 llama-3.3-70b-versatile 폐기(2026-08-16) 조치에 따른 대응. TPM 한도가 낮아져(12,000→8,000) 배치 크기를 10→6으로 축소. 모델명은 하드코딩하지 않고 `.env`의 `GROQ_MODEL`로 관리한다.
- google-play-scraper는 비공식 API. Google Play 정책 변경 시 동작 불안정 가능.
- data/reviews.csv, docs/ 전체(랜딩 + 도메인별 대시보드)는 git에서 추적한다. GitHub Actions가 매일 자동 커밋.
- review_id 기준 중복 체크로 동일 리뷰가 두 번 저장되지 않는다.
