import json
import os
import time

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

_client = Groq(api_key=os.environ["GROQ_API_KEY"])
_MODEL = "llama-3.3-70b-versatile"

CATEGORIES = ["BM", "밸런스", "강화", "서버", "운영"]
SENTIMENTS = ["부정", "중립", "긍정"]

_PROMPT_TEMPLATE = """\
아래 게임 리뷰들을 분석하여 JSON 배열로 반환하라.
각 항목은 반드시 다음 키를 포함해야 한다:
- category: {categories} 중 하나
- sentiment: {sentiments} 중 하나
- summary: 리뷰 핵심을 1~2문장으로 요약
- keywords: 핵심 키워드 3개 이내, 쉼표로 구분한 문자열
- priority: 긴급도 1~5 정수 (5가 가장 긴급)

한국어가 아닌 리뷰는 한국어로 번역 후 분석하라.

리뷰 목록 (index 순서대로 결과를 반환):
{reviews_json}

반드시 JSON 배열만 출력하고, 마크다운 코드 블록이나 다른 텍스트를 포함하지 마라.
배열 길이는 입력 리뷰 수와 동일해야 한다.
"""

# Groq 무료 티어: 분당 30회 요청 (llama-3.3-70b-versatile)
_REQUESTS_PER_MINUTE = 30
_BATCH_SIZE = 10
_REQUEST_INTERVAL = 60.0 / _REQUESTS_PER_MINUTE  # 2초


def _build_prompt(records: list[dict]) -> str:
    reviews = [
        {"index": i, "rating": r["rating"], "text": r["review_text"]}
        for i, r in enumerate(records)
    ]
    return _PROMPT_TEMPLATE.format(
        categories="、".join(CATEGORIES),
        sentiments="、".join(SENTIMENTS),
        reviews_json=json.dumps(reviews, ensure_ascii=False, indent=2),
    )


def _parse_response(text: str) -> list[dict]:
    """응답 텍스트에서 JSON 배열을 파싱한다."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
    return json.loads(text)


def _analyze_batch(records: list[dict]) -> list[dict]:
    """리뷰 배치를 Groq로 분석하고 결과를 병합한 레코드를 반환한다."""
    prompt = _build_prompt(records)
    response = _client.chat.completions.create(
        model=_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    results = _parse_response(response.choices[0].message.content)

    if len(results) != len(records):
        raise ValueError(
            f"응답 길이 불일치: 입력 {len(records)}개, 응답 {len(results)}개"
        )

    merged = []
    for record, analysis in zip(records, results):
        merged.append({
            **record,
            "category": analysis.get("category", ""),
            "sentiment": analysis.get("sentiment", ""),
            "summary": analysis.get("summary", ""),
            "keywords": analysis.get("keywords", ""),
            "priority": int(analysis.get("priority", 3)),
        })
    return merged


def analyze(records: list[dict]) -> list[dict]:
    """수집된 리뷰 레코드 전체를 배치 단위로 분석한다."""
    analyzed = []
    total = len(records)

    for i in range(0, total, _BATCH_SIZE):
        batch = records[i: i + _BATCH_SIZE]
        batch_num = i // _BATCH_SIZE + 1
        total_batches = (total + _BATCH_SIZE - 1) // _BATCH_SIZE

        print(f"[analyzer] 배치 {batch_num}/{total_batches} 분석 중... ({len(batch)}건)")

        try:
            result = _analyze_batch(batch)
            analyzed.extend(result)
            print(f"[analyzer] 배치 {batch_num} 완료")
        except Exception as e:
            print(f"[analyzer] 배치 {batch_num} 실패: {e}")
            for record in batch:
                analyzed.append({
                    **record,
                    "category": "",
                    "sentiment": "",
                    "summary": "",
                    "keywords": "",
                    "priority": 0,
                })

        if i + _BATCH_SIZE < total:
            time.sleep(_REQUEST_INTERVAL)

    return analyzed
