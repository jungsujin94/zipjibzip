"""
extractor.py — Anthropic Claude API로 제품 USP 추출 및 카드뉴스 콘텐츠 생성
카드 구조: HOOK → PROBLEM → LIST (저장유도) → STAT (공유유도) → SOLUTION → CTA
"""

import json
import re
import os
import anthropic

SYSTEM_PROMPT = """당신은 한국 SNS 마케팅 전문가입니다.
인스타그램 카드뉴스를 제작하여 저장수·공유수·팔로워를 늘리는 것이 전문입니다.

카드뉴스 구조 원칙:
1. HOOK: "이거 내 얘기잖아?" → 스크롤 멈추게, 클릭 유도
2. COMBO: 페인포인트(3개) + 선택 포인트(3개)를 한 장에 → 공감 + 저장 동시 유도
3. REVIEW: 실제 구매자 후기 3개 요약 → 신뢰 구축, "나도 사야겠다" 유도
4. STAT: 놀라운 통계/수치 → "이거 알아?" → 공유 유도
5. SOLUTION: 제품 소개 + 가격
6. CTA: 팔로우/구매 유도

반드시 유효한 JSON만 반환하세요."""

USER_PROMPT_TEMPLATE = """아래 제품 정보를 분석해 인스타그램 카드뉴스 6장 콘텐츠를 JSON으로 반환하라.

제품 정보:
{data}

[REVIEW 카드 지침]
{review_instruction}

반환 형식 (이 구조 그대로, 다른 텍스트 없이):
{{
  "product_slug": "영문-소문자-하이픈",

  "card1": {{
    "tag": "HOOK",
    "headline": "스크롤 멈추는 30자 이내 문구. '이거 내 얘기잖아?' 느낌. 아래 유형 중 제품에 가장 어울리는 한 가지로 작성 (매 제품마다 반드시 다른 유형 선택):
    - [페인포인트 직격] 예: '하루 10시간 앉아 있는데 의자가 싸구려?' / '식탁 흠집 날까봐 유리판 깔고 사세요?'
    - [공감 상황 묘사] 예: '밥 먹다가 식탁 흔들린 적 있죠?' / '조명 켜도 거실이 어둡게 느껴질 때'
    - [질문형 저격] 예: '원형 식탁 vs 사각 식탁, 우리 집엔 어떤 게 맞을까?' / '10년 쓸 소파, 뭘 봐야 할까?'
    - [수치/팩트 후킹] 예: '세라믹 식탁, 긁힘 강도 유리의 3배' / '천연가죽 소파 수명이 합성피혁의 4배인 이유'
    - [before/after 암시] 예: '이 조명 달기 전엔 거실 사진 올리기 싫었어요' / '식탁 바꾸고 집밥이 늘었어요'
    절대 금지: 가격·금액 언급 ('XX만원', '저렴', '가성비' 등 — 가격 후킹은 절대 사용하지 말 것), '분위기가 달라진다/바뀐다' 같은 막연한 표현, '손님 오기 전', '집들이', '한숨' 등 손님·집들이 관련 클리셰 — 제품 자체의 물성·기능·사용 경험에서 후킹 포인트를 찾을 것",
    "subtext": "공감 서브카피 1줄 (25자 이내)"
  }},

  "card2": {{
    "tag": "COMBO",
    "pain_headline": "이런 고민 있으신가요?",
    "pain_points": [
      "페인포인트 1 (20자 이내, 사용자가 실제 겪는 불편)",
      "페인포인트 2 (20자 이내)",
      "페인포인트 3 (20자 이내)"
    ],
    "list_headline": "선택할 때 이것만 체크",
    "items": [
      {{"num": "01", "title": "항목 제목 (10자 이내)", "desc": "한 줄 설명 (18자 이내)"}},
      {{"num": "02", "title": "항목 제목", "desc": "한 줄 설명"}},
      {{"num": "03", "title": "항목 제목", "desc": "한 줄 설명"}}
    ]
  }},

  "card3": {{
    "tag": "REVIEW",
    "headline": "실제 구매자 후기",
    "reviews": [
{review_items}
    ],
    "overall": "전반적 만족도 한 줄 요약 (20자 이내, 예: '재구매 의사 90% 이상')"
  }},

  "card4": {{
    "tag": "STAT",
    "intro": "이거 알고 계셨나요?",
    "stat_number": "XX%",
    "stat_desc": "통계 설명 (35자 이내, 제품과 연관된 놀라운 사실)",
    "context": "당신의 상황과 연결하는 질문 (25자 이내)"
  }},

  "card5": {{
    "tag": "SOLUTION",
    "product_name": "제품 풀네임",
    "brand": "브랜드명",
    "price": "스크래핑된 실제 가격 그대로 (예: 202,400원)",
    "discount": "할인율 (예: 10% 또는 없으면 빈 문자열)",
    "highlight": "핵심 USP 한 줄 (20자 이내, 배송/마일리지/쿠폰 제외, 예: '이탈리아 정품 직수입')",
    "url": "ohou.se 또는 coupang.com"
  }},

  "card6": {{
    "tag": "CTA",
    "headline": "팔로우하면 얻는 것 (25자 이내)",
    "subtext": "다음에도 보고 싶게 만드는 문구",
    "cta_button": "link in caption",
    "url_display": "사이트 도메인"
  }},

  "caption": {{
    "hook_line": "스크롤 멈추는 한 줄 후킹 문구 + 이모지 (예: '고급진 선반 하나만 잘 두면 집들이때 인기스타 ✨')",
    "body_lines": [
      "제품 혜택/감성 라인 1 (15자 내외, 줄 끝 이모지 없음)",
      "제품 혜택/감성 라인 2 (15자 내외)",
      "마지막 라인 — 핵심 가치 정리 + 🖤 또는 관련 이모지"
    ],
    "hashtags": ["#오늘의집", "#카테고리태그1", "#카테고리태그2", "#홈스타일링", "#집꾸미기"]
  }}
}}

분석 시 반드시:
1. 가격은 제품 정보에 있는 값을 그대로 사용 (절대 만들어내지 말 것)
   REVIEW 카드(card3): 위 [REVIEW 카드 지침]에 따라 실제 리뷰를 요약하거나 창작하고, 별점 분포도 지침에 명시된 대로 반드시 따를 것.
2. STAT 수치는 독자가 "어, 이거 진짜야?" 하고 공유하고 싶을 만큼 insightful하고 believable해야 한다. 아래 원칙을 반드시 따를 것:
   [신뢰도 원칙]
   - "X명 중 Y명" 형태는 출처가 불분명해 보여 신뢰도가 낮다 — 절대 사용 금지
   - 대신 측정·관찰 가능한 수치를 사용: 시간(하루 평균 Xh/분), 비용(평균 X만원), 물리적 수치(X배 강도), 주기(평균 X년), 공식 통계 퍼센트(통계청·갤럽 출처 느낌)
   - 60~70% 구간 숫자(64%·68%·72%·73%·78% 등) 반복 절대 금지 — 매 제품마다 전혀 다른 수치·형태 사용
   - stat_desc는 수치가 왜 놀라운지 맥락을 1줄로 설명 (단순 사실 나열 금지)
   [카테고리별 참고 수치 — 교체 주기 수치는 절대 사용 금지, 아래 예시처럼 행동·심리·환경 데이터 중심으로 선택]
   - 의자/소파: 성인 하루 평균 착석 시간 10h, 허리 디스크 환자 연 190만 명(건보공단), 잘못된 좌자세 2h 지속 시 허리 압력 정상의 3배(척추연구소), 소파에서 보내는 시간 하루 평균 3h 24분(닐슨)
   - 조명: 수면 전 블루라이트 노출 시 멜라토닌 분비 최대 50% 억제(하버드 의대), 조도 500lux 이상 환경에서 집중력 15% 향상, 조명 색온도 2700K vs 6500K에서 긴장도 차이 40%(건축환경연구)
   - 식탁/테이블: 한국 가족 공동 식사 주 평균 4.1회(통계청), 식사 자리 테이블이 대화 시간에 미치는 영향 +23%(가족연구소), 세라믹 표면 강도 강화유리 대비 3배
   - 수납/선반: 정리된 공간 vs 어수선한 공간에서 집중 유지 시간 차이 2.1배(UCLA 연구), 시야에 물건이 많을수록 코르티솔 수치 평균 17% 상승, 가정 내 물건 수 평균 30만 개(LA타임스 조사), 정리 후 불안감 감소 체감률 68%(심리학 연구)
   - TV/AV: 한국인 하루 평균 TV 시청 시간 3h 12분(방통위), 시청 거리 권장치(화면 대각선의 1.5~2배) 지키는 가정 31%에 불과, 4K 콘텐츠 실제 체감 차이 임계거리 2.5m
   - 침대/수면: 한국인 평균 실제 수면 6h 28분(OECD 최하위권), 수면 중 자세 변환 횟수 평균 40~60회/야, 침대 프레임 강성이 낮을 경우 파트너 움직임 전달률 최대 68%
   - 러그/소품: 바닥 소재별 보행 시 관절 충격 흡수율 — 러그 위 보행이 맨 바닥 대비 충격 최대 30% 감소(정형외과 연구), 실내 소음 반사를 러그 한 장으로 최대 25% 저감, 거실 러그 유무에 따라 실내 체감 온도 1~2°C 차이
   - 거울/소품: 자연광 반사 거울 배치 시 체감 공간 1.5~2배 넓어 보임, 전신 거울 사용자 외출 준비 시간 평균 3분 단축, 인테리어 만족도 조사 '소품 교체' 효과 체감률 1위(오늘의집 설문)
   - 시계/벽장식: 아날로그 시계가 있는 공간에서 시간 인지 정확도 디지털 대비 1.4배 높음(인지심리 연구), 벽면 여백 70% 이상인 공간이 스트레스 감소에 효과적(환경심리학)
   - 책상/홈오피스: 재택근무자 업무 집중 방해 요소 1위 '공간 정돈 안 됨'(47%, 잡코리아), 높이 조절 책상 사용자 오후 집중도 일반 책상 대비 +19%(스탠딩 데스크 연구)
3. LIST 항목은 저장하고 싶을 만큼 유용하게
4. HOOK은 제품 카테고리 특유의 페인포인트를 정확히 저격. '분위기가 달라진다/바뀐다' 류의 막연한 표현 절대 금지 — 매 제품마다 다른 후킹 유형(페인포인트 직격·반전·상황 묘사·질문형·수치 팩트·before/after) 중 가장 임팩트 있는 것 선택
5. hashtags는 반드시 정확히 5개만 (인스타그램 정책)
6. HOOK 중복 금지 — 아래 패턴은 이미 사용했으므로 절대 재사용 금지:
   - "물건 찾는 시간", "하루 10분", "물건이 쌓여", "선반 하나 올렸을 뿐"
   - "식탁 흠집", "유리판 깔고", "그라인더 일체형", "원두 갈고"
   - "거울 앞에 서도 전신이 안 보인다면", "외출하고 후회", "전신이 잘리는"
   - 매 제품마다 완전히 다른 상황·각도에서 후킹 포인트를 찾을 것
{recent_hooks_ban}"""


def _collect_recent_hooks(output_dir: str, limit: int = 20) -> str:
    """output 폴더에서 최근 생성된 content.json 파일들의 hook headline을 수집해 ban list 문자열 반환"""
    import glob
    import os as _os

    pattern = _os.path.join(output_dir, "*_content.json")
    files = sorted(glob.glob(pattern), key=_os.path.getmtime, reverse=True)[:limit]

    hooks = []
    for f in files:
        try:
            with open(f, encoding="utf-8") as fp:
                data = json.load(fp)
            headline = data.get("card_content", {}).get("card1", {}).get("headline", "")
            if headline:
                hooks.append(f'   - "{headline}"')
        except Exception:
            continue

    if not hooks:
        return ""

    return "\n   [최근 실제 사용된 훅 — 아래 문구와 유사한 구조·표현 절대 재사용 금지]:\n" + "\n".join(hooks)


def _review_distribution(avg_rating: float) -> list:
    """평균 평점 → 5개 리뷰의 별점 분포 반환"""
    if avg_rating >= 4.9:
        return [5, 5, 5, 5, 5]
    elif avg_rating >= 4.8:
        return [5, 5, 5, 5, 4]
    elif avg_rating >= 4.5:
        return [5, 5, 5, 4, 4]
    elif avg_rating >= 4.0:
        return [5, 5, 4, 4, 4]
    else:  # 3.5~3.9
        return [5, 5, 4, 4, 3]


def _build_review_template(scraped_data: dict) -> str:
    """스크래핑 데이터에서 평균 평점을 파싱해 리뷰 템플릿 동적 생성"""
    # 평균 평점 파싱
    raw_rating = scraped_data.get("rating", "")
    avg = 4.7  # 기본값
    try:
        import re as _re
        m = _re.search(r'[\d.]+', str(raw_rating))
        if m:
            avg = float(m.group())
    except Exception:
        pass

    dist = _review_distribution(avg)

    # 실제 스크래핑된 리뷰
    scraped_reviews = scraped_data.get("reviews", [])
    if scraped_reviews:
        review_instruction = (
            f"아래 실제 스크래핑된 리뷰들을 바탕으로 각 리뷰를 40자 이내로 자연스럽게 요약하라 (구매자 말투 살리기).\n"
            f"실제 리뷰 원문:\n"
            + "\n".join(f"  - [{r.get('rating','?')}★] {r.get('text','')}" for r in scraped_reviews[:7])
            + f"\n평균 평점: {avg} → 별점 분포: {dist}"
        )
    else:
        review_instruction = (
            f"실제 리뷰 데이터 없음 → 제품 특성에 맞게 실제 구매자가 남길 법한 후기를 창작.\n"
            f"평균 평점: {avg} → 별점 분포: {dist}"
        )

    review_items = "\n".join(
        f'      {{{{"rating": {r}, "text": "리뷰 핵심 문구 요약 (40자 이내, 구매자 말투 그대로 살리기)"}}}}'
        for r in dist
    )

    return review_instruction, review_items


def extract_card_content(scraped_data: dict, api_key: str, output_dir: str = None) -> dict:
    client = anthropic.Anthropic(api_key=api_key)

    review_instruction, review_items = _build_review_template(scraped_data)

    # 최근 훅 ban list 자동 수집
    recent_hooks_ban = ""
    if output_dir and os.path.isdir(output_dir):
        recent_hooks_ban = _collect_recent_hooks(output_dir)

    user_prompt = USER_PROMPT_TEMPLATE.format(
        data=json.dumps(scraped_data, ensure_ascii=False, indent=2),
        review_instruction=review_instruction,
        review_items=review_items,
        recent_hooks_ban=recent_hooks_ban,
    )

    models = ["claude-sonnet-4-6", "claude-haiku-4-5-20251001"]
    last_error = None

    for model in models:
        try:
            print(f"[extractor] {model} 모델로 분석 중...", flush=True)
            response = client.messages.create(
                model=model,
                max_tokens=2000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}]
            )
            raw = response.content[0].text.strip()
            if "```" in raw:
                raw = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "").strip()
            result = json.loads(raw)
            print(f"[extractor] {model} 분석 완료.", flush=True)
            return result
        except anthropic.APIStatusError as e:
            print(f"[extractor] {model} 오류 ({e.status_code}), 폴백...", flush=True)
            last_error = e
        except json.JSONDecodeError as e:
            raise RuntimeError(f"JSON 파싱 실패: {e}") from e
        except Exception as e:
            raise RuntimeError(f"API 오류: {e}") from e

    raise RuntimeError(f"모든 모델 실패: {last_error}")


def validate_content(content: dict, scraped_data: dict = None) -> dict:
    """누락 필드 채우기 + 가격은 scraped_data 우선 사용"""
    # 가격 교정: scraper에서 가져온 실제 가격 우선
    if scraped_data and scraped_data.get("price"):
        if "card5" not in content:
            content["card5"] = {}
        content["card5"]["price"] = scraped_data["price"]
        if scraped_data.get("discount"):
            content["card5"]["discount"] = scraped_data["discount"]

    defaults = {
        "product_slug": "furniture-product",
        "card1": {"tag": "HOOK", "headline": "공간을 바꾸면 일상이 달라집니다", "subtext": "딱 하나만 바꿔보세요"},
        "card2": {"tag": "COMBO", "pain_headline": "이런 고민 있으신가요?",
                  "pain_points": ["공간이 너무 좁아요", "인테리어가 어려워요", "가성비 제품을 못 찾겠어요"],
                  "list_headline": "선택할 때 이것만 체크",
                  "items": [
                      {"num": "01", "title": "핵심 기능 1", "desc": "한 줄 설명"},
                      {"num": "02", "title": "핵심 기능 2", "desc": "한 줄 설명"},
                      {"num": "03", "title": "핵심 기능 3", "desc": "한 줄 설명"},
                  ]},
        "card3": {"tag": "REVIEW", "headline": "실제 구매자 후기",
                  "reviews": [
                      {"rating": 5, "text": "기대 이상으로 만족스러워요"},
                      {"rating": 5, "text": "배송도 빠르고 품질도 좋아요"},
                      {"rating": 4, "text": "인테리어에 잘 어울려요"},
                  ],
                  "overall": "재구매 의사 높음"},
        "card4": {"tag": "STAT", "intro": "이거 알고 계셨나요?",
                  "stat_number": "78%", "stat_desc": "인테리어가 기분에 영향을 준다는 연구 결과",
                  "context": "당신의 공간은 어떤가요?"},
        "card5": {"tag": "SOLUTION", "product_name": "제품명", "brand": "브랜드",
                  "price": "가격 확인", "discount": "", "highlight": "오늘의집 단독", "url": "ohou.se"},
        "card6": {"tag": "CTA", "headline": "인테리어 꿀팁 매주 업데이트",
                  "subtext": "팔로우하고 먼저 받아보세요", "cta_button": "link in caption", "url_display": "ohou.se"},
        "caption": {
            "hook_line": "공간을 바꾸면 일상이 달라집니다 ✨",
            "body_lines": ["정리도 되고", "인테리어도 되고", "한 번에 두 가지를 해결할 수 있어요 🖤"],
            "hashtags": ["#오늘의집", "#홈인테리어", "#인테리어소품", "#홈스타일링", "#집꾸미기"],
        },
    }

    for key, default_val in defaults.items():
        if key not in content or not content[key]:
            content[key] = default_val
        elif isinstance(default_val, dict):
            for sub_key, sub_default in default_val.items():
                if sub_key not in content[key] or content[key][sub_key] == "":
                    if key == "card5" and sub_key == "price" and scraped_data:
                        continue  # 이미 위에서 처리
                    content[key][sub_key] = sub_default

    # product_slug 정리
    slug = content.get("product_slug", "product")
    slug = re.sub(r'[^a-z0-9\-]', '', slug.lower().replace(" ", "-").replace("_", "-"))
    slug = re.sub(r'-+', '-', slug).strip('-')
    content["product_slug"] = slug or "furniture-product"

    return content
