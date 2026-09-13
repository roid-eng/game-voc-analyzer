DOMAINS = {
    "game": {
        "label": "게임",
        "emoji": "🎮",
        "channel": "google_play",
        "categories": {
            "BM": "과금 구조, 아이템 가격, 확률 관련 불만",
            "밸런스": "직업/스킬/PvP 밸런스 이슈",
            "강화": "강화 시스템, 확률, 결과 불만",
            "서버": "렉, 점검, 서버 안정성, 버그",
            "운영": "GM 대응, 제재, 공지, 이벤트 운영",
        },
        "apps": {
            "lineage_m": {
                "app_id": "com.ncsoft.lineagem",
                "genre": "MMORPG",
                "label": "리니지M",
            },
            "browndust2": {
                "app_id": "com.neowizgames.game.browndust2",
                "genre": "전략RPG",
                "label": "브라운더스트2",
            },
        },
    },
    "health": {
        "label": "헬스",
        "emoji": "💊",
        "channel": "google_play",
        "categories": {
            "데이터정확도": "앱이 정상 동작하는 상태에서 측정값(걸음수·심박수·거리·수면 등 실제 수치)이 부정확하게 나오는 경우",
            "앱안정성": "기기 간 연동/동기화 실패, 크래시, 로그인·로그아웃 문제 등 기능 자체가 정상 동작하지 않는 경우",
            "UX/UI": "사용성, 화면 구성, 접근성 관련 불만",
            "구독과금": "프리미엄 구독, 결제, 환불 관련 불만",
            "알림개인정보": "알림 과다/누락, 개인정보·건강데이터 처리 우려",
            "운영대응": "CS 응대, 업데이트 공지, 정책 변경 대응",
        },
        "apps": {
            "samsung_health": {
                "app_id": "com.sec.android.app.shealth",
                "genre": "헬스케어",
                "label": "삼성헬스",
            },
        },
    },
}


def get_apps(domain: str | None = None) -> dict:
    """도메인의 앱 설정을 앱 키 기준으로 평탄화해 반환한다.
    domain을 지정하지 않으면 전체 도메인의 앱을 합쳐서 반환한다."""
    keys = [domain] if domain else list(DOMAINS.keys())
    apps = {}
    for key in keys:
        for app_key, app_info in DOMAINS[key]["apps"].items():
            apps[app_key] = {**app_info, "domain": key}
    return apps


def get_categories(domain: str) -> list[str]:
    """도메인의 분석 카테고리 이름 목록을 반환한다."""
    return list(DOMAINS[domain]["categories"].keys())


def get_category_specs(domain: str) -> dict[str, str]:
    """도메인의 분석 카테고리 이름→설명 매핑을 반환한다."""
    return DOMAINS[domain]["categories"]


# 하위 호환: game 도메인 앱만 담은 기존 GAMES 형태 (game 파이프라인 코드가 참조)
GAMES = get_apps("game")
