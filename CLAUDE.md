# 카드뉴스 생성 프로젝트

## 개요
가구 제품 URL(오늘의집/쿠팡)을 받아 OpenAI o3로 USP를 추출하고,
Pillow로 6장의 카드뉴스 PNG를 생성하는 파이프라인.

## 핵심 파일
- `pipeline.py` — 메인 진입점 (`python pipeline.py [URL]`)
- `scraper.js` — Node.js Playwright 스크래퍼 (ohou.se / coupang.com)
- `extractor.py` — OpenAI o3 API 호출, 6장 카드 콘텐츠 JSON 반환
- `card_renderer.py` — Pillow 1080×1080 카드 PNG 렌더러

## API 키 설정
`.env` 파일에 `OPENAI_API_KEY` 필요. `.env.example` 참고.
절대 커밋 금지.

## 실행
```bash
python pipeline.py https://www.coupang.com/vp/products/XXXXX
python pipeline.py https://www.ohou.se/products/XXXXX
```

## 출력
`output/` 폴더에 `{slug}_card_1.png` ~ `{slug}_card_6.png` 생성

## 스킬 호출
Claude Code에서 `/cardnews [URL]` 입력
