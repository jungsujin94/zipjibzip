"""
card_renderer.py — 1080×1350 카드뉴스 렌더러
디자인: 에디토리얼 라이트 팔레트, 제품 이미지 전 카드 활용
"""

import os
import re
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageChops, ImageOps
from rembg import remove as rembg_remove, new_session as rembg_session

_REMBG_SESSION = None

def _get_rembg_session():
    global _REMBG_SESSION
    if _REMBG_SESSION is None:
        _REMBG_SESSION = rembg_session("birefnet-general")
    return _REMBG_SESSION

W, H   = 1080, 1350
PAD    = 72
IMAGES = os.path.join(os.path.dirname(__file__), "images")
FONTS  = os.path.join(os.path.dirname(__file__), "fonts")

C = {
    "bg":           (250, 248, 243),
    "white":        (255, 255, 255),
    "border":       (224, 218, 206),
    "border_light": (238, 234, 224),
    "text":         (24,  21,  16),
    "text_mid":     (82,  76,  68),
    "text_muted":   (152, 146, 136),
    "coral":        (208, 80,  50),
    "coral_pale":   (252, 234, 224),
    "ink":          (20,  18,  14),
    "stone":        (228, 224, 214),
}

BOLD       = "C:/Windows/Fonts/malgunbd.ttf"
REG        = "C:/Windows/Fonts/malgun.ttf"
SERIF      = "C:/Windows/Fonts/NotoSerifKR-VF.ttf"      # 에디토리얼 서브텍스트
HANDWRITE  = os.path.join(FONTS, "NanumPenScript.ttf")  # 배민 스타일 캐주얼 레이블


# ── 유틸 ─────────────────────────────────────────────────────────

def strip_emoji(text: str) -> str:
    return re.sub(
        r'[\U00010000-\U0010FFFF\U0001F300-\U0001F9FF'
        r'\U00002600-\U000027BF\u200d\ufe0f\U0001FA00-\U0001FA6F]',
        '', text
    ).strip()


def F(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def wrap(text, font, max_w, draw):
    """띄어쓰기 경계 우선, 한 단어가 너무 길 때만 글자 단위로 자름."""
    if not text:
        return []
    words = text.split(' ')
    lines, cur = [], ""
    for word in words:
        if not word:
            continue
        candidate = (cur + ' ' + word).lstrip() if cur else word
        if draw.textbbox((0, 0), candidate, font=font)[2] <= max_w:
            cur = candidate
        else:
            if cur:
                lines.append(cur)
            # 단어 자체가 max_w보다 넓으면 글자 단위로 자름
            if draw.textbbox((0, 0), word, font=font)[2] > max_w:
                char_line = ""
                for ch in word:
                    test = char_line + ch
                    if draw.textbbox((0, 0), test, font=font)[2] > max_w and char_line:
                        lines.append(char_line)
                        char_line = ch
                    else:
                        char_line = test
                cur = char_line
            else:
                cur = word
    if cur:
        lines.append(cur)
    return lines


def put(draw, text, font, color, x, y, max_w,
        align="left", line_gap=10, lines=None) -> int:
    lines = lines if lines is not None else wrap(text, font, max_w, draw)
    dy = 0
    for line in lines:
        bb = draw.textbbox((0, 0), line, font=font)
        lw = bb[2] - bb[0]
        lh = bb[3] - bb[1]
        if align == "center":
            draw.text((x - lw // 2, y + dy), line, font=font, fill=color)
        elif align == "right":
            draw.text((x - lw, y + dy), line, font=font, fill=color)
        else:
            draw.text((x, y + dy), line, font=font, fill=color)
        dy += lh + line_gap
    return dy


def balanced_wrap(text, font, max_w, draw) -> list:
    """모든 줄 너비가 최대한 균등하도록 최적 줄바꿈 (binary search)."""
    lines = wrap(text, font, max_w, draw)
    n = len(lines)
    if n <= 1:
        return lines
    # n줄을 유지하는 최소 max_w를 이진탐색 → 각 줄 너비 균등화
    lo, hi = max_w // n, max_w
    while lo < hi - 2:
        mid = (lo + hi) // 2
        if len(wrap(text, font, mid, draw)) == n:
            hi = mid
        else:
            lo = mid
    return wrap(text, font, hi, draw)


def text_height(text, font, max_w, draw, line_gap=10) -> int:
    lines = wrap(text, font, max_w, draw)
    dummy = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    total = 0
    for line in lines:
        bb = dummy.textbbox((0, 0), line, font=font)
        total += (bb[3] - bb[1]) + line_gap
    return total


def make_bg() -> Image.Image:
    return Image.new("RGBA", (W, H), (*C["bg"], 255))


def warm_gradient_bg(top, bot) -> Image.Image:
    img = Image.new("RGBA", (W, H))
    dr  = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        r = int(top[0] + (bot[0]-top[0])*t)
        g = int(top[1] + (bot[1]-top[1])*t)
        b = int(top[2] + (bot[2]-top[2])*t)
        dr.line([(0,y),(W,y)], fill=(r,g,b,255))
    return img


def load_img(path, w, h, mode="fill") -> Image.Image:
    img = Image.open(path).convert("RGBA")
    iw, ih = img.size
    if mode == "fill":
        scale = max(w/iw, h/ih)
        nw, nh = int(iw*scale), int(ih*scale)
        img = img.resize((nw, nh), Image.LANCZOS)
        img = img.crop(((nw-w)//2, (nh-h)//2,
                        (nw-w)//2+w, (nh-h)//2+h))
    else:
        scale = min(w/iw, h/ih)
        nw, nh = int(iw*scale), int(ih*scale)
        img = img.resize((nw, nh), Image.LANCZOS)
    return img


def rrect(draw, box, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill,
                           outline=outline, width=width)


# ── 제품 이미지를 고스트(배경 워터마크)로 합성 ────────────────────

def ghost(base: Image.Image, prod_path: str,
          target_w: int, x: int, y: int, opacity: float = 0.18):
    """배경 제거 후 제품 실루엣만 저불투명도로 합성 (박스 테두리 없음)."""
    if not prod_path or not os.path.exists(prod_path):
        return
    try:
        raw = Image.open(prod_path).convert("RGB")
        # 배경 제거 → 제품 실루엣만 남김
        pi = remove_bg(raw)
        iw, ih = pi.size
        scale = target_w / iw
        nw, nh = int(iw * scale), int(ih * scale)
        pi = pi.resize((nw, nh), Image.LANCZOS)
        # 채도 약간 낮춤 → 크림 배경에 자연스럽게 섞임
        rgb  = pi.convert("RGB")
        gray = rgb.convert("L").convert("RGB")
        rgb  = Image.blend(rgb, gray, 0.30)
        pi_rgb = rgb.convert("RGBA")
        # 기존 알파(배경제거 마스크) × opacity
        orig_a = pi.split()[3]
        new_a  = orig_a.point(lambda p: int(p * opacity))
        pi_rgb.putalpha(new_a)
        cx = max(-nw + 1, min(x, W - 1))
        cy = max(-nh + 1, min(y, H - 1))
        base.alpha_composite(pi_rgb, (cx, cy))
    except Exception:
        pass


# ── 배경 제거 공통 유틸 ───────────────────────────────────────────

def remove_bg(img: Image.Image) -> Image.Image:
    """
    배경 제거: 코너 샘플로 밝음/어둠 감지 + 중앙 가중치로 흰 제품 보존.
    """
    orig_lum = np.array(img.convert("L")).astype(np.float32)
    h_, w_ = orig_lum.shape
    margin = max(h_ // 10, w_ // 10, 20)
    corner_lum = np.mean([
        orig_lum[:margin, :margin].mean(),
        orig_lum[:margin, -margin:].mean(),
        orig_lum[-margin:, :margin].mean(),
        orig_lum[-margin:, -margin:].mean(),
    ])

    if corner_lum < 100:
        # 어두운 배경: 어두운 픽셀 투명
        lum_alpha = np.clip((orig_lum - 25) * 6, 0, 255)
    else:
        # 밝은 배경: 밝은 픽셀 투명 (임계값 완화: 248)
        lum_alpha = np.clip((248 - orig_lum) * 5, 0, 255)

    # 중앙 가중치: 화면 중앙 픽셀은 밝아도 불투명도 보존
    # → 흰색/크림색 제품이 배경과 같은 밝기여도 중앙이면 살아남음
    y_idx = np.arange(h_)[:, np.newaxis].astype(np.float32)
    x_idx = np.arange(w_)[np.newaxis, :].astype(np.float32)
    rel_y = np.abs(y_idx - h_ / 2) / (h_ / 2)
    rel_x = np.abs(x_idx - w_ / 2) / (w_ / 2)
    # 중앙에서 멀어질수록 0에 가까워지는 가중치
    center_w = np.clip(1.0 - np.maximum(rel_y, rel_x) * 1.3, 0, 1)
    alpha = np.clip(lum_alpha + center_w * 90, 0, 255).astype(np.uint8)

    rgba = img.convert("RGBA")
    rgba.putalpha(Image.fromarray(alpha))
    return rgba


# ── 잉크 스케치 + 수채화 효과 (카드1 전용) ───────────────────────

def sketch_effect(img_path: str) -> Image.Image:
    """
    컬러 수채화 연필 스케치:
    - 원본 색상 80% 유지 → 선명한 컬러 워시
    - 가볍게 밝혀서 수채화 질감 (백지 30%)
    - Color-Dodge + DoG 연필선을 색상 위에 오버레이
    """
    img = Image.open(img_path).convert("RGB")

    # ── 1. 컬러 수채화 베이스: 색상 거의 그대로, 아주 살짝 밝히기만 ──
    soft = img.filter(ImageFilter.GaussianBlur(1.5))   # 노이즈 제거, 색면 부드럽게
    gray_rgb = soft.convert("L").convert("RGB")
    color_wash = Image.blend(soft, gray_rgb, 0.08)     # 8%만 회색화 → 색상 92% 유지
    # 아주 살짝만 밝히기 (수채화: 색상이 물로 희석된 느낌)
    paper = np.array([255, 252, 247], dtype=np.float32)
    wash_arr = np.array(color_wash).astype(np.float32)
    base_arr = wash_arr * 0.88 + paper * 0.12          # 88% 컬러 + 12% 밝힘

    # ── 2. Classic Color-Dodge 연필 스케치 ────────────────────────
    gray_l = img.convert("L")
    sharp = gray_l.filter(ImageFilter.UnsharpMask(radius=1.0, percent=150, threshold=1))
    sharp_arr = np.array(sharp).astype(np.float32)

    # 반전 블러 (연필 스케치 핵심)
    inv = 255.0 - sharp_arr
    blurred_inv = np.array(
        Image.fromarray(np.clip(inv, 0, 255).astype(np.uint8))
        .filter(ImageFilter.GaussianBlur(3.0))
    ).astype(np.float32)
    # Color dodge: sharp / (1 - blurred_inv/255)
    # 평탄 영역 → 255(흰 종이), 엣지 → 어두운 연필선
    dodge = np.clip(sharp_arr * 255.0 / np.maximum(255.0 - blurred_inv, 1.0), 0, 255)

    # 선 강도맵: 0=종이, 1=진한선
    line_strength = np.clip(1.0 - dodge / 255.0, 0, 1)
    # 약한 노이즈 선 제거, 강한 선 강조
    line_strength = np.clip(line_strength ** 0.75, 0, 1)

    # ── 3. DoG 보조 엣지 (외곽선 보강) ──────────────────────────
    g1 = np.array(sharp.filter(ImageFilter.GaussianBlur(0.8))).astype(np.float32)
    g2 = np.array(sharp.filter(ImageFilter.GaussianBlur(3.5))).astype(np.float32)
    dog = np.clip(np.abs(g1 - g2) * 3.0, 0, 255) / 255.0
    dog = np.clip(dog ** 0.70, 0, 1)

    # Color-Dodge + DoG 합산 (DoG는 보조 역할 30%)
    combined = np.clip(line_strength * 0.70 + dog * 0.40, 0, 1)
    # 약간의 블러로 브러시 느낌
    combined = np.array(
        Image.fromarray((combined * 255).astype(np.uint8))
        .filter(ImageFilter.GaussianBlur(0.4))
    ).astype(np.float32) / 255.0

    # ── 4. 베이스에 연필선 적용 ──────────────────────────────────
    # 연필 색상: 진한 네이비 (카드 배경과 어울리도록)
    pencil = np.array([38, 38, 58], dtype=np.float32)
    s = combined[..., np.newaxis]
    result_arr = base_arr * (1.0 - s * 0.82) + pencil * (s * 0.82)
    result_arr = np.clip(result_arr, 0, 255).astype(np.uint8)

    # ── 5. 종이 질감 노이즈 ──────────────────────────────────────
    rng = np.random.default_rng(42)
    noise = rng.normal(0, 2.2, result_arr.shape).astype(np.float32)
    result_arr = np.clip(result_arr.astype(np.float32) + noise, 0, 255).astype(np.uint8)

    result = Image.fromarray(result_arr)

    # ── 6. 배경 제거: birefnet 신경망으로 제품만 누끼 ──────────────
    try:
        cutout = rembg_remove(img, session=_get_rembg_session())
        clean_a = cutout.split()[3]
        result_rgba = result.convert("RGBA")
        result_rgba.putalpha(clean_a)
        return result_rgba
    except Exception:
        # OOM 등 실패 시: 배경 제거 없이 스케치 + 균일 반투명 알파로 fallback
        result_rgba = result.convert("RGBA")
        alpha = Image.new("L", result_rgba.size, 220)  # 약 86% 불투명
        result_rgba.putalpha(alpha)
        return result_rgba


# ── 페이지 번호 (우상단 미니 필) ──────────────────────────────────

def indicator(img: Image.Image, n: int, total: int = 6):
    draw  = ImageDraw.Draw(img)
    label = f"{n} / {total}"
    font  = F(REG, 22)
    bb    = draw.textbbox((0, 0), label, font=font)
    lw    = bb[2] - bb[0]
    lh    = bb[3] - bb[1]
    px1   = W - PAD - lw - 20
    py1   = PAD - 4
    px2   = W - PAD + 4
    py2   = py1 + lh + 16
    rrect(draw, [px1, py1, px2, py2],
          radius=(py2 - py1)//2, fill=C["stone"])
    draw.text((px1 + 10, py1 + 8), label, font=font, fill=C["text_mid"])


def thin_rule(draw, y, x0=None, x1=None):
    """아주 연한 구분선."""
    x0 = x0 if x0 is not None else PAD
    x1 = x1 if x1 is not None else W - PAD
    draw.rectangle([x0, y, x1, y], fill=C["border_light"])


# ── 마켓플레이스 로고 ────────────────────────────────────────────

def get_marketplace_logo(site: str, target_h: int = 64):
    candidates = {
        "ohou":    ["todayhouse logo.png", "ohou_logo.png"],
        "coupang": ["coupang logo.png",    "coupang_logo.png"],
    }
    for fname in candidates.get(site, []):
        path = os.path.join(IMAGES, fname)
        if os.path.exists(path):
            try:
                logo = Image.open(path).convert("RGBA")
                lw, lh = logo.size
                scale  = target_h / lh
                return logo.resize((int(lw*scale), target_h), Image.LANCZOS)
            except Exception:
                pass
    return None


# ══════════════════════════════════════════════════════════════════
# CARD 1 — HOOK
# ══════════════════════════════════════════════════════════════════

def render_hook(c: dict, prod_img_path: str = None) -> Image.Image:
    img = make_bg()

    # 제품 이미지 — 배경 제거 후 스케치 효과 적용, 하단 중앙에 크게
    if prod_img_path and os.path.exists(prod_img_path):
        try:
            sketch = sketch_effect(prod_img_path)

            # 하단 영역: 카드 높이의 약 58% 차지하도록 크기 조정
            target_h = int(H * 0.58)
            sw, sh = sketch.size
            scale = target_h / sh
            nw, nh = int(sw * scale), int(sh * scale)
            # 폭이 카드보다 넓으면 폭 기준으로 재조정
            if nw > int(W * 0.96):
                scale = int(W * 0.96) / sw
                nw, nh = int(sw * scale), int(sh * scale)
            sketch = sketch.resize((nw, nh), Image.LANCZOS)

            # 하단 중앙 배치
            px = (W - nw) // 2
            py = H - nh - int(H * 0.02)
            img.alpha_composite(sketch, (px, py))
        except Exception:
            pass

    draw = ImageDraw.Draw(img)

    # 헤드라인 — 좌상단 큰 텍스트
    fh = F(BOLD, 70)
    headline = strip_emoji(c.get("headline", ""))
    h1 = put(draw, headline, fh, C["text"],
             PAD, PAD + 56, int(W * 0.68), line_gap=14)

    # 서브텍스트 — NotoSerif로 에디토리얼 느낌
    fs = F(SERIF, 33)
    subtext = strip_emoji(c.get("subtext", ""))
    put(draw, subtext, fs, C["text_muted"],
        PAD, PAD + 56 + h1 + 22, int(W * 0.65), line_gap=8)

    indicator(img, 1)
    return img.convert("RGB")


# ══════════════════════════════════════════════════════════════════
# CARD 2 — PROBLEM
# ══════════════════════════════════════════════════════════════════

def render_problem(c: dict, prod_img_path: str = None) -> Image.Image:
    img = make_bg()

    # 고스트 이미지 — 우하단
    ghost(img, prod_img_path,
          target_w=int(W * 0.75), x=int(W * 0.32), y=int(H * 0.35),
          opacity=0.16)

    draw = ImageDraw.Draw(img)

    # 헤드라인
    fh = F(BOLD, 64)
    headline = c.get("headline", "이런 고민 있으신가요?")
    h1 = put(draw, headline, fh, C["text"], PAD, PAD + 52, W - PAD*2, line_gap=12)

    thin_rule(draw, PAD + 52 + h1 + 24)

    # 페인포인트 — 가운데 정렬, 카드 잔여 공간에 균등 분포
    pts     = c.get("pain_points", [])[:3]
    ft      = F(SERIF, 42)
    fn      = F(BOLD, 26)
    cx      = W // 2
    text_w  = W - PAD * 3

    # 각 아이템 실제 높이 측정
    _dd     = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    nb_s    = _dd.textbbox((0, 0), "01", font=fn)
    num_h   = (nb_s[3] - nb_s[1]) + 10
    item_heights = [num_h + text_height(pt, ft, text_w, _dd, line_gap=8)
                    for pt in pts]

    avail_top = PAD + 52 + h1 + 64
    avail_bot = H - PAD - 40
    avail_h   = avail_bot - avail_top
    total_content = sum(item_heights)
    n = len(pts)
    # 균등 간격: 아이템 위아래 포함 n+1 개의 같은 여백
    gap = max(20, (avail_h - total_content) // (n + 1))

    cy = avail_top + gap
    for i, (pt, ih) in enumerate(zip(pts, item_heights)):
        num = f"{i+1:02d}"
        nb  = draw.textbbox((0, 0), num, font=fn)
        draw.text((cx - (nb[2]-nb[0])//2, cy), num, font=fn, fill=C["coral"])
        put(draw, pt, ft, C["text"],
            cx, cy + num_h, text_w, align="center", line_gap=8)
        cy += ih + gap
        # 구분선 (마지막 제외)
        if i < n - 1:
            sep_y = cy - gap // 2
            draw.line([(cx - 50, sep_y), (cx + 50, sep_y)],
                      fill=C["coral_pale"], width=1)

    indicator(img, 2)
    return img.convert("RGB")


# ══════════════════════════════════════════════════════════════════
# CARD 3 — LIST
# ══════════════════════════════════════════════════════════════════

def render_list(c: dict, prod_img_path: str = None) -> Image.Image:
    img = make_bg()

    # 고스트 이미지 — 우하단, 크게
    ghost(img, prod_img_path,
          target_w=int(W * 0.65), x=int(W * 0.42), y=int(H * 0.42),
          opacity=0.13)

    draw = ImageDraw.Draw(img)

    # 헤드라인 + 저장 뱃지
    fh       = F(BOLD, 54)
    headline = c.get("headline", "")
    save_txt = c.get("save_cta", "저장해두세요")
    fs_save  = F(HANDWRITE, 26)  # 배민스타일 손글씨 레이블
    sb       = draw.textbbox((0, 0), save_txt, font=fs_save)
    sw       = sb[2] - sb[0]

    h1 = put(draw, headline, fh, C["text"],
             PAD, PAD + 44, W - PAD*2 - sw - 56, line_gap=10)

    # 저장 뱃지 (우측)
    bx1 = W - PAD - sw - 28
    by1 = PAD + 44
    bx2 = W - PAD
    by2 = by1 + 40
    rrect(draw, [bx1, by1, bx2, by2], radius=20, fill=C["coral_pale"])
    draw.text((bx1 + 14, by1 + 10), save_txt,
              font=fs_save, fill=C["coral"])

    thin_rule(draw, PAD + 44 + h1 + 20)

    # 아이템
    items   = c.get("items", [])[:4]
    start_y = PAD + 44 + h1 + 50
    avail   = H - start_y - PAD - 48
    n       = max(len(items), 1)
    item_h  = min(avail // n - 8, 210)

    ft = F(BOLD, 34)
    fd = F(SERIF, 27)   # 항목 설명은 NotoSerif로 가독성

    for i, item in enumerate(items):
        iy  = start_y + i * (item_h + 8)
        num = item.get("num", f"0{i+1}")
        tx  = PAD + 74
        tw  = W - PAD - tx - 16

        # 제목·설명 높이 미리 계산 (수직 중앙 정렬용)
        title_str = item.get("title", "")
        desc_str  = item.get("desc", "")
        title_h   = text_height(title_str, ft, tw, draw, line_gap=4)
        desc_b    = draw.textbbox((0, 0), desc_str, font=fd)
        desc_h_1  = desc_b[3] - desc_b[1]   # 단일 줄 높이
        gap       = 8
        block_h   = title_h + gap + desc_h_1 + 10  # pill 패딩 포함
        text_top  = iy + (item_h - block_h) // 2

        # 번호 원 — 텍스트 블록 중앙에 맞춤
        cx_ = PAD + 26
        cy_ = iy + item_h // 2
        r_  = 24
        draw.ellipse([cx_-r_, cy_-r_, cx_+r_, cy_+r_],
                     fill=C["coral_pale"])
        fn_ = F(BOLD, 20)
        nb_ = draw.textbbox((0, 0), num, font=fn_)
        draw.text((cx_ - (nb_[2]-nb_[0])//2,
                   cy_ - (nb_[3]-nb_[1])//2 - 1),
                  num, font=fn_, fill=C["coral"])

        # 제목
        put(draw, title_str, ft, C["text"],
            tx, text_top, tw, line_gap=4)

        # 설명 — pill 배경 + 진한 텍스트
        desc_y = text_top + title_h + gap
        desc_w = draw.textbbox((0, 0), desc_str, font=fd)[2] - draw.textbbox((0, 0), desc_str, font=fd)[0]
        pill_pad_x, pill_pad_y = 14, 5
        pill_x1 = tx - pill_pad_x
        pill_y1 = desc_y - pill_pad_y
        pill_x2 = tx + min(desc_w, tw) + pill_pad_x
        pill_y2 = desc_y + desc_h_1 + pill_pad_y
        rrect(draw, [pill_x1, pill_y1, pill_x2, pill_y2],
              radius=16, fill=C["stone"])
        put(draw, desc_str, fd, C["text_mid"],
            tx, desc_y, tw, line_gap=2)

        if i < len(items) - 1:
            thin_rule(draw, iy + item_h + 2, x0=PAD + 60)

    indicator(img, 3)
    return img.convert("RGB")


# ══════════════════════════════════════════════════════════════════
# CARD 4 — STAT
# ══════════════════════════════════════════════════════════════════

def render_stat(c: dict, prod_img_path: str = None) -> Image.Image:
    img  = warm_gradient_bg(C["bg"], (248, 243, 228))

    # 고스트 이미지 — 중앙 오른쪽, 배경처럼
    ghost(img, prod_img_path,
          target_w=int(W * 0.70), x=int(W * 0.28), y=int(H * 0.22),
          opacity=0.12)

    draw = ImageDraw.Draw(img)
    cx   = W // 2

    fi = F(HANDWRITE, 34)  # 인트로 라인 손글씨 감성
    fd = F(SERIF, 32)      # 통계 설명은 세리프체
    fq = F(BOLD, 38)

    intro     = c.get("intro", "이거 알고 계셨나요?")
    num       = c.get("stat_number", "—")
    stat_desc = c.get("stat_desc", "")
    context   = strip_emoji(c.get("context", ""))
    desc_max  = W - PAD * 2 - 48

    # 숫자 폰트: 텍스트 폭이 카드 너비를 넘지 않도록 자동 축소
    num_max_w = W - PAD * 2 - 32
    fn_size = 148
    fn = F(BOLD, fn_size)
    while fn_size > 48:
        nb_test = draw.textbbox((0, 0), num, font=fn)
        if (nb_test[2] - nb_test[0]) <= num_max_w:
            break
        fn_size -= 8
        fn = F(BOLD, fn_size)

    show_intro = bool(intro)
    ib         = draw.textbbox((0, 0), intro, font=fi) if show_intro else (0, 0, 0, 0)
    intro_h    = (ib[3] - ib[1]) if show_intro else 0
    nb         = draw.textbbox((0, 0), num, font=fn)
    num_w      = nb[2] - nb[0]
    num_h_safe = fn_size + 16
    desc_lines  = balanced_wrap(stat_desc, fd, desc_max, draw)
    _dd = ImageDraw.Draw(Image.new("RGBA", (2, 2)))
    desc_text_h = sum(
        (_dd.textbbox((0,0), l, font=fd)[3] - _dd.textbbox((0,0), l, font=fd)[1]) + 8
        for l in desc_lines
    )
    desc_card_h = desc_text_h + 52
    ctx_h       = text_height(context, fq, W - PAD*2, draw, line_gap=8)

    intro_block = (intro_h + 36) if show_intro else 0
    total_h = (intro_block
               + num_h_safe + 14 + 52
               + desc_card_h + 44 + ctx_h)
    y = max((H - total_h) // 2, PAD + 32)

    # 인트로 (있을 때만)
    if show_intro:
        iw = ib[2] - ib[0]
        draw.text((cx - iw//2, y), intro, font=fi, fill=C["text_muted"])
        y += intro_h + 36

    # 숫자
    draw.text((cx - num_w//2, y), num, font=fn, fill=C["ink"])
    y += num_h_safe + 14 + 52

    # 설명 카드
    rrect(draw, [PAD+24, y, W-PAD-24, y+desc_card_h],
          radius=20, fill=C["white"],
          outline=C["border_light"], width=1)
    put(draw, stat_desc, fd, C["text_mid"],
        cx, y+26, desc_max, align="center", line_gap=8, lines=desc_lines)
    y += desc_card_h + 44

    # 질문
    put(draw, context, fq, C["coral"],
        cx, y, W-PAD*2, align="center", line_gap=8)

    indicator(img, 4)
    return img.convert("RGB")


# ══════════════════════════════════════════════════════════════════
# CARD 5 — SOLUTION  (제품 + 가격 + 포인트 3가지)
# ══════════════════════════════════════════════════════════════════

def render_solution(c: dict, prod_img_path: str = None,
                    features: list = None) -> Image.Image:
    img = make_bg()

    # 제품 이미지 — 우측: 배경 제거 후 제품만 표시
    if prod_img_path and os.path.exists(prod_img_path):
        try:
            raw   = Image.open(prod_img_path).convert("RGB")
            pi    = remove_bg(raw)          # 배경 제거 RGBA
            iw, ih = pi.size
            # 높이 기준으로 카드 높이에 맞게 스케일
            scale = H / ih
            nw, nh = int(iw * scale), H
            pi = pi.resize((nw, nh), Image.LANCZOS)
            # 좌측 페이드 (텍스트 영역과 자연스럽게 겹치도록)
            orig_a = np.array(pi.split()[3]).astype(np.float32)
            fade_w = min(200, nw // 3)
            for dx in range(fade_w):
                orig_a[:, dx] *= dx / fade_w
            pi.putalpha(Image.fromarray(np.clip(orig_a, 0, 255).astype(np.uint8)))
            # 우측 중앙 배치
            px = W - nw + max(0, (nw - int(W * 0.58)) // 2)
            img.alpha_composite(pi, (px, 0))
        except Exception:
            pass

    # 텍스트 영역 다크 패널 — 배경 이미지 위에 가독성 확보
    panel_w = int(W * 0.60)
    panel   = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd      = ImageDraw.Draw(panel)
    # 좌측 불투명 → 우측 투명 그라디언트 패널
    fade_start = int(panel_w * 0.72)
    for x in range(panel_w):
        if x < fade_start:
            a = 210
        else:
            a = int(210 * (1 - (x - fade_start) / (panel_w - fade_start)))
        pd.line([(x, 0), (x, H)], fill=(18, 16, 12, a))
    img = Image.alpha_composite(img, panel)

    draw   = ImageDraw.Draw(img)
    text_w = int(W * 0.54) - PAD

    # 브랜드
    brand = re.sub(r'\s*[\(（].*?[\)）]', '', c.get("brand", "")).strip()
    put(draw, brand, F(REG, 26), (180, 175, 165), PAD, PAD + 52, text_w)

    # 제품명 — 길이에 따라 폰트 크기 자동 축소 (최대 2줄)
    raw_name = c.get("product_name", "")
    name     = re.sub(r'\s*[\(（].*?[\)）]', '', raw_name).strip() or raw_name
    for fs in (50, 42, 36, 30):
        fn    = F(BOLD, fs)
        lines = wrap(name, fn, text_w, draw)
        if len(lines) <= 2:
            break
    if len(lines) > 2:
        words = name.split()
        while len(words) > 1:
            words.pop()
            candidate = " ".join(words) + "…"
            lines = wrap(candidate, fn, text_w, draw)
            if len(lines) <= 2:
                name = candidate
                break
    h1       = put(draw, name, fn, C["white"], PAD, PAD + 90, text_w, line_gap=10)
    name_bot = PAD + 90 + h1

    # highlight 배지
    highlight = c.get("highlight", "")
    _noise    = ("배송", "마일리지", "쿠폰", "→", "할인")
    if any(n in highlight for n in _noise) or len(highlight) > 22:
        highlight = ""
    badge_y = name_bot + 20
    if highlight:
        fhi = F(REG, 24)
        hib = draw.textbbox((0, 0), highlight, font=fhi)
        hiw = hib[2] - hib[0]
        rrect(draw, [PAD, badge_y, PAD + hiw + 28, badge_y + 40],
              radius=20, fill=C["coral"])
        draw.text((PAD + 14, badge_y + 9), highlight,
                  font=fhi, fill=C["white"])
        badge_y += 56

    # 핵심 포인트 (card3 items 활용)
    feats = (features or [])[:3]
    if feats:
        thin_rule(draw, badge_y + 8, x0=PAD, x1=int(W * 0.50))
        fy   = badge_y + 28
        ft_  = F(BOLD, 30)
        fd_  = F(SERIF, 25)
        feat_x_off = int(draw.textbbox((0, 0), "· ", font=ft_)[2])
        feat_text_w = text_w - feat_x_off
        for feat in feats:
            title = feat.get("title", "")
            desc  = feat.get("desc", "")
            draw.text((PAD, fy), "·", font=ft_, fill=C["coral"])
            title_h = put(draw, title, ft_, C["white"],
                          PAD + feat_x_off, fy, feat_text_w)
            fy_ = fy + title_h + 4
            desc_h = put(draw, desc, fd_, (190, 185, 175),
                         PAD + feat_x_off, fy_, feat_text_w)
            fy += title_h + 4 + desc_h + 14  # 동적 간격
        badge_y = fy + 8

    # 할인율
    discount = c.get("discount", "")
    price_y  = badge_y + 24
    if discount:
        put(draw, f"{discount} 할인", F(BOLD, 28), C["coral"],
            PAD, price_y, text_w)
        price_y += 44

    # 가격
    price = c.get("price", "")
    fp    = F(BOLD, 84)
    price_y = min(price_y, H - fp.size - PAD)  # 카드 하단 이탈 방지
    draw.text((PAD, price_y), price, font=fp, fill=C["white"])

    indicator(img, 5)
    return img.convert("RGB")


# ══════════════════════════════════════════════════════════════════
# CARD 6 — CTA
# ══════════════════════════════════════════════════════════════════

def render_cta(c: dict, site: str = "ohou",
               prod_img_path: str = None) -> Image.Image:
    img = make_bg()

    # 고스트 이미지 — 하단 중앙
    ghost(img, prod_img_path,
          target_w=int(W * 0.72), x=int(W * 0.14), y=int(H * 0.36),
          opacity=0.14)

    draw = ImageDraw.Draw(img)
    cx   = W // 2

    # 마켓플레이스 로고
    logo     = get_marketplace_logo(site, target_h=68)
    logo_bot = PAD + 72
    if logo:
        lw, lh = logo.size
        lx     = cx - lw // 2
        ly     = PAD + 52
        overlay = Image.new("RGBA", (W, H), (*C["bg"], 0))
        overlay.alpha_composite(logo, (lx, ly))
        img  = Image.alpha_composite(img, overlay)
        draw = ImageDraw.Draw(img)
        logo_bot = ly + lh + 36

    thin_rule(draw, logo_bot, x0=cx-72, x1=cx+72)

    # 헤드라인
    fh       = F(BOLD, 56)
    headline = strip_emoji(c.get("headline", ""))
    head_y   = logo_bot + 40
    h1 = put(draw, headline, fh, C["text"],
             cx, head_y, W - PAD*2, align="center", line_gap=12)

    # 서브텍스트 — NotoSerif 에디토리얼 감성
    fs      = F(SERIF, 32)
    subtext = strip_emoji(c.get("subtext", ""))
    sub_y   = head_y + h1 + 16
    h2 = put(draw, subtext, fs, C["text_mid"],
             cx, sub_y, W - PAD*2, align="center", line_gap=8)

    # CTA 버튼
    btn_y = sub_y + h2 + 64
    btn_w = 560
    btn_h = 96
    btn_x = cx - btn_w // 2
    rrect(draw, [btn_x, btn_y, btn_x+btn_w, btn_y+btn_h],
          radius=btn_h//2, fill=C["coral"])
    fb      = F(BOLD, 38)
    btn_txt = c.get("cta_button", "link in caption")
    bb      = draw.textbbox((0, 0), btn_txt, font=fb)
    draw.text((cx - (bb[2]-bb[0])//2,
               btn_y + (btn_h-(bb[3]-bb[1]))//2 - 2),
              btn_txt, font=fb, fill=C["white"])

    # 면책 고지 — 다크 배경 + 흰 글씨
    fd      = F(REG, 17)
    disc    = "이 포스팅은 오늘의집 큐레이터 활동의 일환으로, 구매시 이에 따른 일정액의 수수료를 제공받습니다."
    d_pad_x = 20
    d_pad_y = 14
    d_max_w = W - PAD * 2 - d_pad_x * 2
    # 실제 줄 수 / 높이를 먼저 측정
    disc_lines = wrap(disc, fd, d_max_w, draw)
    _dummy     = ImageDraw.Draw(Image.new("RGBA", (2, 2)))
    disc_h     = sum(
        (_dummy.textbbox((0,0), l, font=fd)[3] - _dummy.textbbox((0,0), l, font=fd)[1]) + 6
        for l in disc_lines
    )
    d_box_h = disc_h + d_pad_y * 2
    d_box_y = H - 20 - d_box_h          # 하단 20px 여백 고정
    rrect(draw,
          [PAD - 4, d_box_y, W - PAD + 4, d_box_y + d_box_h],
          radius=10, fill=(20, 18, 14))
    put(draw, disc, fd, (210, 205, 195),
        cx, d_box_y + d_pad_y, d_max_w, align="center", line_gap=6)

    indicator(img, 6)
    return img.convert("RGB")


# ══════════════════════════════════════════════════════════════════
# 메인 API
# ══════════════════════════════════════════════════════════════════

def render_all_cards(content: dict, output_dir: str,
                     product_image_paths=None) -> list:
    """
    product_image_paths: str (단일 경로) 또는 list[str] (여러 뷰)
    카드별로 다른 제품 이미지 뷰를 배정해 시각적 다양성을 높임.
      카드1 (sketch) → imgs[0]  가장 깔끔한 정면 히어로샷
      카드2 (ghost)  → imgs[1]  다른 앵글/측면
      카드3 (ghost)  → imgs[2]  디테일 or 라이프스타일
      카드4 (ghost)  → imgs[1]  (2 없으면 1 재사용)
      카드5 (solid)  → imgs[0]  히어로샷 (가격 카드라 제일 선명하게)
      카드6 (ghost)  → imgs[3 or 2]  마지막 뷰
    """
    os.makedirs(output_dir, exist_ok=True)
    slug     = content.get("product_slug", "product")
    site_url = content.get("card5", {}).get("url", "ohou.se")
    site_key = "coupang" if "coupang" in site_url else "ohou"
    features = content.get("card3", {}).get("items", [])

    # 단일 문자열을 리스트로 통일
    if isinstance(product_image_paths, str):
        product_image_paths = [product_image_paths]
    imgs = product_image_paths or []

    def pick(idx: int) -> str:
        """유효한 이미지 경로 반환 (없으면 None)."""
        if not imgs:
            return None
        path = imgs[min(idx, len(imgs) - 1)]
        return path if os.path.exists(path) else None

    cards = [
        (1, lambda: render_hook    (content["card1"], pick(0))),
        (2, lambda: render_problem (content["card2"], pick(1))),
        (3, lambda: render_list    (content["card3"], pick(2))),
        (4, lambda: render_stat    (content["card4"], pick(1))),
        (5, lambda: render_solution(content["card5"], pick(0), features)),
        (6, lambda: render_cta     (content["card6"], site_key, pick(3))),
    ]

    paths = []
    for num, fn in cards:
        print(f"[renderer] 카드 {num}/6 렌더링 중...", flush=True)
        img = fn()
        fp  = os.path.join(output_dir, f"{slug}_card_{num}.png")
        img.save(fp, "PNG", optimize=True)
        print(f"[renderer] 저장: {fp}", flush=True)
        paths.append(fp)
    return paths


# ── 테스트 ────────────────────────────────────────────────────────

if __name__ == "__main__":
    mock = {
        "product_slug": "design-test",
        "card1": {"headline": "방 분위기, 조명 하나로 180° 바뀝니다",
                  "subtext":  "아직도 형광등 쓰고 계신가요?"},
        "card2": {"headline": "이런 고민 있으신가요?",
                  "pain_points": ["밝기 하나뿐, 분위기 연출이 안 돼요",
                                  "예쁜 조명은 너무 비싸거나 촌스러워요",
                                  "인테리어랑 따로 노는 조명에 지쳤어요"]},
        "card3": {"headline": "무드등 고를 때 꼭 알아야 할 4가지",
                  "save_cta": "저장해두세요",
                  "items": [{"num":"01","title":"삼색 변환 기능",   "desc":"공간 용도별 빛 색상 조절"},
                             {"num":"02","title":"미드센츄리 디자인","desc":"어떤 인테리어에도 자연스럽게"},
                             {"num":"03","title":"이탈리아 정품",    "desc":"Artemide 브랜드 정품 수입"},
                             {"num":"04","title":"무료 배송",        "desc":"추가 설치비 없이 집까지"}]},
        "card4": {"intro": "이거 알고 계셨나요?",
                  "stat_number": "68%",
                  "stat_desc":   "사람들은 조명만 바꿔도 공간 만족도가 크게 올랐다고 응답했습니다",
                  "context":     "당신의 방은 지금 몇 점인가요?"},
        "card5": {"product_name": "베이글 EDITION II 단스탠드 LED 무드등",
                  "brand":        "어반아트리",
                  "price":        "369,000원",
                  "discount":     "",
                  "highlight":    "이탈리아 정품 직수입",
                  "url":          "store.ohou.se"},
        "card6": {"headline": "팔로우하면 인테리어 꿀팁 먼저 받아요",
                  "subtext":  "다음 콘텐츠도 놓치지 마세요",
                  "cta_button": "link in caption"},
    }
    paths = render_all_cards(mock, "output", [])
    for p in paths:
        print(" ", p)
