import pandas as pd

df = pd.read_csv("data/reviews.csv", parse_dates=["date"])

top = (
    df.sort_values(["priority", "date"], ascending=[False, False])
    .groupby(["game", "category"], as_index=False)
    .first()
)[["game", "category", "priority", "summary", "keywords"]]

top = top.sort_values(["game", "priority"], ascending=[True, False])

top.to_csv("data/top_issues.csv", index=False, encoding="utf-8-sig")
print(f"저장 완료: {len(top)}건 → data/top_issues.csv")
print(top.to_string(index=False))
