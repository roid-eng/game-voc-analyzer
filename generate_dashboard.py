#!/usr/bin/env python3
"""reviews.csv를 읽어 도메인별 대시보드(docs/{domain}/index.html)와
랜딩 페이지(docs/index.html)를 생성한다."""

import csv
import json
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from pathlib import Path

from config import DOMAINS, get_apps, get_categories

REVIEWS_CSV = Path("data/reviews.csv")
DOCS_DIR = Path("docs")

VALID_SENTIMENTS = {"부정", "중립", "긍정"}
PALETTE = ["#f472b6", "#38bdf8", "#34d399", "#fbbf24", "#a78bfa", "#f87171"]
RISK_COLOR = {"HIGH": "#ef4444", "MID": "#f59e0b", "LOW": "#22c55e"}
RISK_ORDER = {"LOW": 0, "MID": 1, "HIGH": 2}


def _domain_of(row: dict) -> str:
    return row.get("domain") or "game"


def load_reviews() -> list[dict]:
    if not REVIEWS_CSV.exists():
        return []
    with REVIEWS_CSV.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["domain"] = _domain_of(r)
        r["category"] = (r.get("category") or "").strip()
        r["sentiment"] = (r.get("sentiment") or "").strip()
        valid_categories = get_categories(r["domain"]) if r["domain"] in DOMAINS else []
        if r["category"] not in valid_categories:
            r["category"] = "기타"
        if r["sentiment"] not in VALID_SENTIMENTS:
            r["sentiment"] = "기타"
        try:
            r["priority"] = int(r["priority"])
        except (ValueError, KeyError):
            r["priority"] = 0
    return rows


def calc_risk(rows: list[dict], app_key: str) -> str:
    app_rows = [r for r in rows if r["game"] == app_key and r["priority"] > 0]
    if not app_rows:
        return "LOW"
    avg = sum(r["priority"] for r in app_rows) / len(app_rows)
    if avg >= 3.5:
        return "HIGH"
    if avg >= 2.5:
        return "MID"
    return "LOW"


def build_domain_data(domain_key: str, rows: list[dict]) -> dict:
    """도메인 하나(예: game, health)에 대한 대시보드 데이터를 만든다."""
    domain_rows = [r for r in rows if r["domain"] == domain_key]
    apps = get_apps(domain_key)
    categories = get_categories(domain_key)

    today = datetime.now()
    week_ago = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    month_ago = (today - timedelta(days=30)).strftime("%Y-%m-%d")

    week_rows = [r for r in domain_rows if r.get("date", "") >= week_ago]
    month_rows = [r for r in domain_rows if r.get("date", "") >= month_ago]

    risk = {app_key: calc_risk(domain_rows, app_key) for app_key in apps}

    dates_30 = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(29, -1, -1)]
    daily = defaultdict(lambda: defaultdict(int))
    for r in month_rows:
        daily[r["game"]][r["date"]] += 1
    trend = {
        "dates": dates_30,
        "series": {app_key: [daily[app_key].get(d, 0) for d in dates_30] for app_key in apps},
    }

    cat_counter = Counter(r["category"] for r in domain_rows if r["category"] in categories)
    category = {"labels": list(cat_counter.keys()), "values": list(cat_counter.values())}

    sent_counter = Counter(r["sentiment"] for r in domain_rows if r["sentiment"] in VALID_SENTIMENTS)
    sentiment = {"labels": list(sent_counter.keys()), "values": list(sent_counter.values())}

    app_category = {
        "labels": categories,
        "series": {
            app_key: [
                sum(1 for r in domain_rows if r["game"] == app_key and r["category"] == cat)
                for cat in categories
            ]
            for app_key in apps
        },
    }

    pri_counter = Counter(r["priority"] for r in domain_rows if r["priority"] > 0)
    priority = {
        "labels": [f"긴급도 {i}" for i in range(1, 6)],
        "values": [pri_counter.get(i, 0) for i in range(1, 6)],
    }

    urgent = sorted(
        [r for r in week_rows if r["priority"] >= 4],
        key=lambda r: r["priority"],
        reverse=True,
    )
    urgent_table = [
        {
            "app": apps.get(r["game"], {}).get("label", r["game"]),
            "category": r["category"],
            "summary": r.get("summary", "")[:80],
            "keywords": r.get("keywords", ""),
            "priority": r["priority"],
        }
        for r in urgent[:20]
    ]

    return {
        "updated": today.strftime("%Y-%m-%d"),
        "apps": {app_key: app_info.get("label", app_key) for app_key, app_info in apps.items()},
        "risk": risk,
        "week_total": len(week_rows),
        "total": len(domain_rows),
        "trend": trend,
        "category": category,
        "sentiment": sentiment,
        "app_category": app_category,
        "priority": priority,
        "urgent_table": urgent_table,
    }


_DASHBOARD_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; }
header { padding: 24px 32px; border-bottom: 1px solid #1e293b; }
.back-link { display: inline-block; color: #38bdf8; font-size: 0.85rem; text-decoration: none; margin-bottom: 8px; }
.back-link:hover { text-decoration: underline; }
header h1 { font-size: 1.5rem; font-weight: 700; }
header p { font-size: 0.85rem; color: #94a3b8; margin-top: 4px; }
.container { max-width: 1200px; margin: 0 auto; padding: 24px 32px; }
.row { display: grid; gap: 16px; margin-bottom: 24px; }
.row-cards { grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); }
.row-1 { grid-template-columns: 1fr; }
.row-2 { grid-template-columns: 1fr 1fr; }
.card { background: #1e293b; border-radius: 12px; padding: 20px; }
.card h2 { font-size: 0.8rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 16px; }
.risk-value { font-size: 2.2rem; font-weight: 800; }
.stat-value { font-size: 2.5rem; font-weight: 800; color: #38bdf8; }
.chart-wrap { position: relative; height: 260px; }
.chart-wrap-lg { position: relative; height: 300px; }
table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
th { text-align: left; padding: 10px 12px; background: #0f172a; color: #94a3b8; font-weight: 600; }
td { padding: 10px 12px; border-top: 1px solid #0f172a; vertical-align: top; }
tr:hover td { background: #263348; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 9999px; font-size: 0.75rem; font-weight: 700; }
.p5 { background: #450a0a; color: #fca5a5; }
.p4 { background: #431407; color: #fdba74; }
.empty { text-align: center; color: #64748b; padding: 24px; }
@media (max-width: 768px) {
  .row-2 { grid-template-columns: 1fr; }
  .container { padding: 16px; }
}
"""


def generate_domain_html(domain_info: dict, d: dict) -> str:
    data_json = json.dumps(d, ensure_ascii=False)
    app_labels = d["apps"]

    risk_cards = "\n".join(
        f'''    <div class="card">
      <h2>{label} 위험등급</h2>
      <div class="risk-value" style="color:{RISK_COLOR[d['risk'][app_key]]}">{d['risk'][app_key]}</div>
    </div>'''
        for app_key, label in app_labels.items()
    )

    emoji = domain_info.get("emoji", "")
    label = domain_info.get("label", "")
    apps_desc = " · ".join(app_labels.values())

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{label} VOC 분석 대시보드</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>{_DASHBOARD_CSS}</style>
</head>
<body>
<header>
  <a class="back-link" href="../index.html">← 홈</a>
  <h1>{emoji} {label} VOC 분석 대시보드</h1>
  <p>마지막 업데이트: {d["updated"]} &nbsp;|&nbsp; {apps_desc}</p>
</header>
<div class="container">

  <!-- Row 1: 요약 카드 -->
  <div class="row row-cards">
{risk_cards}
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
      <h2>앱별 카테고리 비교</h2>
      <div class="chart-wrap"><canvas id="appCategoryChart"></canvas></div>
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
            <th>앱</th><th>카테고리</th><th>긴급도</th><th>요약</th><th>키워드</th>
          </tr>
        </thead>
        <tbody id="urgentBody"></tbody>
      </table>
    </div>
  </div>

</div>
<script>
const D = {data_json};
const PALETTE = {json.dumps(PALETTE)};
const GRID = '#263348';
Chart.defaults.color = '#94a3b8';
Chart.defaults.font.family = "'Segoe UI', sans-serif";

// 트렌드
const trendDatasets = Object.entries(D.trend.series).map(([key, data], i) => ({{
  label: D.apps[key] || key,
  data,
  borderColor: PALETTE[i % PALETTE.length],
  backgroundColor: PALETTE[i % PALETTE.length] + '14',
  tension: 0.3, fill: true, pointRadius: 3
}}));
new Chart(document.getElementById('trendChart'), {{
  type: 'line',
  data: {{ labels: D.trend.dates, datasets: trendDatasets }},
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
    datasets: [{{ data: D.category.values, backgroundColor: PALETTE.concat(['#818cf8','#64748b']) }}]
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

// 앱별 카테고리 막대
const appCategoryDatasets = Object.entries(D.app_category.series).map(([key, data], i) => ({{
  label: D.apps[key] || key,
  data,
  backgroundColor: PALETTE[i % PALETTE.length]
}}));
new Chart(document.getElementById('appCategoryChart'), {{
  type: 'bar',
  data: {{ labels: D.app_category.labels, datasets: appCategoryDatasets }},
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
      <td>${{r.app}}</td>
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


def _worst_risk(risk: dict) -> str:
    worst = "LOW"
    for r in risk.values():
        if RISK_ORDER.get(r, 0) > RISK_ORDER.get(worst, 0):
            worst = r
    return worst


def generate_landing_html(summaries: dict[str, dict]) -> str:
    """도메인 카드 랜딩 페이지를 만든다."""
    cards = []
    for domain_key, domain_info in DOMAINS.items():
        s = summaries.get(domain_key, {})
        emoji = domain_info.get("emoji", "")
        label = domain_info.get("label", domain_key)
        apps_desc = " · ".join(a.get("label", k) for k, a in domain_info["apps"].items())
        worst = _worst_risk(s.get("risk", {}))
        color = RISK_COLOR.get(worst, RISK_COLOR["LOW"])
        cards.append(f'''
    <a class="domain-card" href="{domain_key}/index.html" style="--accent:{color}">
      <div class="domain-emoji">{emoji}</div>
      <h2>{label} VOC</h2>
      <p class="apps">{apps_desc}</p>
      <p class="meta">총 {s.get("total", 0)}건 · 위험등급 <span style="color:{color}">{worst}</span></p>
    </a>''')
    cards_html = "\n".join(cards)

    updated = max(
        (s.get("updated", "") for s in summaries.values()),
        default=datetime.now().strftime("%Y-%m-%d"),
    )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>VOC 자동분석 프레임워크</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0;
  min-height: 100vh; display: flex; flex-direction: column; align-items: center;
  padding: 64px 24px;
}}
.hero {{ text-align: center; max-width: 640px; margin-bottom: 48px; }}
.hero h1 {{ font-size: 2rem; font-weight: 800; margin-bottom: 12px; }}
.hero p {{ color: #94a3b8; font-size: 0.95rem; line-height: 1.6; }}
.hero .updated {{ margin-top: 12px; font-size: 0.8rem; color: #64748b; }}
.cards {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 280px));
  gap: 24px; justify-content: center; width: 100%; max-width: 720px;
}}
.domain-card {{
  background: #1e293b; border-radius: 16px; padding: 32px 24px; text-align: center;
  text-decoration: none; color: inherit; border: 1px solid #263348;
  border-top: 4px solid var(--accent, #38bdf8);
  transition: transform 0.15s ease, background 0.15s ease;
}}
.domain-card:hover {{ transform: translateY(-4px); background: #263348; }}
.domain-emoji {{ font-size: 2.5rem; margin-bottom: 12px; }}
.domain-card h2 {{ font-size: 1.2rem; font-weight: 700; margin-bottom: 8px; }}
.domain-card .apps {{ font-size: 0.85rem; color: #94a3b8; margin-bottom: 12px; }}
.domain-card .meta {{ font-size: 0.8rem; color: #64748b; }}
</style>
</head>
<body>
  <div class="hero">
    <h1>VOC 자동분석 프레임워크</h1>
    <p>Google Play 리뷰를 자동 수집·분석해 도메인별 플레이어/사용자 VOC 현황을 대시보드로 제공합니다.
    아래 카드를 눌러 도메인별 대시보드로 이동하세요.</p>
    <p class="updated">마지막 업데이트: {updated}</p>
  </div>
  <div class="cards">
{cards_html}
  </div>
</body>
</html>"""


def main():
    rows = load_reviews()
    DOCS_DIR.mkdir(exist_ok=True)

    summaries = {}
    for domain_key, domain_info in DOMAINS.items():
        data = build_domain_data(domain_key, rows)
        summaries[domain_key] = {
            "updated": data["updated"],
            "total": data["total"],
            "risk": data["risk"],
        }
        domain_dir = DOCS_DIR / domain_key
        domain_dir.mkdir(exist_ok=True)
        (domain_dir / "index.html").write_text(generate_domain_html(domain_info, data), encoding="utf-8")
        print(f"[dashboard] docs/{domain_key}/index.html 생성 완료 ({data['updated']}, 총 {data['total']}건)")

    (DOCS_DIR / "index.html").write_text(generate_landing_html(summaries), encoding="utf-8")
    print("[dashboard] docs/index.html(랜딩 페이지) 생성 완료")


if __name__ == "__main__":
    main()
