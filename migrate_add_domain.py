"""data/reviews.csv에 domain 컬럼을 안전하게 추가하는 1회성 마이그레이션 스크립트.

기존 행(전부 game 도메인)에는 domain=game을 채운다.
이미 domain 컬럼이 있으면 아무것도 하지 않는다 (안전하게 재실행 가능).
원본은 reviews.csv.bak으로 백업한 뒤 원자적으로 교체한다.
"""
import csv
import shutil
from pathlib import Path

CSV_PATH = Path("data/reviews.csv")
BACKUP_PATH = Path("data/reviews.csv.bak")
TMP_PATH = Path("data/reviews.csv.tmp")

DEFAULT_DOMAIN = "game"


def migrate() -> None:
    if not CSV_PATH.exists():
        print(f"[migrate] {CSV_PATH} 없음 - 마이그레이션 불필요")
        return

    with CSV_PATH.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    if "domain" in fieldnames:
        print("[migrate] domain 컬럼이 이미 존재함 - 스킵")
        return

    if "date" not in fieldnames:
        raise ValueError(f"'date' 컬럼을 찾을 수 없음: {fieldnames}")

    new_fieldnames = ["date", "domain"] + [c for c in fieldnames if c != "date"]

    for row in rows:
        row["domain"] = DEFAULT_DOMAIN

    shutil.copyfile(CSV_PATH, BACKUP_PATH)

    with TMP_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=new_fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    TMP_PATH.replace(CSV_PATH)

    print(f"[migrate] {len(rows)}건에 domain={DEFAULT_DOMAIN} 채움")
    print(f"[migrate] 백업: {BACKUP_PATH.resolve()}")
    print(f"[migrate] 완료: {CSV_PATH.resolve()}")


if __name__ == "__main__":
    migrate()
