#!/usr/bin/env python3
"""reviews.csv + top_issues.csv를 읽어 docs/index.html을 생성한다."""

import csv
import json
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from pathlib import Path

REVIEWS_CSV = Path("data/reviews.csv")
TOP_ISSUES_CSV = Path("data/top_issues.csv")
OUTPUT_HTML = Path("docs/index.html")

VALID_CATEGORIES = {"BM", "밸런스", "강화", "서버", "운영"}
VALID_SENTIMENTS = {"부정", "중립", "긍정"}
GAME_LABELS = {
    "lineage_m": "리니지M",
    "browndust2": "브라운더스트2",
}


def load_reviews():
    if not REVIEWS_CSV.exists():
        return []
    with REVIEWS_CSV.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["category"] = r["category"].strip()
        r["sentiment"] = r["sentiment"].strip()
        if r["category"] not in VALID_CATEGORIES:
            r["category"] = "기타"
        if r["sentiment"] not in VALID_SENTIMENTS:
            r["sentiment"] = "기타"
        try:
            r["priority"] = int(r["priority"])
        except (ValueError, KeyError):
            r["priority"] = 0
    return rows


def calc_risk(rows, game):
    game_rows = [r for r in rows if r["game"] == game and r["priority"] > 0]
    if not game_rows:
        return "LOW"
    avg = sum(r["priority"] for r in game_rows) / len(game_rows)
    if avg >= 3.5:
        return "HIGH"
    if avg >= 2.5:
        return "MID"
    return "LOW"


def build_data(rows):
    today = datetime.now()
    week_ago = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    month_ago = (today - timedelta(days=30)).strftime("%Y-%m-%d")

    week_rows = [r for r in rows if r.get("date", "") >= week_ago]
    month_rows = [r for r in rows if r.get("date", "") >= month_ago]

    # 위험등급
    risk = {
        "lineage_m": calc_risk(rows, "lineage_m"),
        "browndust2": calc_risk(rows, "browndust2"),
    }

    # 최근 30일 일별 트렌드
    dates_30 = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(29, -1, -1)]
    daily = defaultdict(lambda: defaultdict(int))
    for r in month_rows:
        daily[r["game"]][r["date"]] += 1

    trend = {
        "dates": dates_30,
        "lineage_m": [daily["lineage_m"].get(d, 0) for d in dates_30],
        "browndust2": [daily["browndust2"].get(d, 0) for d in dates_30],
    }

    # 카테고리 분포 (전체, 유효값만)
    cat_counter = Counter(r["category"] for r in rows if r["category"] in VALID_CATEGORIES)
    category = {
        "labels": list(cat_counter.keys()),
        "values": list(cat_counter.values()),
    }

    # 감성 분포
    sent_counter = Counter(r["sentiment"] for r in rows if r["sentiment"] in VALID_SENTIMENTS)
    sentiment = {
        "labels": list(sent_counter.keys()),
        "values": list(sent_counter.values()),
    }

    # 게임별 카테고리 비교
    categories = ["BM", "밸런스", "강화", "서버", "운영"]
    game_cat = {}
    for game in ["lineage_m", "browndust2"]:
        c = Counter(r["category"] for r in rows if r["game"] == game and r["category"] in VALID_CATEGORIES)
        game_cat[game] = [c.get(cat, 0) for cat in categories]

    game_category = {
        "labels": categories,
        "lineage_m": game_cat["lineage_m"],
        "browndust2": game_cat["browndust2"],
    }

    # 긴급도 분포
    pri_counter = Counter(r["priority"] for r in rows if r["priority"] > 0)
    priority = {
        "labels": ["긴급도 1", "긴급도 2", "긴급도 3", "긴급도 4", "긴급도 5"],
        "values": [pri_counter.get(i, 0) for i in range(1, 6)],
    }

    # 이번 주 긴급 이슈 테이블 (긴급도 4~5)
    urgent = sorted(
        [r for r in week_rows if r["priority"] >= 4],
        key=lambda r: r["priority"],
        reverse=True,
    )
    urgent_table = [
        {
            "game": GAME_LABELS.get(r["game"], r["game"]),
            "category": r["category"],
            "summary": r.get("summary", "")[:80],
            "keywords": r.get("keywords", ""),
            "priority": r["priority"],
        }
        for r in urgent[:20]
    ]

    return {
        "updated": today.strftime("%Y-%m-%d"),
        "risk": risk,
        "week_total": len(week_rows),
        "trend": trend,
        "category": category,
        "sentiment": sentiment,
        "game_category": game_category,
        "priority": priority,
        "urgent_table": urgent_table,
    }


def generate_html(d: dict) -> str:
    data_json = json.dumps(d, ensure_ascii=False)
    risk_color = {"HIGH": "#ef4444", "MID": "#f59e0b", "LOW": "#22c55e"}
    lm_risk = d["risk"]["lineage_m"]
    bd_risk = d["risk"]["browndust2"]

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>게임 VOC 분석 대시보드</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; }}
header {{ padding: 24px 32px; border-bottom: 1px solid #1e293b; }}
header h1 {{ font-size: 1.5rem; font-weight: 700; }}
header p {{ font-size: 0.85rem; color: #94a3b8; margin-top: 4px; }}
.container {{ max-width: 1200px; margin: 0 auto; padding: 24px 32px; }}
.row {{ display: grid; gap: 16px; margin-bottom: 24px; }}
.row-3 {{ grid-template-columns: 1fr 1fr 1fr; }}
.row-1 {{ grid-template-columns: 1fr; }}
.row-2 {{ grid-template-columns: 1fr 1fr; }}
.card {{ background: #1e293b; border-radius: 12px; padding: 20px; }}
.card h2 {{ font-size: 0.8rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 16px; }}
.risk-value {{ font-size: 2.2rem; font-weight: 800; }}
.stat-value {{ font-size: 2.5rem; font-weight: 800; color: #38bdf8; }}
.chart-wrap {{ position: relative; height: 260px; }}
.chart-wrap-lg {{ position: relative; height: 300px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
th {{ text-align: left; padding: 10px 12px; background: #0f172a; color: #94a3b8; font-weight: 600; }}
td {{ padding: 10px 12px; border-top: 1px solid #0f172a; vertical-align: top; }}
tr:hover td {{ background: #263348; }}
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 9999px; font-size: 0.75rem; font-weight: 700; }}
.p5 {{ background: #450a0a; color: #fca5a5; }}
.p4 {{ background: #431407; color: #fdba74; }}
.empty {{ text-align: center; color: #64748b; padding: 24px; }}
@media (max-width: 768px) {{
  .row-3, .row-2 {{ grid-template-columns: 1fr; }}
  .container {{ padding: 16px; }}
}}
</style>
</head>
<body>
<header>
  <h1>🎮 게임 VOC 분석 대시보드</h1>
  <p>마지막 업데이트: {d["updated"]} &nbsp;|&nbsp; 리니지M · 브라운더스트2</p>
</header>
<div class="container">

  <!-- Row 1: 요약 카드 -->
  <div class="row row-3">
    <div class="card">
      <h2>리니지M 위험등급</h2>
      <div class="risk-value" style="color:{risk_color[lm_risk]}">{lm_risk}</div>
    </div>
    <div class="card">
      <h2>브라운더스트2 위험등급</h2>
      <div class="risk-value" style="color:{risk_color[bd_risk]}">{bd_risk}</div>
    </div>
    <div class="card">
      <h2>이번 주 총 리뷰</h2>
      <div class="stat-value">{d["week_total"]}건</div>
    </div>
  </div>

  <!-- Row 2: 일별 트렌드 -->
  <div class="row row-1">
    <div class="card">
      <h2>최근 30일 일별 리뷰 추이</h2>
      <div class="chart-wrap-lg"><canvas id="trendChart"></canvas></div>
    </div>
  </div>

  <!-- Row 3: 파이 차트 -->
  <div class="row row-2">
    <div class="card">
      <h2>카테고리 분포 (전체)</h2>
      <div class="chart-wrap"><canvas id="categoryChart"></canvas></div>
    </div>
    <div class="card">
      <h2>감성 분포 (전체)</h2>
      <div class="chart-wrap"><canvas id="sentimentChart"></canvas></div>
    </div>
  </div>

  <!-- Row 4: 막대 차트 -->
  <div class="row row-2">
    <div class="card">
      <h2>게임별 카테고리 비교</h2>
      <div class="chart-wrap"><canvas id="gameCategoryChart"></canvas></div>
    </div>
    <div class="card">
      <h2>긴급도별 분포</h2>
      <div class="chart-wrap"><canvas id="priorityChart"></canvas></div>
    </div>
  </div>

  <!-- Row 5: 긴급 이슈 테이블 -->
  <div class="row row-1">
    <div class="card">
      <h2>이번 주 긴급 이슈 (긴급도 4~5)</h2>
      <table>
        <thead>
          <tr>
            <th>게임</th><th>카테고리</th><th>긴급도</th><th>요약</th><th>키워드</th>
          </tr>
        </thead>
        <tbody id="urgentBody"></tbody>
      </table>
    </div>
  </div>

</div>
<script>
const D = {data_json};
const GRID = '#263348';
Chart.defaults.color = '#94a3b8';
Chart.defaults.font.family = "'Segoe UI', sans-serif";

// 트렌드
new Chart(document.getElementById('trendChart'), {{
  type: 'line',
  data: {{
    labels: D.trend.dates,
    datasets: [
      {{ label: '리니지M', data: D.trend.lineage_m, borderColor: '#f472b6', backgroundColor: 'rgba(244,114,182,0.08)', tension: 0.3, fill: true, pointRadius: 3 }},
      {{ label: '브라운더스트2', data: D.trend.browndust2, borderColor: '#38bdf8', backgroundColor: 'rgba(56,189,248,0.08)', tension: 0.3, fill: true, pointRadius: 3 }},
    ]
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ position: 'top' }} }},
    scales: {{
      x: {{ grid: {{ color: GRID }}, ticks: {{ maxTicksLimit: 10 }} }},
      y: {{ grid: {{ color: GRID }}, beginAtZero: true }}
    }}
  }}
}});

// 카테고리 도넛
new Chart(document.getElementById('categoryChart'), {{
  type: 'doughnut',
  data: {{
    labels: D.category.labels,
    datasets: [{{ data: D.category.values, backgroundColor: ['#f472b6','#818cf8','#34d399','#fbbf24','#f87171','#a78bfa'] }}]
  }},
  options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ position: 'right' }} }} }}
}});

// 감성 도넛
new Chart(document.getElementById('sentimentChart'), {{
  type: 'doughnut',
  data: {{
    labels: D.sentiment.labels,
    datasets: [{{ data: D.sentiment.values, backgroundColor: ['#f87171','#94a3b8','#34d399','#64748b'] }}]
  }},
  options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ position: 'right' }} }} }}
}});

// 게임별 카테고리 막대
new Chart(document.getElementById('gameCategoryChart'), {{
  type: 'bar',
  data: {{
    labels: D.game_category.labels,
    datasets: [
      {{ label: '리니지M', data: D.game_category.lineage_m, backgroundColor: '#f472b6' }},
      {{ label: '브라운더스트2', data: D.game_category.browndust2, backgroundColor: '#38bdf8' }},
    ]
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ position: 'top' }} }},
    scales: {{ x: {{ grid: {{ color: GRID }} }}, y: {{ grid: {{ color: GRID }}, beginAtZero: true }} }}
  }}
}});

// 긴급도 막대
new Chart(document.getElementById('priorityChart'), {{
  type: 'bar',
  data: {{
    labels: D.priority.labels,
    datasets: [{{ label: '건수', data: D.priority.values, backgroundColor: ['#34d399','#6ee7b7','#fbbf24','#f97316','#ef4444'] }}]
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{ x: {{ grid: {{ color: GRID }} }}, y: {{ grid: {{ color: GRID }}, beginAtZero: true }} }}
  }}
}});

// 긴급 이슈 테이블
const tbody = document.getElementById('urgentBody');
if (D.urgent_table.length === 0) {{
  tbody.innerHTML = '<tr><td colspan="5" class="empty">이번 주 긴급 이슈 없음</td></tr>';
}} else {{
  D.urgent_table.forEach(r => {{
    const cls = r.priority === 5 ? 'p5' : 'p4';
    tbody.innerHTML += `<tr>
      <td>${{r.game}}</td>
      <td>${{r.category}}</td>
      <td><span class="badge ${{cls}}">${{r.priority}}</span></td>
      <td>${{r.summary}}</td>
      <td style="color:#94a3b8;font-size:0.8rem">${{r.keywords}}</td>
    </tr>`;
  }});
}}
</script>
</body>
</html>"""


def main():
    rows = load_reviews()
    data = build_data(rows)
    OUTPUT_HTML.parent.mkdir(exist_ok=True)
    OUTPUT_HTML.write_text(generate_html(data), encoding="utf-8")
    print(f"[dashboard] docs/index.html 생성 완료 ({data['updated']}, 총 {len(rows)}건)")


if __name__ == "__main__":
    main()
