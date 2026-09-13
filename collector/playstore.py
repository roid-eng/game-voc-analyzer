import time
from datetime import datetime, timedelta
from google_play_scraper import reviews, Sort
from config import DOMAINS, get_apps

_APPS = get_apps()


def fetch_reviews(game_key: str, days: int = 30) -> list[dict]:
    """지정한 앱의 최근 N일치 Google Play 리뷰를 수집한다."""
    game = _APPS[game_key]
    cutoff = datetime.now() - timedelta(days=days)

    records = []
    continuation_token = None

    while True:
        result, continuation_token = reviews(
            game['app_id'],
            lang='ko',
            country='kr',
            sort=Sort.NEWEST,
            count=200,
            continuation_token=continuation_token,
        )

        if not result:
            break

        reached_cutoff = False
        for r in result:
            if not r.get('content'):
                continue
            if r['at'] < cutoff:
                reached_cutoff = True
                break
            records.append({
                'date': r['at'].strftime('%Y-%m-%d'),
                'domain': game['domain'],
                'game': game_key,
                'genre': game['genre'],
                'review_id': r['reviewId'],
                'rating': r['score'],
                'review_text': r['content'],
            })

        if reached_cutoff or not continuation_token:
            break

        time.sleep(1)

    return records


def fetch_domain(domain_key: str, days: int = 30) -> list[dict]:
    """지정한 도메인에 속한 모든 앱의 리뷰를 순서대로 수집한다."""
    all_records = []

    for game_key in DOMAINS[domain_key]["apps"]:
        print(f"[collector] {game_key} 수집 중... (최근 {days}일)")
        try:
            records = fetch_reviews(game_key, days)
            all_records.extend(records)
            print(f"[collector] {game_key} 완료: {len(records)}건")
        except Exception as e:
            print(f"[collector] {game_key} 수집 실패: {e}")
        time.sleep(2)

    return all_records


def fetch_all(days: int = 30) -> list[dict]:
    """모든 도메인의 모든 앱 리뷰를 순서대로 수집한다."""
    all_records = []

    for domain_key in DOMAINS:
        all_records.extend(fetch_domain(domain_key, days))

    return all_records
