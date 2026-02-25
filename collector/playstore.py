import time
from google_play_scraper import reviews, Sort
from config import GAMES


def fetch_reviews(game_key: str, count: int = 100) -> list[dict]:
    """지정한 게임의 Google Play 최신 리뷰를 수집한다."""
    game = GAMES[game_key]

    result, _ = reviews(
        game['app_id'],
        lang='ko',
        country='kr',
        sort=Sort.NEWEST,
        count=count,
    )

    records = []
    for r in result:
        # 빈 리뷰 텍스트는 건너뜀
        if not r.get('content'):
            continue
        records.append({
            'date': r['at'].strftime('%Y-%m-%d'),
            'game': game_key,
            'genre': game['genre'],
            'review_id': r['reviewId'],
            'rating': r['score'],
            'review_text': r['content'],
        })

    return records


def fetch_all(count: int = 100) -> list[dict]:
    """모든 게임 리뷰를 순서대로 수집한다."""
    all_records = []

    for game_key in GAMES:
        print(f"[collector] {game_key} 수집 중... (최대 {count}건)")
        try:
            records = fetch_reviews(game_key, count)
            all_records.extend(records)
            print(f"[collector] {game_key} 완료: {len(records)}건")
        except Exception as e:
            print(f"[collector] {game_key} 수집 실패: {e}")
        time.sleep(2)  # 게임 간 요청 딜레이

    return all_records
