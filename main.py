import argparse
import sys

from config import GAMES
from collector.playstore import fetch_reviews, fetch_all
from analyzer.gemini import analyze
from storage.csv_storage import save


def run(game_key: str | None, count: int) -> None:
    # 1. 수집
    if game_key:
        print(f"\n[main] 수집 시작: {game_key} ({count}건)")
        records = fetch_reviews(game_key, count)
        print(f"[main] 수집 완료: {len(records)}건")
    else:
        print(f"\n[main] 수집 시작: 전체 게임 ({count}건/게임)")
        records = fetch_all(count)
        print(f"[main] 수집 완료: 총 {len(records)}건")

    if not records:
        print("[main] 수집된 리뷰가 없습니다. 종료합니다.")
        return

    # 2. 분석
    print(f"\n[main] 분석 시작: {len(records)}건")
    analyzed = analyze(records)
    print(f"[main] 분석 완료: {len(analyzed)}건")

    # 3. 저장
    print("\n[main] 저장 시작")
    save(analyzed)
    print("[main] 저장 완료")


def main() -> None:
    parser = argparse.ArgumentParser(description="게임 VOC 자동 분석 파이프라인")
    parser.add_argument(
        "--game",
        choices=list(GAMES.keys()),
        default=None,
        help="분석할 게임 (미지정 시 전체 게임 실행)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=100,
        help="게임당 수집할 리뷰 수 (기본값: 100)",
    )
    args = parser.parse_args()

    try:
        run(args.game, args.count)
    except KeyboardInterrupt:
        print("\n[main] 사용자 중단")
        sys.exit(0)
    except Exception as e:
        print(f"\n[main] 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
