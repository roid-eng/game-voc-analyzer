import csv
import os
from pathlib import Path

DATA_DIR = Path("data")
CSV_PATH = DATA_DIR / "reviews.csv"

COLUMNS = [
    "date", "game", "genre", "review_id", "rating",
    "review_text", "category", "sentiment", "summary", "keywords", "priority",
]


def _get_existing_ids() -> set[str]:
    """CSV에서 이미 저장된 review_id 집합을 반환한다."""
    if not CSV_PATH.exists():
        return set()
    with CSV_PATH.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return {row["review_id"] for row in reader if row.get("review_id")}


def save(records: list[dict]) -> None:
    """분석된 레코드를 data/reviews.csv에 누적 저장한다 (중복 제외)."""
    if not records:
        print("[storage] 저장할 레코드 없음")
        return

    DATA_DIR.mkdir(exist_ok=True)

    existing_ids = _get_existing_ids()
    new_records = [r for r in records if r["review_id"] not in existing_ids]

    skipped = len(records) - len(new_records)
    if not new_records:
        print(f"[storage] 신규 리뷰 없음 (중복 {skipped}건 제외)")
        return

    write_header = not CSV_PATH.exists()
    with CSV_PATH.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerows(new_records)

    print(f"[storage] {len(new_records)}건 저장 완료 (중복 {skipped}건 제외)")
    print(f"[storage] 저장 경로: {CSV_PATH.resolve()}")
