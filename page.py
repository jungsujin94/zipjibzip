"""
page.py — Generates index.html catalog from products/ folder.

Usage:
  python page.py          # auto-discovers products, creates products.json if missing
  python page.py --regen  # re-scans products/ and overwrites products.json

Workflow:
  1. Run once → products.json is created with placeholder purchase_url values.
  2. Edit products.json and fill in the real purchase URLs.
  3. Run again → index.html is generated, ready for GitHub Pages.
"""

import json
import sys
from pathlib import Path

PRODUCTS_DIR = Path("products")
PRODUCTS_JSON = Path("products.json")
OUTPUT_HTML = Path("index.html")
CATALOG_TITLE = "zipjibzip picks"
DISCLAIMER_OHOUSE  = "이 포스팅은 오늘의집 큐레이터 활동의 일환으로, 구매시 이에 따른 일정액의 수수료를 제공받습니다."
DISCLAIMER_COUPANG = "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."
DISCLAIMER_PRICE   = "※ 표시된 가격은 쿠폰 적용 전 가격이며, 배송비가 별도로 발생할 수 있습니다."


def slug_to_title(slug: str) -> str:
    return " ".join(w.capitalize() for w in slug.split("-"))


def discover_products() -> list[dict]:
    products = []
    seen: set[str] = set()
    for img in sorted(PRODUCTS_DIR.glob("*_card_1.png")):
        slug = img.stem[: img.stem.rfind("_card_")]
        if slug in seen:
            continue
        seen.add(slug)
        products.append(
            {
                "slug": slug,
                "title": slug_to_title(slug),
                "image": f"products/{img.name}",
                "purchase_url": "https://example.com",
                "coupang_url": "",
                "category": "",
                "ohouse price": "",
                "coupang price": "",
            }
        )
    return products


def load_products(regen: bool) -> list[dict]:
    if regen or not PRODUCTS_JSON.exists():
        products = discover_products()
        PRODUCTS_JSON.write_text(
            json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        action = "Re-generated" if regen else "Created"
        print(f"{action} {PRODUCTS_JSON} ({len(products)} products found).")
        if not regen:
            print("  → Edit products.json and fill in each 'purchase_url', then re-run.")
        return products

    with open(PRODUCTS_JSON, encoding="utf-8") as f:
        return json.load(f)


def build_card(p: dict) -> str:
    ohouse_url  = p.get("purchase_url", "#")
    img         = p.get("image", "")
    title       = p.get("title", "")
    category    = p.get("category", "")
    coupang_url = p.get("coupang_url", "")
    ohouse_price  = p.get("ohouse price") or p.get("price", "")
    coupang_price = p.get("coupang price", "")

    digits = "".join(c for c in ohouse_price if c.isdigit()) if ohouse_price else ""
    price_num = int(digits) if digits else 0
    has_coupang = bool(coupang_url)

    if has_coupang:
        cta_html = f"""<div class="cta-group">
          <a class="cta cta-ohouse" href="{ohouse_url}" target="_blank" rel="noopener noreferrer">
            <div class="cta-top">
              <img src="images/todayhouse_nobg.png" alt="오늘의집" class="cta-logo">
              <span class="cta-arrow">↗</span>
            </div>
            <span class="cta-price">{ohouse_price or '—'}</span>
          </a>
          <a class="cta cta-coupang" href="{coupang_url}" target="_blank" rel="noopener noreferrer">
            <div class="cta-top">
              <img src="images/coupang%20logo.png" alt="쿠팡" class="cta-logo">
              <span class="cta-arrow">↗</span>
            </div>
            <span class="cta-price">{coupang_price or '—'}</span>
          </a>
        </div>"""
    else:
        cta_html = f"""<div class="cta-group">
          <a class="cta cta-ohouse" href="{ohouse_url}" target="_blank" rel="noopener noreferrer">
            <div class="cta-top">
              <img src="images/todayhouse_nobg.png" alt="오늘의집" class="cta-logo">
              <span class="cta-arrow">↗</span>
            </div>
            <span class="cta-price">{ohouse_price or '—'}</span>
          </a>
        </div>"""

    return f"""
    <div class="card" data-category="{category}" data-price="{price_num}">
      <a class="img-link" href="{ohouse_url}" target="_blank" rel="noopener noreferrer">
        <div class="img-wrap">
          <img src="{img}" alt="{title}" loading="lazy">
        </div>
      </a>
      <div class="info">
        <p class="title">{title}</p>
        {cta_html}
      </div>
    </div>"""


def build_tabs(products: list[dict]) -> str:
    seen = []
    for p in products:
        cat = p.get("category", "")
        if cat and cat not in seen:
            seen.append(cat)
    tabs = '<button class="tab active" data-filter="전체">전체</button>'
    for cat in seen:
        tabs += f'\n    <button class="tab" data-filter="{cat}">{cat}</button>'
    return tabs


def generate_html(products: list[dict]) -> str:
    cards = "".join(build_card(p) for p in products)
    tabs = build_tabs(products)
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{CATALOG_TITLE}</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: 'Segoe UI', Arial, sans-serif;
      background: #f5f4f0;
      color: #1a1a1a;
      padding: 48px 24px 80px;
    }}

    .logo {{
      display: block;
      margin: 0 auto 24px;
      max-height: 144px;
      width: auto;
    }}

    .disclaimers {{
      text-align: center;
      margin-bottom: 32px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}

    .disclaimer {{
      font-size: 0.78rem;
      color: #aaa;
    }}

    .toolbar {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 16px;
      max-width: 1280px;
      margin: 0 auto 36px;
    }}

    .tabs {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      flex: 1;
    }}

    .tab {{
      border: 1.5px solid #ddd;
      background: #fff;
      border-radius: 999px;
      padding: 8px 20px;
      font-size: 0.88rem;
      font-weight: 500;
      color: #666;
      cursor: pointer;
      transition: all .18s ease;
    }}

    .tab:hover {{
      border-color: #aaa;
      color: #222;
    }}

    .tab.active {{
      background: #1a1a1a;
      border-color: #1a1a1a;
      color: #fff;
    }}

    .sort-controls {{
      display: flex;
      flex-direction: column;
      gap: 6px;
      flex-shrink: 0;
    }}

    .sort-btn {{
      border: 1.5px solid #ddd;
      background: #fff;
      border-radius: 999px;
      padding: 8px 16px;
      font-size: 0.82rem;
      font-weight: 500;
      color: #666;
      cursor: pointer;
      white-space: nowrap;
      transition: all .18s ease;
    }}

    .sort-btn:hover {{
      border-color: #aaa;
      color: #222;
    }}

    .sort-btn.active {{
      background: #1a1a1a;
      border-color: #1a1a1a;
      color: #fff;
    }}

    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 28px;
      max-width: 1280px;
      margin: 0 auto;
    }}

    .card {{
      background: #fff;
      border-radius: 16px;
      overflow: hidden;
      text-decoration: none;
      color: inherit;
      box-shadow: 0 2px 14px rgba(0, 0, 0, .07);
      transition: transform .22s ease, box-shadow .22s ease;
      display: flex;
      flex-direction: column;
    }}

    .card:hover {{
      transform: translateY(-5px);
      box-shadow: 0 10px 32px rgba(0, 0, 0, .14);
    }}

    .card.hidden {{
      display: none;
    }}

    .img-wrap {{
      width: 100%;
      aspect-ratio: 1 / 1;
      overflow: hidden;
      background: #f0ede8;
    }}

    .img-wrap img {{
      width: 100%;
      height: 100%;
      object-fit: contain;
      display: block;
      transition: transform .3s ease;
    }}

    .card:hover .img-wrap img {{
      transform: scale(1.04);
    }}

    .info {{
      padding: 20px 20px 22px;
      display: flex;
      flex-direction: column;
      gap: 14px;
      flex: 1;
      justify-content: space-between;
    }}

    .title {{
      font-size: 1rem;
      font-weight: 600;
      line-height: 1.5;
    }}

    .img-link {{
      display: block;
      text-decoration: none;
    }}

    .cta-group {{
      display: flex;
      gap: 10px;
    }}

    .cta {{
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 4px;
      border-radius: 12px;
      padding: 12px 10px;
      text-decoration: none;
      transition: filter .18s ease;
      flex: 1;
    }}

    .cta:hover {{
      filter: brightness(0.93);
    }}

    .cta-ohouse {{
      background: #f8f8f8;
      border: 1.5px solid #96C8F0;
      color: #1a1a1a;
    }}

    .cta-coupang {{
      background: #f8f8f8;
      border: 1.5px solid #F5B080;
      color: #1a1a1a;
    }}

    .cta-top {{
      display: flex;
      align-items: center;
      gap: 5px;
    }}

    .cta-logo {{
      height: 22px;
      width: auto;
      display: block;
    }}

    .cta-arrow {{
      font-size: 0.85rem;
      font-weight: 700;
      color: #333;
      line-height: 1;
    }}

    .cta-price {{
      font-size: 0.85rem;
      font-weight: 700;
    }}
  </style>
</head>
<body>
  <img src="images/zipjibzip_nobg.png" alt="zipjibzip" class="logo">
  <div class="disclaimers">
    <p class="disclaimer">{DISCLAIMER_OHOUSE}</p>
    <p class="disclaimer">{DISCLAIMER_COUPANG}</p>
    <p class="disclaimer">{DISCLAIMER_PRICE}</p>
  </div>
  <div class="toolbar">
    <div class="tabs">
      {tabs}
    </div>
    <div class="sort-controls">
      <button class="sort-btn" data-sort="asc">가격 낮은순 ↑</button>
      <button class="sort-btn" data-sort="desc">가격 높은순 ↓</button>
    </div>
  </div>
  <div class="grid">{cards}
  </div>
  <script>
    const tabs = document.querySelectorAll('.tab');
    const sortBtns = document.querySelectorAll('.sort-btn');
    const grid = document.querySelector('.grid');
    let currentFilter = '전체';
    let currentSort = null;

    function getCards() {{
      return Array.from(grid.querySelectorAll('.card'));
    }}

    function applyFilterAndSort() {{
      const cards = getCards();
      // filter visibility
      cards.forEach(card => {{
        const match = currentFilter === '전체' || card.dataset.category === currentFilter;
        card.classList.toggle('hidden', !match);
      }});
      // sort
      if (currentSort) {{
        const visible = cards.filter(c => !c.classList.contains('hidden'));
        const hidden = cards.filter(c => c.classList.contains('hidden'));
        visible.sort((a, b) => {{
          const pa = parseInt(a.dataset.price) || 0;
          const pb = parseInt(b.dataset.price) || 0;
          return currentSort === 'asc' ? pa - pb : pb - pa;
        }});
        [...visible, ...hidden].forEach(c => grid.appendChild(c));
      }}
    }}

    tabs.forEach(tab => {{
      tab.addEventListener('click', () => {{
        tabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        currentFilter = tab.dataset.filter;
        applyFilterAndSort();
      }});
    }});

    sortBtns.forEach(btn => {{
      btn.addEventListener('click', () => {{
        if (currentSort === btn.dataset.sort) {{
          // toggle off
          btn.classList.remove('active');
          currentSort = null;
        }} else {{
          sortBtns.forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          currentSort = btn.dataset.sort;
        }}
        applyFilterAndSort();
      }});
    }});
  </script>
</body>
</html>"""


def main():
    regen = "--regen" in sys.argv
    products = load_products(regen)

    if not products:
        print("No products found in products/. Add *_card_5.png images and re-run.")
        return

    html = generate_html(products)
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"Generated {OUTPUT_HTML} with {len(products)} products.")


if __name__ == "__main__":
    main()
