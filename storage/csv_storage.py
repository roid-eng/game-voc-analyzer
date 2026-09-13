import csv
import os
from pathlib import Path

DATA_DIR = Path("data")
CSV_PATH = DATA_DIR / "reviews.csv"

COLUMNS = [
    "date", "domain", "game", "genre", "review_id", "rating",
    "review_text", "category", "sentiment", "summary", "keywords", "priority",
]


def _domain_of(row: dict) -> str:
    """domain 컬럼이 없는 과거 행은 game 도메인으로 간주한다 (마이그레이션 전 데이터 호환)."""
    return row.get("domain") or "game"


def _get_existing_ids() -> set[tuple[str, str]]:
    """CSV에서 이미 저장된 (domain, review_id) 집합을 반환한다.
    도메인이 다르면 review_id가 우연히 같아도 별개 리뷰로 취급한다."""
    if not CSV_PATH.exists():
        return set()
    with CSV_PATH.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return {(_domain_of(row), row["review_id"]) for row in reader if row.get("review_id")}


def save(records: list[dict]) -> None:
    """분석된 레코드를 data/reviews.csv에 누적 저장한다 (중복 제외)."""
    if not records:
        print("[storage] 저장할 레코드 없음")
        return

    DATA_DIR.mkdir(exist_ok=True)

    existing_ids = _get_existing_ids()
    new_records = [r for r in records if (_domain_of(r), r["review_id"]) not in existing_ids]

    skipped = len(records) - len(new_records)
    if not new_records:
        print(f"[storage] 신규 리뷰 없음 (중복 {skipped}건 제외)")
        return

    def _clean(record: dict) -> dict:
        return {
            k: v.encode("utf-8", errors="ignore").decode("utf-8") if isinstance(v, str) else v
            for k, v in record.items()
        }

    write_header = not CSV_PATH.exists()
    with CSV_PATH.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerows(_clean(r) for r in new_records)

    print(f"[storage] {len(new_records)}건 저장 완료 (중복 {skipped}건 제외)")
    print(f"[storage] 저장 경로: {CSV_PATH.resolve()}")
