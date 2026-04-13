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
2. PROBLEM: "그래, 나도 그래서 힘들었어" → 공감, 다음 장 보게
3. LIST: 번호 리스트 → "나중에 써먹어야지" → 저장 유도
4. STAT: 놀라운 통계/수치 → "이거 알아?" → 공유 유도
5. SOLUTION: 제품 소개 + 가격
6. CTA: 팔로우/구매 유도

반드시 유효한 JSON만 반환하세요."""

USER_PROMPT_TEMPLATE = """아래 제품 정보를 분석해 인스타그램 카드뉴스 6장 콘텐츠를 JSON으로 반환하라.

제품 정보:
{data}

반환 형식 (이 구조 그대로, 다른 텍스트 없이):
{{
  "product_slug": "영문-소문자-하이픈",

  "card1": {{
    "tag": "HOOK",
    "headline": "스크롤 멈추는 30자 이내 문구. '이거 내 얘기잖아?' 느낌. 아래 유형 중 제품에 가장 어울리는 한 가지로 작성 (매 제품마다 반드시 다른 유형 선택):
    - [페인포인트 직격] 예: '하루 10시간 앉아 있는데 의자가 싸구려?' / '식탁 흠집 날까봐 유리판 깔고 사세요?'
    - [반전/놀람] 예: '이 퀄리티가 XX만원이라고?' / '이탈리아 가죽 소파가 국산보다 저렴한 이유'
    - [공감 상황 묘사] 예: '밥 먹다가 식탁 흔들린 적 있죠?' / '조명 켜도 거실이 어둡게 느껴질 때'
    - [질문형 저격] 예: '원형 식탁 vs 사각 식탁, 우리 집엔 어떤 게 맞을까?' / '10년 쓸 소파, 뭘 봐야 할까?'
    - [수치/팩트 후킹] 예: '세라믹 식탁, 긁힘 강도 유리의 3배' / '천연가죽 소파 수명이 합성피혁의 4배인 이유'
    - [before/after 암시] 예: '이 조명 달기 전엔 거실 사진 올리기 싫었어요' / '식탁 바꾸고 집밥이 늘었어요'
    절대 금지: '분위기가 달라진다/바뀐다' 같은 막연한 표현, '손님 오기 전', '집들이', '한숨' 등 손님·집들이 관련 클리셰 — 제품 자체의 물성·기능·사용 경험에서 후킹 포인트를 찾을 것",
    "subtext": "공감 서브카피 1줄 (25자 이내)"
  }},

  "card2": {{
    "tag": "PROBLEM",
    "headline": "이런 고민 있으신가요?",
    "pain_points": [
      "페인포인트 1 (25자 이내)",
      "페인포인트 2 (25자 이내)",
      "페인포인트 3 (25자 이내)"
    ]
  }},

  "card3": {{
    "tag": "LIST",
    "headline": "꼭 알아야 할 X가지",
    "save_cta": "저장해두세요",
    "items": [
      {{"num": "01", "title": "항목 제목 (12자 이내)", "desc": "한 줄 설명 (20자 이내)"}},
      {{"num": "02", "title": "항목 제목", "desc": "한 줄 설명"}},
      {{"num": "03", "title": "항목 제목", "desc": "한 줄 설명"}},
      {{"num": "04", "title": "항목 제목", "desc": "한 줄 설명"}}
    ]
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
2. STAT 수치는 아래 카테고리별 가이드를 참고해 실제 연구·통계 기반으로 생성. 60~70% 구간 숫자(64%·68%·72%·73%·78% 등) 반복 절대 금지 — 매 제품마다 전혀 다른 수치 사용. 퍼센트 외에 시간(하루 평균 Xh), 배수(X배), 절대 수치(X명 중 1명), 금액(연 X만원) 형태도 적극 활용:
   - 의자/소파: 허리통증(성인 80% 경험), 앉는 시간(하루 평균 10시간), 자세 불량(직장인 60%), 근골격계 질환 등
   - 조명: 수면 질(블루라이트 노출 50% 수면 감소), 집중력(조명 밝기에 따라 15% 향상), 멜라토닌, 눈 피로 등
   - 식탁/테이블: 가족 식사 빈도(주 3회 이하 52%), 식탁 교체 주기(평균 7년), 공간별 테이블 선호도 등
   - 수납/선반: 정리 안된 공간 스트레스(응답자 72%), 물건 찾는 시간(하루 평균 10분), 수납 부족 불만 등
   - 거울: 외출 전 전신 확인 후 자신감 향상(61%), 거울 배치가 공간 넓어 보이는 효과 등
   - 세라믹/식탁: 식탁 소재가 식사 분위기에 영향(응답자 64%), 원형 테이블 대화 활성화 효과 등
3. LIST 항목은 저장하고 싶을 만큼 유용하게
4. HOOK은 제품 카테고리 특유의 페인포인트를 정확히 저격. '분위기가 달라진다/바뀐다' 류의 막연한 표현 절대 금지 — 매 제품마다 다른 후킹 유형(페인포인트 직격·반전·상황 묘사·질문형·수치 팩트·before/after) 중 가장 임팩트 있는 것 선택
5. hashtags는 반드시 정확히 5개만 (인스타그램 정책)"""


def extract_card_content(scraped_data: dict, api_key: str) -> dict:
    client = anthropic.Anthropic(api_key=api_key)
    user_prompt = USER_PROMPT_TEMPLATE.format(
        data=json.dumps(scraped_data, ensure_ascii=False, indent=2)
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
        "card2": {"tag": "PROBLEM", "headline": "이런 고민 있으신가요?",
                  "pain_points": ["공간이 너무 좁아요", "인테리어가 어려워요", "가성비 제품을 못 찾겠어요"]},
        "card3": {"tag": "LIST", "headline": "꼭 알아야 할 4가지", "save_cta": "저장해두세요",
                  "items": [
                      {"num": "01", "title": "핵심 기능 1", "desc": "한 줄 설명"},
                      {"num": "02", "title": "핵심 기능 2", "desc": "한 줄 설명"},
                      {"num": "03", "title": "핵심 기능 3", "desc": "한 줄 설명"},
                      {"num": "04", "title": "핵심 기능 4", "desc": "한 줄 설명"},
                  ]},
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
