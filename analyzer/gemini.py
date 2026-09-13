import json
import os
import time

from groq import Groq, RateLimitError
from dotenv import load_dotenv

from config import get_apps, get_category_specs

load_dotenv()

_client = Groq(api_key=os.environ["GROQ_API_KEY"])
_MODEL = "openai/gpt-oss-120b"

_APPS = get_apps()

SENTIMENTS = ["부정", "중립", "긍정"]

_PROMPT_TEMPLATE = """\
아래 리뷰들을 분석하여 JSON 배열로 반환하라.

카테고리 정의 (각 카테고리의 기준을 정확히 구분해서 적용하라):
{category_specs}

각 항목은 반드시 다음 키를 포함해야 한다:
- category: 위 목록 중 정확히 하나의 이름만 그대로 사용 (번역·변형 금지): {categories}
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

# Groq 무료 티어 (openai/gpt-oss-120b): 분당 30회 요청, 분당 8,000 토큰
# TPM이 llama-3.3-70b-versatile(12,000) 대비 낮아져 배치 크기를 줄임
_REQUESTS_PER_MINUTE = 30
_BATCH_SIZE = 6
_REQUEST_INTERVAL = 60.0 / _REQUESTS_PER_MINUTE  # 2초

# 429(rate limit) 재시도: TPM 한도는 분 단위로 회복되므로 몇 초 간격으로 재시도한다.
# 응답의 "in Xms" 안내는 순간적인 토큰 여유만 반영해 실제로는 더 걸릴 때가 많아 신뢰하지 않는다.
_MAX_RETRIES = 3
_RETRY_BACKOFF = 8.0  # 초, 시도 횟수에 비례해 증가 (8s, 16s, 24s)


def _build_prompt(records: list[dict], category_specs: dict[str, str]) -> str:
    reviews = [
        {"index": i, "rating": r["rating"], "text": r["review_text"]}
        for i, r in enumerate(records)
    ]
    specs_text = "\n".join(f"- {name}: {desc}" for name, desc in category_specs.items())
    return _PROMPT_TEMPLATE.format(
        category_specs=specs_text,
        categories=" / ".join(category_specs.keys()),
        sentiments=" / ".join(SENTIMENTS),
        reviews_json=json.dumps(reviews, ensure_ascii=False, indent=2),
    )


def _parse_response(text: str) -> list[dict]:
    """응답 텍스트에서 JSON 배열을 파싱한다."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
    return json.loads(text)


def _call_groq(prompt: str):
    """Groq 호출. 429(rate limit)는 짧게 대기 후 재시도하고, 그래도 안 되면 예외를 올린다."""
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return _client.chat.completions.create(
                model=_MODEL,
                messages=[{"role": "user", "content": prompt}],
            )
        except RateLimitError as e:
            if attempt == _MAX_RETRIES:
                raise
            wait = _RETRY_BACKOFF * attempt
            print(f"[analyzer] rate limit(429) — {wait:.0f}초 후 재시도 ({attempt}/{_MAX_RETRIES})")
            time.sleep(wait)


def _analyze_batch(records: list[dict], category_specs: dict[str, str]) -> list[dict]:
    """리뷰 배치를 Groq로 분석하고 결과를 병합한 레코드를 반환한다."""
    prompt = _build_prompt(records, category_specs)
    response = _call_groq(prompt)
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


def _group_by_domain(records: list[dict]) -> dict[str, list[dict]]:
    """레코드를 앱(game 컬럼) 기준으로 소속 도메인별로 묶는다 (입력 순서 유지)."""
    groups: dict[str, list[dict]] = {}
    for r in records:
        domain = _APPS[r["game"]]["domain"]
        groups.setdefault(domain, []).append(r)
    return groups


def analyze(records: list[dict]) -> list[dict]:
    """수집된 리뷰 레코드 전체를 도메인별 카테고리를 반영해 배치 단위로 분석한다."""
    batches = []
    for domain, group in _group_by_domain(records).items():
        category_specs = get_category_specs(domain)
        for i in range(0, len(group), _BATCH_SIZE):
            batches.append((domain, category_specs, group[i: i + _BATCH_SIZE]))

    analyzed = []
    total_batches = len(batches)

    for idx, (domain, category_specs, batch) in enumerate(batches, start=1):
        print(f"[analyzer] 배치 {idx}/{total_batches} 분석 중... ({domain}, {len(batch)}건)")

        try:
            result = _analyze_batch(batch, category_specs)
            analyzed.extend(result)
            print(f"[analyzer] 배치 {idx} 완료")
        except Exception as e:
            print(f"[analyzer] 배치 {idx} 실패: {e}")
            for record in batch:
                analyzed.append({
                    **record,
                    "category": "",
                    "sentiment": "",
                    "summary": "",
                    "keywords": "",
                    "priority": 0,
                })

        if idx < total_batches:
            time.sleep(_REQUEST_INTERVAL)

    return analyzed
