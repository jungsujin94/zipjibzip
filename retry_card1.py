"""
retry_card1.py — card 1 이미지만 다시 렌더링
사용: python retry_card1.py [slug] [image_index(1부터)]
예시: python retry_card1.py matt-silver-steel-magnetic-sliding-mirror 2
      → 이미지 2번으로 card_1 재렌더링 (Claude API 재호출 없음)
"""

import sys
import os
import json
import tempfile
import requests
from dotenv import load_dotenv

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
SCRAPER_JS = os.path.join(os.path.dirname(__file__), "scraper.js")


def run(slug: str, image_index: int):
    # 1. 저장된 콘텐츠 JSON 로드
    content_path = os.path.join(OUTPUT_DIR, f"{slug}_content.json")
    if not os.path.exists(content_path):
        raise RuntimeError(f"콘텐츠 파일 없음: {content_path}\n먼저 pipeline.py를 실행하세요.")

    with open(content_path, "r", encoding="utf-8") as f:
        saved = json.load(f)

    card_content = saved["card_content"]
    product_url  = saved.get("product_url", "")

    # 2. 제품 이미지 다시 스크래핑 → 다운로드
    import subprocess
    from pipeline import resolve_url, scrape_product, download_product_images, _promote_best_card1_image

    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

    resolved_url = resolve_url(product_url)
    print(f"[retry] 제품 스크래핑: {resolved_url[:60]}...", flush=True)
    scraped_data = scrape_product(resolved_url)

    print(f"[retry] 이미지 다운로드 중...", flush=True)
    paths = download_product_images(scraped_data, resolved_url, max_images=5)

    if not paths:
        raise RuntimeError("이미지 다운로드 실패")

    print(f"[retry] 다운로드된 이미지 수: {len(paths)}", flush=True)
    for i, p in enumerate(paths):
        print(f"  이미지 {i+1}: {p}", flush=True)

    # 3. 지정한 인덱스 이미지를 맨 앞으로
    idx = image_index - 1  # 1-based → 0-based
    if idx < 0 or idx >= len(paths):
        raise RuntimeError(f"이미지 인덱스 범위 초과: {image_index} (총 {len(paths)}장)")

    if idx != 0:
        paths[0], paths[idx] = paths[idx], paths[0]
    print(f"[retry] {image_index}번 이미지로 card 1 렌더링", flush=True)

    # 4. card 1만 렌더링
    from card_renderer import render_hook
    out_path = os.path.join(OUTPUT_DIR, f"{slug}_card_1.png")
    img = render_hook(card_content["card1"], paths[0])
    img.save(out_path)
    print(f"[retry] 저장: {out_path}", flush=True)

    # 5. 임시 파일 정리
    for p in paths:
        if os.path.exists(p):
            os.unlink(p)

    print(f"\n완료! card_1 재렌더링: {out_path}", flush=True)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("사용법: python retry_card1.py [slug] [image_index]")
        print("예시:   python retry_card1.py matt-silver-steel-magnetic-sliding-mirror 2")
        sys.exit(1)

    slug_arg  = sys.argv[1].strip()
    img_idx   = int(sys.argv[2].strip())

    try:
        run(slug_arg, img_idx)
    except Exception as e:
        print(f"\n오류: {e}", file=sys.stderr)
        sys.exit(1)
