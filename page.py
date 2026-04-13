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
DISCLAIMER = "이 포스팅은 오늘의집 큐레이터 활동의 일환으로, 구매시 이에 따른 일정액의 수수료를 제공받습니다."


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
    url = p.get("purchase_url", "#")
    img = p.get("image", "")
    title = p.get("title", "")
    category = p.get("category", "")
    price = p.get("price", "")
    price_html = f'<p class="price">{price}</p>' if price else ""
    return f"""
    <a class="card" href="{url}" target="_blank" rel="noopener noreferrer" data-category="{category}">
      <div class="img-wrap">
        <img src="{img}" alt="{title}" loading="lazy">
      </div>
      <div class="info">
        <div class="title-group">
          <p class="title">{title}</p>
          {price_html}
        </div>
        <div class="cta">
          <img src="images/todayhouse_nobg.png" alt="오늘의집" class="cta-logo">
          <span>에서 구매하기</span>
        </div>
      </div>
    </a>"""


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

    .disclaimer {{
      text-align: center;
      font-size: 0.78rem;
      color: #aaa;
      margin-bottom: 32px;
    }}

    .tabs {{
      display: flex;
      justify-content: center;
      flex-wrap: wrap;
      gap: 8px;
      max-width: 1280px;
      margin: 0 auto 36px;
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

    .title-group {{
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}

    .title {{
      font-size: 1rem;
      font-weight: 600;
      line-height: 1.5;
    }}

    .price {{
      font-size: 0.92rem;
      font-weight: 700;
      color: #e05c2a;
    }}

    .cta {{
      display: flex;
      align-items: center;
      gap: 7px;
      background: #f5f4f0;
      border-radius: 10px;
      padding: 10px 14px;
      font-size: 0.85rem;
      font-weight: 500;
      color: #444;
    }}

    .cta-logo {{
      height: 22px;
      width: auto;
    }}
  </style>
</head>
<body>
  <img src="images/zipjibzip_nobg.png" alt="zipjibzip" class="logo">
  <p class="disclaimer">{DISCLAIMER}</p>
  <div class="tabs">
    {tabs}
  </div>
  <div class="grid">{cards}
  </div>
  <script>
    const tabs = document.querySelectorAll('.tab');
    const cards = document.querySelectorAll('.card');
    tabs.forEach(tab => {{
      tab.addEventListener('click', () => {{
        tabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        const filter = tab.dataset.filter;
        cards.forEach(card => {{
          const match = filter === '전체' || card.dataset.category === filter;
          card.classList.toggle('hidden', !match);
        }});
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
