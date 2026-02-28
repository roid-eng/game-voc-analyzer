import csv
import json
import os
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

_CSV_PATH = Path("data/reviews.csv")
_MODEL = "llama-3.3-70b-versatile"

_RISK_EMOJI = {"HIGH": "🔴", "MID": "🟡", "LOW": "🟢"}


def _load_recent(days: int = 30) -> list[dict]:
    """reviews.csv에서 최근 N일 데이터를 반환한다."""
    if not _CSV_PATH.exists():
        return []
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    records = []
    with _CSV_PATH.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("date", "") >= cutoff and row.get("priority", "0").isdigit():
                row["priority"] = int(row["priority"])
                records.append(row)
    return records


def _calc_risk(records: list[dict], game: str) -> str:
    """게임의 위험등급을 계산한다 (HIGH/MID/LOW)."""
    game_records = [r for r in records if r["game"] == game and r["priority"] > 0]
    if not game_records:
        return "LOW"
    avg = sum(r["priority"] for r in game_records) / len(game_records)
    if avg >= 3.5:
        return "HIGH"
    if avg >= 2.5:
        return "MID"
    return "LOW"


def _get_top3(records: list[dict]) -> list[dict]:
    """긴급도 5 이슈를 우선순위 순으로 Top3 반환한다."""
    p5 = [r for r in records if r["priority"] == 5]
    # 날짜 최신순 → 최대 3건
    p5.sort(key=lambda r: r.get("date", ""), reverse=True)
    if not p5:
        # 긴급도 5가 없으면 최고 긴급도 순
        sorted_all = sorted(records, key=lambda r: r["priority"], reverse=True)
        p5 = sorted_all
    return p5[:3]


def _generate_ai_comment(game_stats: dict, top3: list[dict]) -> tuple[str, str]:
    """Groq로 AI 코멘트와 권장 액션을 생성한다. (코멘트, 액션) 반환."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "AI 코멘트 생성 불가 (GROQ_API_KEY 없음)", ""

    stats_text = "\n".join(
        f"- {game}: 위험등급 {info['risk']}, 평균 긴급도 {info['avg_priority']:.1f}, 총 {info['count']}건"
        for game, info in game_stats.items()
    )
    issues_text = "\n".join(
        f"{i+1}. [{r['game']} · {r['category']}] {r.get('summary', r.get('review_text', ''))[:60]}"
        for i, r in enumerate(top3)
    )

    prompt = f"""다음은 게임 VOC 분석 결과다. 운영 PM을 위한 브리핑을 작성하라.

[게임별 현황]
{stats_text}

[긴급도 높은 이슈]
{issues_text}

아래 두 항목을 JSON으로 반환하라:
{{
  "comment": "전체 VOC 상황 요약 (2~3문장, 한국어)",
  "actions": ["권장 대응 액션 1", "권장 대응 액션 2", "권장 대응 액션 3"]
}}

JSON만 출력하라."""

    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.choices[0].message.content.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
        data = json.loads(text)
        comment = data.get("comment", "")
        actions = "\n".join(f"{i+1}. {a}" for i, a in enumerate(data.get("actions", [])))
        return comment, actions
    except Exception as e:
        return f"AI 코멘트 생성 실패: {e}", ""


def _build_message(game_stats: dict, top3: list[dict], comment: str, actions: str) -> str:
    today = datetime.now().strftime("%Y-%m-%d")

    risk_lines = "\n".join(
        f"• {info['label']} ({info['genre']}): {_RISK_EMOJI[info['risk']]} {info['risk']}"
        for info in game_stats.values()
    )

    issue_lines = "\n".join(
        f"{i+1}. [{r['game']} · {r['category']}] {r.get('summary', r.get('review_text', ''))[:50]}"
        for i, r in enumerate(top3)
    ) or "해당 없음"

    parts = [
        f"🎮 게임 VOC 일일 브리핑 | {today}",
        "",
        "📊 위험등급",
        risk_lines,
        "",
        "🚨 긴급도 5 이슈 Top3",
        issue_lines,
    ]

    if comment:
        parts += ["", "🤖 AI 코멘트", comment]

    if actions:
        parts += ["", "💡 권장 액션", actions]

    return "\n".join(parts)


def _send(token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": text,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())
    if not result.get("ok"):
        raise RuntimeError(f"Telegram 발송 실패: {result}")


def send_briefing(days: int = 30) -> None:
    """일일 VOC 브리핑을 텔레그램으로 발송한다."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("[reporter] TELEGRAM_BOT_TOKEN/CHAT_ID 없음 - 브리핑 스킵")
        return

    records = _load_recent(days)
    if not records:
        print("[reporter] 분석 데이터 없음 — 브리핑 스킵")
        return

    # 게임별 통계
    from config import GAMES
    game_stats = {}
    for game_key, game_info in GAMES.items():
        game_records = [r for r in records if r["game"] == game_key and r["priority"] > 0]
        avg = sum(r["priority"] for r in game_records) / len(game_records) if game_records else 0
        game_stats[game_key] = {
            "label": game_info.get("label", game_key),
            "genre": game_info["genre"],
            "risk": _calc_risk(records, game_key),
            "avg_priority": avg,
            "count": len(game_records),
        }

    top3 = _get_top3(records)
    comment, actions = _generate_ai_comment(game_stats, top3)
    message = _build_message(game_stats, top3, comment, actions)

    try:
        _send(token, chat_id, message)
        print("[reporter] 텔레그램 브리핑 발송 완료")
    except Exception as e:
        print(f"[reporter] 텔레그램 발송 실패: {e}")
