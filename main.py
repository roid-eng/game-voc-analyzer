import argparse
import sys

from config import DOMAINS, get_apps
from collector.playstore import fetch_reviews, fetch_domain, fetch_all
from analyzer.gemini import analyze
from storage.csv_storage import save
from reporter.telegram import send_briefing, send_no_review_notice


def run(game_key: str | None, domain_key: str | None, days: int) -> None:
    # 1. 수집
    if game_key:
        print(f"\n[main] 수집 시작: {game_key} (최근 {days}일)")
        records = fetch_reviews(game_key, days)
        print(f"[main] 수집 완료: {len(records)}건")
    elif domain_key:
        print(f"\n[main] 수집 시작: {domain_key} 도메인 (최근 {days}일)")
        records = fetch_domain(domain_key, days)
        print(f"[main] 수집 완료: 총 {len(records)}건")
    else:
        print(f"\n[main] 수집 시작: 전체 도메인 (최근 {days}일)")
        records = fetch_all(days)
        print(f"[main] 수집 완료: 총 {len(records)}건")

    if not records:
        print("[main] 수집된 리뷰가 없습니다.")
        send_no_review_notice(domain=domain_key, game=game_key)
        return

    # 2. 분석
    print(f"\n[main] 분석 시작: {len(records)}건")
    analyzed = analyze(records)
    print(f"[main] 분석 완료: {len(analyzed)}건")

    # 3. 저장
    print("\n[main] 저장 시작")
    save(analyzed)
    print("[main] 저장 완료")

    # 4. 텔레그램 브리핑
    send_briefing(days)


def main() -> None:
    parser = argparse.ArgumentParser(description="VOC 자동분석 파이프라인")
    parser.add_argument(
        "--game",
        choices=list(get_apps().keys()),
        default=None,
        help="분석할 앱 (미지정 시 --domain 또는 전체 도메인 실행)",
    )
    parser.add_argument(
        "--domain",
        choices=list(DOMAINS.keys()),
        default=None,
        help="분석할 도메인 (미지정 시 전체 도메인 순차 실행)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="수집할 리뷰 기간 (기본값: 30일)",
    )
    args = parser.parse_args()

    if args.game and args.domain:
        parser.error("--game과 --domain은 동시에 지정할 수 없습니다.")

    try:
        run(args.game, args.domain, args.days)
    except KeyboardInterrupt:
        print("\n[main] 사용자 중단")
        sys.exit(0)
    except Exception as e:
        print(f"\n[main] 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
