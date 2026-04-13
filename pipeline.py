"""
pipeline.py — 카드뉴스 생성 메인 오케스트레이터
사용: python pipeline.py [URL]
"""

import sys
import os
import json
import subprocess
import tempfile
from typing import Optional
import requests
from dotenv import load_dotenv

from extractor import extract_card_content, validate_content
from card_renderer import render_all_cards

SUPPORTED_DOMAINS = ["ohou.se", "coupang.com"]
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
SCRAPER_JS = os.path.join(os.path.dirname(__file__), "scraper.js")


def resolve_url(url: str) -> str:
    """단축 URL(ozip.me 등)을 실제 URL로 자동 해석."""
    short_domains = ["ozip.me", "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly"]
    if any(d in url for d in short_domains):
        try:
            resp = requests.get(url, allow_redirects=True, timeout=15,
                                headers={"User-Agent": "Mozilla/5.0"})
            resolved = resp.url
            if resolved != url:
                print(f"[pipeline] 단축 URL 해석: {url} → {resolved}", flush=True)
            return resolved
        except Exception as e:
            print(f"[pipeline] URL 해석 실패, 원본 사용: {e}", flush=True)
    return url


def validate_url(url: str):
    if not url or not url.startswith("http"):
        raise ValueError(f"유효하지 않은 URL입니다: {url}")
    if not any(domain in url for domain in SUPPORTED_DOMAINS):
        raise ValueError(f"지원하지 않는 사이트입니다. 지원 사이트: {', '.join(SUPPORTED_DOMAINS)}")


def scrape_product(url: str) -> dict:
    print(f"[pipeline] 제품 페이지 스크래핑 중: {url}", flush=True)
    result = subprocess.run(
        ["node", SCRAPER_JS, url],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60
    )

    if result.returncode != 0:
        stderr_msg = result.stderr.strip()
        try:
            err = json.loads(stderr_msg)
            raise RuntimeError(f"스크래퍼 오류: {err.get('error', stderr_msg)}")
        except (json.JSONDecodeError, TypeError):
            raise RuntimeError(f"스크래퍼 실행 실패: {stderr_msg or '알 수 없는 오류'}")

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"스크래퍼 출력 파싱 실패: {e}\n출력: {result.stdout[:500]}")

    print(f"[pipeline] 스크래핑 완료: {data.get('name', '이름 없음')}", flush=True)
    return data


def download_product_images(scraped_data: dict, referer_url: str,
                            max_images: int = 5) -> list:
    """여러 각도의 제품 이미지를 최대 max_images장 다운로드해 임시 파일 경로 리스트 반환."""
    image_urls = scraped_data.get("imageUrls", [])
    if not image_urls:
        return []

    # 쿼리 파라미터 제거 후 중복 URL 제거 (같은 이미지 다른 해상도 중복 방지)
    from urllib.parse import urlparse
    seen_bases = set()
    deduped_urls = []
    for u in image_urls:
        base = urlparse(u)._replace(query="", fragment="").geturl()
        if base not in seen_bases:
            seen_bases.add(base)
            deduped_urls.append(u)
    image_urls = deduped_urls

    headers = {
        "Referer": referer_url,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "image/webp,image/apng,image/*,*/*;q=0.8"
    }

    paths = []
    for img_url in image_urls[:max_images * 2]:  # 실패 대비 여유 있게 시도
        if len(paths) >= max_images:
            break
        try:
            resp = requests.get(img_url, headers=headers, timeout=15, stream=True)
            if resp.status_code == 200 and "image" in resp.headers.get("content-type", ""):
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                for chunk in resp.iter_content(8192):
                    tmp.write(chunk)
                tmp.close()
                paths.append(tmp.name)
                print(f"[pipeline] 이미지 {len(paths)} 다운로드: {img_url[:70]}...", flush=True)
        except Exception as e:
            print(f"[pipeline] 이미지 다운로드 실패 ({img_url[:60]}...): {e}", flush=True)

    if not paths:
        print("[pipeline] 제품 이미지를 가져올 수 없어 텍스트 전용으로 진행합니다.", flush=True)
    else:
        print(f"[pipeline] 총 {len(paths)}장의 제품 이미지 다운로드 완료.", flush=True)
    return paths


def _promote_best_card1_image(paths: list) -> list:
    """birefnet으로 각 이미지의 전경 비율을 측정, 가장 선명한 제품 단독샷을 index 0으로."""
    try:
        from rembg import remove as rembg_remove, new_session as rembg_session
        import numpy as np
        from PIL import Image as PILImage
        session = rembg_session("birefnet-general")

        best_idx, best_score = 0, -1.0
        for i, p in enumerate(paths[:3]):   # 앞 3장만 비교 (속도)
            try:
                raw = PILImage.open(p).convert("RGB")
                # 256px로 축소해 빠르게 처리
                raw.thumbnail((256, 256))
                cutout = rembg_remove(raw, session=session)
                alpha = np.array(cutout.split()[3]).astype(np.float32) / 255.0
                score = float(alpha.mean())          # 전경 픽셀 비율
                print(f"[pipeline] 이미지 {i+1} 전경 비율: {score:.3f}", flush=True)
                if score > best_score:
                    best_score, best_idx = score, i
            except Exception:
                pass

        if best_idx != 0:
            print(f"[pipeline] 카드1 이미지: {best_idx+1}번 이미지 선택 (전경 비율 {best_score:.3f})", flush=True)
            paths[0], paths[best_idx] = paths[best_idx], paths[0]
    except Exception as e:
        print(f"[pipeline] 이미지 선별 실패, 원래 순서 유지: {e}", flush=True)
    return paths


def run(url: str):
    print("\n" + "=" * 60, flush=True)
    print("  카드뉴스 생성 시작", flush=True)
    print("=" * 60 + "\n", flush=True)

    # 1. URL 해석 (단축 URL 자동 처리) + 유효성 검사
    original_url = url          # 캡션용 원본 단축 URL 보존
    url = resolve_url(url)
    validate_url(url)

    # 2. .env에서 API 키 로드
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or "여기에" in api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY가 설정되지 않았습니다.\n"
            ".env 파일에 ANTHROPIC_API_KEY를 입력하세요.\n"
            "발급: https://console.anthropic.com/settings/keys"
        )

    # 3. 제품 스크래핑
    scraped_data = scrape_product(url)

    # 4. 제품 이미지 여러 장 다운로드 (최대 5장)
    product_image_paths = download_product_images(scraped_data, url, max_images=5)
    # 카드 1용 최적 이미지 선별: 배경 제거 후 전경 비율이 가장 높은 이미지를 맨 앞으로
    if len(product_image_paths) > 1:
        product_image_paths = _promote_best_card1_image(product_image_paths)

    # 5. Claude로 카드 콘텐츠 생성
    print(f"[pipeline] Claude로 USP 분석 중...", flush=True)
    card_content = extract_card_content(scraped_data, api_key)
    card_content = validate_content(card_content, scraped_data)

    # 6. 카드뉴스 PNG 렌더링
    print(f"[pipeline] 카드뉴스 이미지 생성 중...", flush=True)
    output_paths = render_all_cards(card_content, OUTPUT_DIR, product_image_paths)

    # 7. 카드 콘텐츠 JSON 저장 (retry_card1 용)
    slug = card_content.get("product_slug", "product")
    content_path = os.path.join(OUTPUT_DIR, f"{slug}_content.json")
    with open(content_path, "w", encoding="utf-8") as f:
        json.dump({"card_content": card_content, "product_url": original_url,
                   "scraped_name": scraped_data.get("name", "")}, f, ensure_ascii=False, indent=2)

    # 8. 인스타 캡션 txt 저장
    caption_path = _write_caption(card_content, original_url, OUTPUT_DIR)

    # 8. 임시 이미지 파일 정리
    for p in product_image_paths:
        if os.path.exists(p):
            os.unlink(p)

    # 9. 결과 출력
    print("\n" + "=" * 60, flush=True)
    print("  카드뉴스 생성 완료!", flush=True)
    print("=" * 60, flush=True)
    print(f"\n제품명: {scraped_data.get('name', '알 수 없음')}", flush=True)
    print(f"\n생성된 파일 ({len(output_paths)}장):", flush=True)

    card_summaries = [
        ("카드 1 (커버)", card_content["card1"].get("headline", "")),
        ("카드 2 (페인포인트)", card_content["card2"].get("headline", "")),
        ("카드 3 (솔루션)", card_content["card3"].get("tagline", "")),
        ("카드 4 (기능1)", card_content["card4"].get("feature_title", "")),
        ("카드 5 (기능2)", card_content["card5"].get("feature_title", "")),
        ("카드 6 (CTA)", card_content["card6"].get("cta_headline", "")),
    ]

    for path, (label, summary) in zip(output_paths, card_summaries):
        print(f"  [{label}] {summary}", flush=True)
        print(f"    → {path}", flush=True)

    print(f"\n캡션 파일: {caption_path}", flush=True)
    print(f"\n출력 폴더: {OUTPUT_DIR}\n", flush=True)
    return output_paths


def _write_caption(card_content: dict, product_url: str, output_dir: str) -> str:
    """인스타그램 캡션 txt 파일 생성."""
    cap = card_content.get("caption", {})
    hook    = cap.get("hook_line", "")
    lines   = cap.get("body_lines", [])
    tags    = cap.get("hashtags", [])[:5]
    slug    = card_content.get("product_slug", "product")

    DISCLAIMER = "이 포스팅은 오늘의집 큐레이터 활동의 일환으로, 구매시 이에 따른 일정액의 수수료를 제공받습니다."

    body_text = "\n".join(lines)
    hashtag_text = " ".join(tags)

    caption = (
        f"{product_url}\n"
        f"\n"
        f"{hook}\n"
        f"\n"
        f"{body_text}\n"
        f"\n"
        f"{DISCLAIMER}\n"
        f"\n"
        f"{hashtag_text}\n"
    )

    path = os.path.join(output_dir, f"{slug}_caption.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(caption)
    print(f"[pipeline] 캡션 저장: {path}", flush=True)
    return path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python pipeline.py [URL]")
        print("예시: python pipeline.py https://www.coupang.com/vp/products/XXXXX")
        sys.exit(1)

    url = sys.argv[1].strip()
    try:
        run(url)
    except Exception as e:
        print(f"\n오류 발생: {e}", file=sys.stderr)
        sys.exit(1)
