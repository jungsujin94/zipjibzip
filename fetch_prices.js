/**
 * fetch_prices.js — 각 제품의 쿠폰 적용가를 스크래핑하여 products.json에 저장
 * 사용: node fetch_prices.js
 */

const { chromium } = require('playwright-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const fs = require('fs');
const path = require('path');

chromium.use(StealthPlugin());

const PRODUCTS_JSON = path.join(__dirname, 'products.json');

function detectSite(url) {
  if (url.includes('ohou.se')) return 'ohou';
  if (url.includes('coupang.com')) return 'coupang';
  return 'unknown';
}

function randomDelay(min = 1500, max = 3000) {
  return new Promise(resolve => setTimeout(resolve, Math.floor(Math.random() * (max - min) + min)));
}

async function scrapePrice(page, site) {
  return await page.evaluate((site) => {
    // ── 오늘의집: 쿠폰 적용가 우선, 없으면 판매가
    if (site === 'ohou') {
      // 1순위: 쿠폰 적용가 전용 선택자
      const couponSelectors = [
        '[class*="CouponPrice"]', '[class*="coupon-price"]',
        '[class*="coupon_price"]', '[class*="CouponApply"]',
        '[class*="couponApply"]', '[class*="AfterCoupon"]',
        '[class*="after-coupon"]', '[class*="DiscountPrice"]',
        '[class*="discountPrice"]',
      ];
      for (const sel of couponSelectors) {
        const el = document.querySelector(sel);
        if (el) {
          const m = el.textContent.match(/([\d,]{4,})/);
          if (m) {
            const n = parseInt(m[1].replace(/,/g, ''));
            if (n >= 1000) return n.toLocaleString('ko-KR') + '원';
          }
        }
      }

      // 2순위: JSON-LD
      for (const script of document.querySelectorAll('script[type="application/ld+json"]')) {
        try {
          const d = JSON.parse(script.textContent);
          const p = d?.offers?.price || d?.price;
          if (p) {
            const n = parseFloat(String(p).replace(/,/g, ''));
            if (n >= 1000) return n.toLocaleString('ko-KR') + '원';
          }
        } catch(e) {}
      }

      // 3순위: 판매가 선택자
      const priceSelectors = [
        '[class*="SellingPrice"]', '[class*="sellingPrice"]',
        '[class*="SalePrice"]', '[class*="salePrice"]',
        '[class*="FinalPrice"]', '[class*="finalPrice"]',
        '[class*="GoodsPrice"][class*="selling"]',
        '[class*="GoodsDetailPrice"]',
        '[class*="PriceValue"]', '[class*="price-value"]',
        'meta[property="product:price:amount"]',
      ];
      for (const sel of priceSelectors) {
        const el = document.querySelector(sel);
        if (el) {
          const raw = el.tagName === 'META' ? el.getAttribute('content') : el.textContent;
          const m = raw && raw.match(/([\d,]{4,})/);
          if (m) {
            const n = parseInt(m[1].replace(/,/g, ''));
            if (n >= 1000) return n.toLocaleString('ko-KR') + '원';
          }
        }
      }
    }

    // ── 쿠팡
    if (site === 'coupang') {
      const sel = [
        '.prod-price-cost', '.total-price strong',
        '[class*="price-cost"]', '.price'
      ];
      for (const s of sel) {
        const el = document.querySelector(s);
        if (el) {
          const m = el.textContent.match(/([\d,]{4,})/);
          if (m) {
            const n = parseInt(m[1].replace(/,/g, ''));
            if (n >= 1000) return n.toLocaleString('ko-KR') + '원';
          }
        }
      }
    }

    // 최후 수단: 페이지 텍스트에서 가장 큰 금액
    const matches = [...document.body.innerText.matchAll(/([\d,]{4,})\s*원/g)]
      .map(m => ({ raw: m[1], n: parseInt(m[1].replace(/,/g, '')) }))
      .filter(p => p.n >= 5000 && p.n <= 9999999);
    if (matches.length) {
      matches.sort((a, b) => b.n - a.n);
      return matches[0].n.toLocaleString('ko-KR') + '원';
    }

    return '';
  }, site);
}

(async () => {
  const products = JSON.parse(fs.readFileSync(PRODUCTS_JSON, 'utf-8'));

  const browser = await chromium.launch({
    headless: true,
    args: [
      '--disable-blink-features=AutomationControlled',
      '--no-sandbox', '--disable-setuid-sandbox',
      '--disable-dev-shm-usage', '--lang=ko-KR'
    ]
  });

  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    locale: 'ko-KR',
    viewport: { width: 1366, height: 768 },
    extraHTTPHeaders: {
      'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8',
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }
  });

  for (let i = 0; i < products.length; i++) {
    const p = products[i];
    const url = p.purchase_url;
    if (!url || url === 'https://example.com') {
      console.log(`[${i + 1}/${products.length}] SKIP (no URL): ${p.title}`);
      continue;
    }

    const page = await context.newPage();
    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await randomDelay(1500, 2500);

      const finalUrl = page.url();
      const site = detectSite(finalUrl);
      if (site === 'unknown') {
        console.log(`[${i + 1}/${products.length}] SKIP (unknown site: ${finalUrl}): ${p.title}`);
        await page.close();
        continue;
      }

      // ohou.se: 약간 더 대기해 가격 DOM 렌더링
      if (site === 'ohou') await randomDelay(800, 1200);

      const price = await scrapePrice(page, site);
      products[i].price = price;
      console.log(`[${i + 1}/${products.length}] ${price || '(가격 없음)'} — ${p.title}`);
    } catch (err) {
      console.error(`[${i + 1}/${products.length}] ERROR: ${err.message} — ${p.title}`);
      products[i].price = '';
    } finally {
      await page.close();
    }

    // 서버 부하 방지
    if (i < products.length - 1) await randomDelay(1000, 2000);
  }

  await browser.close();

  fs.writeFileSync(PRODUCTS_JSON, JSON.stringify(products, null, 2), 'utf-8');
  console.log(`\n완료: products.json 업데이트됨 (${products.length}개 제품)`);
})();
