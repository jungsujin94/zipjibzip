"""
make_pdf.py — 카드뉴스 자동화 에이전트 제작 가이드 PDF 생성
"""
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Preformatted,
    Table, TableStyle, PageBreak, HRFlowable, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

# ── 폰트 등록 ──────────────────────────────────────────────────────────────
pdfmetrics.registerFont(TTFont('Malgun',   'C:/Windows/Fonts/malgun.ttf'))
pdfmetrics.registerFont(TTFont('MalgunBd', 'C:/Windows/Fonts/malgunbd.ttf'))
pdfmetrics.registerFontFamily('Malgun', normal='Malgun', bold='MalgunBd')

# ── 컬러 팔레트 ────────────────────────────────────────────────────────────
C_BG        = colors.HexColor('#F7F6F3')
C_DARK      = colors.HexColor('#1A1A1A')
C_BLUE      = colors.HexColor('#3A86FF')
C_PURPLE    = colors.HexColor('#8B5CF6')
C_GREEN     = colors.HexColor('#10B981')
C_ORANGE    = colors.HexColor('#F59E0B')
C_RED       = colors.HexColor('#EF4444')
C_TEAL      = colors.HexColor('#06B6D4')
C_CODE_BG   = colors.HexColor('#1E1E2E')
C_CODE_TXT  = colors.HexColor('#CDD6F4')
C_MUTED     = colors.HexColor('#6B7280')
C_BADGE_BG  = colors.HexColor('#EFF6FF')
C_BADGE_BDR = colors.HexColor('#BFDBFE')
C_WARN_BG   = colors.HexColor('#FFFBEB')
C_WARN_BDR  = colors.HexColor('#FCD34D')

W, H = A4  # 595.27 x 841.89 pt

# ── 스타일 ─────────────────────────────────────────────────────────────────
def make_styles():
    s = {}

    s['body'] = ParagraphStyle('body',
        fontName='Malgun', fontSize=10, leading=16,
        textColor=C_DARK, spaceAfter=6, alignment=TA_JUSTIFY)

    s['body_sm'] = ParagraphStyle('body_sm',
        fontName='Malgun', fontSize=9, leading=14,
        textColor=C_DARK, spaceAfter=4)

    s['h1'] = ParagraphStyle('h1',
        fontName='MalgunBd', fontSize=18, leading=24,
        textColor=C_DARK, spaceBefore=18, spaceAfter=8)

    s['h2'] = ParagraphStyle('h2',
        fontName='MalgunBd', fontSize=13, leading=18,
        textColor=C_DARK, spaceBefore=14, spaceAfter=6)

    s['h3'] = ParagraphStyle('h3',
        fontName='MalgunBd', fontSize=11, leading=15,
        textColor=C_BLUE, spaceBefore=10, spaceAfter=4)

    s['cover_title'] = ParagraphStyle('cover_title',
        fontName='MalgunBd', fontSize=28, leading=36,
        textColor=colors.white, alignment=TA_CENTER)

    s['cover_sub'] = ParagraphStyle('cover_sub',
        fontName='Malgun', fontSize=13, leading=20,
        textColor=colors.HexColor('#CCDDFF'), alignment=TA_CENTER)

    s['label'] = ParagraphStyle('label',
        fontName='MalgunBd', fontSize=9, leading=12,
        textColor=C_BLUE, spaceAfter=2)

    s['code_inline'] = ParagraphStyle('code_inline',
        fontName='Courier', fontSize=8.5, leading=13,
        textColor=C_CODE_TXT, backColor=C_CODE_BG,
        leftIndent=8, rightIndent=8, spaceBefore=4, spaceAfter=4)

    s['bullet'] = ParagraphStyle('bullet',
        fontName='Malgun', fontSize=10, leading=15,
        textColor=C_DARK, leftIndent=16, firstLineIndent=-12, spaceAfter=3)

    s['note'] = ParagraphStyle('note',
        fontName='Malgun', fontSize=9, leading=14,
        textColor=colors.HexColor('#92400E'), backColor=C_WARN_BG,
        borderColor=C_WARN_BDR, borderWidth=1, borderPadding=8,
        spaceBefore=6, spaceAfter=6)

    s['caption'] = ParagraphStyle('caption',
        fontName='Malgun', fontSize=8.5, leading=13,
        textColor=C_MUTED, alignment=TA_CENTER, spaceAfter=4)

    return s

S = make_styles()

# ── 헬퍼 빌더 ──────────────────────────────────────────────────────────────

def hr(color=C_MUTED, thickness=0.5):
    return HRFlowable(width='100%', thickness=thickness, color=color,
                      spaceAfter=6, spaceBefore=6)

def space(h=6):
    return Spacer(1, h)

def h1(text): return Paragraph(text, S['h1'])
def h2(text): return Paragraph(text, S['h2'])
def h3(text): return Paragraph(text, S['h3'])
def body(text): return Paragraph(text, S['body'])
def body_sm(text): return Paragraph(text, S['body_sm'])
def note(text): return Paragraph(f'⚠️  {text}', S['note'])

def bullet(text, bold_prefix=''):
    if bold_prefix:
        t = f'<font name="MalgunBd">• {bold_prefix}</font>{text}'
    else:
        t = f'• {text}'
    return Paragraph(t, S['bullet'])

def code_block(text, label=None):
    """Split code into chunks of max 30 lines to avoid page-overflow."""
    items = []
    if label:
        items.append(Paragraph(label, S['label']))

    pre_style = ParagraphStyle('pre',
        fontName='Courier', fontSize=8, leading=12,
        textColor=C_CODE_TXT, backColor=C_CODE_BG,
        leftIndent=10, rightIndent=10,
        spaceBefore=0, spaceAfter=0,
        borderPadding=(6, 10, 6, 10))

    lines = text.split('\n')
    chunk_size = 28
    chunks = [lines[i:i+chunk_size] for i in range(0, len(lines), chunk_size)]
    for chunk in chunks:
        items.append(Preformatted('\n'.join(chunk), pre_style))
    items.append(space(4))
    return items

def section_badge(text, color=C_BLUE):
    tbl = Table([[Paragraph(f'<font color="white"><b> {text} </b></font>',
                            ParagraphStyle('badge', fontName='MalgunBd',
                                           fontSize=10, textColor=colors.white))]],
                colWidths=[W - 80*mm])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), color),
        ('LEFTPADDING',  (0,0), (-1,-1), 12),
        ('TOPPADDING',   (0,0), (-1,-1), 7),
        ('BOTTOMPADDING',(0,0), (-1,-1), 7),
        ('ROUNDEDCORNERS', [4]),
    ]))
    return tbl

def card_spec_table(rows):
    """카드 스펙 2-column 테이블"""
    data = [[
        Paragraph('<b>필드</b>', ParagraphStyle('th', fontName='MalgunBd', fontSize=9, textColor=colors.white)),
        Paragraph('<b>설명</b>', ParagraphStyle('th', fontName='MalgunBd', fontSize=9, textColor=colors.white)),
    ]]
    for field, desc in rows:
        data.append([
            Paragraph(f'<font name="Courier" size="8">{field}</font>',
                      ParagraphStyle('td_f', fontName='Courier', fontSize=8.5, textColor=C_BLUE)),
            Paragraph(desc, S['body_sm']),
        ])
    col_w = W - 80*mm
    tbl = Table(data, colWidths=[col_w*0.28, col_w*0.72])
    tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0),  C_DARK),
        ('BACKGROUND',    (0,1), (-1,-1), colors.white),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [colors.white, C_BADGE_BG]),
        ('GRID',          (0,0), (-1,-1), 0.4, colors.HexColor('#E5E7EB')),
        ('LEFTPADDING',   (0,0), (-1,-1), 8),
        ('RIGHTPADDING',  (0,0), (-1,-1), 8),
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('VALIGN',        (0,0), (-1,-1), 'TOP'),
    ]))
    return tbl

# ── 커버 페이지 ────────────────────────────────────────────────────────────

def cover_page():
    items = []
    items.append(space(60))

    # 타이틀 블록
    title_data = [[
        Paragraph('카드뉴스 자동화<br/>에이전트 제작 가이드', S['cover_title']),
    ]]
    tbl = Table(title_data, colWidths=[W - 80*mm])
    tbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), C_DARK),
        ('LEFTPADDING',   (0,0), (-1,-1), 24),
        ('RIGHTPADDING',  (0,0), (-1,-1), 24),
        ('TOPPADDING',    (0,0), (-1,-1), 32),
        ('BOTTOMPADDING', (0,0), (-1,-1), 32),
        ('ROUNDEDCORNERS', [8]),
    ]))
    items.append(tbl)
    items.append(space(16))

    items.append(Paragraph(
        'Claude AI + Python으로 만드는<br/>인스타그램 카드뉴스 자동화 파이프라인',
        ParagraphStyle('cs', fontName='Malgun', fontSize=13, leading=20,
                       textColor=C_MUTED, alignment=TA_CENTER)))

    items.append(space(48))
    items.append(hr())
    items.append(space(8))

    badges = [
        ('Python 3.10+', C_BLUE),
        ('Node.js 18+', C_GREEN),
        ('Claude API', C_PURPLE),
        ('Playwright', C_TEAL),
        ('Pillow', C_ORANGE),
    ]
    badge_data = [[
        Paragraph(f'<font color="white"><b> {t} </b></font>',
                  ParagraphStyle('b', fontName='MalgunBd', fontSize=9, textColor=colors.white))
        for t, _ in badges
    ]]
    badge_colors = [c for _, c in badges]
    btbl = Table(badge_data, colWidths=[(W-80*mm)/len(badges)]*len(badges))
    style_cmds = [
        ('LEFTPADDING',   (0,0), (-1,-1), 6),
        ('RIGHTPADDING',  (0,0), (-1,-1), 6),
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('ALIGN',         (0,0), (-1,-1), 'CENTER'),
        ('ROUNDEDCORNERS', [4]),
    ]
    for i, c in enumerate(badge_colors):
        style_cmds.append(('BACKGROUND', (i,0), (i,0), c))
    btbl.setStyle(TableStyle(style_cmds))
    items.append(btbl)

    items.append(space(24))
    items.append(Paragraph(
        '⚠️  이 가이드는 핵심 아이디어와 구조를 공유합니다.<br/>'
        '이미지 배경 제거 및 스케치 렌더링 기능은 포함되지 않습니다.',
        ParagraphStyle('warn', fontName='Malgun', fontSize=9, leading=14,
                       textColor=colors.HexColor('#92400E'),
                       backColor=C_WARN_BG, borderColor=C_WARN_BDR,
                       borderWidth=1, borderPadding=10, alignment=TA_CENTER)))
    items.append(PageBreak())
    return items

# ── 목차 ───────────────────────────────────────────────────────────────────

def toc():
    items = []
    items.append(h1('목차'))
    items.append(hr(C_DARK))
    items.append(space(4))

    sections = [
        ('1', '시스템 개요',          '이 에이전트가 하는 일'),
        ('2', '준비물 & 환경 설정',    'Python, Node.js, API 키, 패키지'),
        ('3', '프로젝트 구조',         '폴더 & 파일 레이아웃'),
        ('4', '카드 구조 스펙',        '6장 카드 각각의 필드 정의'),
        ('5', '스크래퍼 (scraper.js)', 'Playwright로 제품 페이지 크롤링'),
        ('6', '콘텐츠 추출기 (extractor.py)', 'Claude API로 카드 내용 생성'),
        ('7', '카드 렌더러 (card_renderer.py)', 'Pillow 1080×1080 PNG 생성'),
        ('8', '파이프라인 (pipeline.py)', '전체 흐름 오케스트레이션'),
        ('9', 'Claude Code 스킬 설정', 'SKILL.md & yes/no/hold 플로우'),
        ('10','실행 & 테스트',         '처음부터 끝까지 한 번에'),
    ]

    for num, title, sub in sections:
        row_data = [[
            Paragraph(f'<font name="MalgunBd" color="#3A86FF">{num}</font>',
                      ParagraphStyle('n', fontName='MalgunBd', fontSize=12,
                                     textColor=C_BLUE, alignment=TA_CENTER)),
            Paragraph(f'<b>{title}</b><br/><font color="#6B7280" size="9">{sub}</font>',
                      ParagraphStyle('td', fontName='Malgun', fontSize=11,
                                     leading=15, textColor=C_DARK)),
        ]]
        rtbl = Table(row_data, colWidths=[24, W-80*mm-30])
        rtbl.setStyle(TableStyle([
            ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING',   (0,0), (-1,-1), 4),
            ('TOPPADDING',    (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LINEBELOW',     (0,0), (-1,-1), 0.4, colors.HexColor('#E5E7EB')),
        ]))
        items.append(rtbl)

    items.append(PageBreak())
    return items

# ── 섹션 1: 개요 ───────────────────────────────────────────────────────────

def section_overview():
    items = []
    items.append(section_badge('01  시스템 개요', C_DARK))
    items.append(space(8))
    items.append(body(
        '이 에이전트는 오늘의집 또는 쿠팡 제품 URL 하나를 입력받아 '
        '인스타그램용 마케팅 카드뉴스 <b>6장 PNG</b>를 자동 생성합니다. '
        'Claude Code CLI에서 단 한 줄의 명령으로 스크래핑 → AI 분석 → 이미지 렌더링까지 '
        '전 과정이 자동으로 처리됩니다.'
    ))
    items.append(space(8))

    # 흐름도 텍스트
    flow = (
        '  URL 입력\n'
        '     ↓\n'
        '  scraper.js  →  제품명 / 가격 / 이미지 / 리뷰 수집\n'
        '     ↓\n'
        '  extractor.py  →  Claude API → 카드 6장 JSON 생성\n'
        '     ↓\n'
        '  card_renderer.py  →  Pillow 1080×1080 PNG × 6\n'
        '     ↓\n'
        '  pipeline.py  →  yes / no / hold\n'
        '     ↓\n'
        '  products.json + index.html 자동 업데이트'
    )
    items += code_block(flow, '전체 흐름')
    items.append(PageBreak())
    return items

# ── 섹션 2: 준비물 ─────────────────────────────────────────────────────────

def section_prerequisites():
    items = []
    items.append(section_badge('02  준비물 & 환경 설정', C_BLUE))
    items.append(space(8))

    items.append(h3('필수 설치'))
    for item in [
        ('Python 3.10+', 'https://python.org'),
        ('Node.js 18+',  'https://nodejs.org'),
        ('Claude Code CLI', 'npm install -g @anthropic-ai/claude-code'),
    ]:
        items.append(bullet(f'  →  <font name="Courier">{item[1]}</font>', item[0]))

    items.append(space(6))
    items.append(h3('Python 패키지'))
    items += code_block(
        'pip install anthropic pillow python-dotenv requests',
        'terminal'
    )

    items.append(h3('Node.js 패키지'))
    items += code_block(
        'npm install playwright\nnpx playwright install chromium',
        'terminal'
    )

    items.append(h3('API 키 설정'))
    items.append(body(
        '프로젝트 루트에 <font name="Courier">.env</font> 파일을 만들고 Anthropic API 키를 입력하세요. '
        '이 파일은 절대 git에 올리지 마세요.'
    ))
    items += code_block(
        '# .env\nANTHROPIC_API_KEY=sk-ant-...',
        '.env 파일 (절대 공개 금지)'
    )
    items.append(note(
        '.env 파일과 API 키는 절대 GitHub에 올리지 마세요. '
        '.gitignore에 반드시 추가하세요.'
    ))
    items.append(PageBreak())
    return items

# ── 섹션 3: 프로젝트 구조 ──────────────────────────────────────────────────

def section_structure():
    items = []
    items.append(section_badge('03  프로젝트 구조', C_PURPLE))
    items.append(space(8))

    tree = (
        'my-cardnews/\n'
        '├── pipeline.py          # 메인 진입점\n'
        '├── scraper.js           # Playwright 스크래퍼\n'
        '├── extractor.py         # Claude API 콘텐츠 생성\n'
        '├── card_renderer.py     # Pillow PNG 렌더러\n'
        '├── page.py              # HTML 카탈로그 생성\n'
        '├── products.json        # 업로드 승인 제품 DB\n'
        '├── .env                 # API 키 (git 제외)\n'
        '├── products/            # 카드 1번 이미지 저장\n'
        '├── output/              # 생성된 카드 PNG 임시 저장\n'
        '├── images/              # 로고 등 정적 이미지\n'
        '└── index.html           # 웹 카탈로그 (자동 생성)'
    )
    items += code_block(tree, '폴더 구조')
    items.append(PageBreak())
    return items

# ── 섹션 4: 카드 구조 스펙 ────────────────────────────────────────────────

def section_card_spec():
    items = []
    items.append(section_badge('04  카드 구조 스펙 (6장)', C_GREEN))
    items.append(space(6))
    items.append(body(
        'Claude API는 아래 구조의 JSON을 반환해야 합니다. '
        '카드 6장 + 인스타그램 캡션으로 구성됩니다.'
    ))
    items.append(space(6))

    cards = [
        ('카드 1 — HOOK', C_RED,
         '스크롤을 멈추게 하는 첫 장. "이거 내 얘기잖아?" 느낌의 공감 후킹 문구.',
         [
             ('tag',      '"HOOK" (고정값)'),
             ('headline', '30자 이내 후킹 문구. 페인포인트 직격 / 상황 묘사 / 질문형 / 수치 팩트 중 택1'),
             ('subtext',  '공감 서브카피 1줄 (25자 이내)'),
         ]),
        ('카드 2 — COMBO', C_ORANGE,
         '소비자 고민 3가지 + 구매 체크포인트 3가지를 한 장에. 저장 유도 목적.',
         [
             ('tag',          '"COMBO" (고정값)'),
             ('pain_headline','페인포인트 섹션 제목 (예: "이런 고민 있으신가요?")'),
             ('pain_points',  '페인포인트 배열 3개 (각 20자 이내)'),
             ('list_headline','체크리스트 섹션 제목 (예: "선택할 때 이것만 체크")'),
             ('items',        '체크리스트 배열 3개. 각 항목: { num, title(10자), desc(18자) }'),
         ]),
        ('카드 3 — REVIEW', C_TEAL,
         '실제 구매자 후기 요약. 신뢰 구축 및 "나도 사야겠다" 유도.',
         [
             ('tag',      '"REVIEW" (고정값)'),
             ('headline', '"실제 구매자 후기" 등 섹션 제목'),
             ('reviews',  '후기 배열. 각 항목: { rating: 1-5, text: "40자 이내 구매자 말투" }'),
             ('overall',  '전반적 만족도 한 줄 요약 (예: "재구매 의사 90% 이상")'),
         ]),
        ('카드 4 — STAT', C_PURPLE,
         '"이거 알아?" 놀라운 통계/수치로 공유 유도.',
         [
             ('tag',         '"STAT" (고정값)'),
             ('intro',       '"이거 알고 계셨나요?" 등 도입 문구'),
             ('stat_number', '핵심 수치 (예: "하루 10시간", "3배", "40분")'),
             ('stat_desc',   '수치 설명 35자 이내. 출처 느낌 포함 시 신뢰도 상승'),
             ('context',     '독자 상황과 연결하는 질문 (25자 이내)'),
         ]),
        ('카드 5 — SOLUTION', C_GREEN,
         '제품 소개 + 실제 가격. 스크래핑된 가격을 그대로 사용.',
         [
             ('tag',          '"SOLUTION" (고정값)'),
             ('product_name', '제품 풀네임'),
             ('brand',        '브랜드명'),
             ('price',        '스크래핑된 실제 가격 그대로 (예: "285,000원"). 절대 만들지 말 것'),
             ('discount',     '할인율 (예: "10%"). 없으면 빈 문자열'),
             ('highlight',    '핵심 USP 한 줄 (20자 이내. 배송/쿠폰 제외)'),
             ('url',          '제품 구매 URL 도메인'),
         ]),
        ('카드 6 — CTA', C_BLUE,
         '팔로우 및 구매 유도 마지막 장.',
         [
             ('tag',         '"CTA" (고정값)'),
             ('headline',    '팔로우하면 얻는 것 (25자 이내)'),
             ('subtext',     '"다음에도 보고 싶게 만드는" 서브 문구'),
             ('cta_button',  '"link in caption" 등 CTA 라벨'),
             ('url_display', '표시할 사이트 도메인'),
         ]),
    ]

    for card_title, color, desc, fields in cards:
        items.append(KeepTogether([
            space(6),
            section_badge(card_title, color),
            space(4),
            body(desc),
            card_spec_table(fields),
        ]))
        items.append(space(4))

    # Caption
    items.append(KeepTogether([
        space(6),
        section_badge('캡션 (caption)', C_DARK),
        space(4),
        body('카드 게시 시 사용할 인스타그램 캡션. 후킹 라인 + 본문 + 해시태그로 구성.'),
        card_spec_table([
            ('hook_line',  '스크롤 멈추는 첫 줄 후킹 문구 + 이모지'),
            ('body_lines', '본문 라인 배열 (2~3줄 권장)'),
            ('hashtags',   '해시태그 배열 정확히 5개 (인스타그램 정책)'),
        ]),
    ]))

    items.append(space(8))
    items.append(body('JSON 전체 반환 예시 스켈레톤:'))
    items += code_block(
        '{\n'
        '  "product_slug": "product-name-in-english",\n'
        '  "card1": { "tag": "HOOK", "headline": "...", "subtext": "..." },\n'
        '  "card2": { "tag": "COMBO", "pain_headline": "...",\n'
        '             "pain_points": ["...", "...", "..."],\n'
        '             "list_headline": "...",\n'
        '             "items": [{"num":"01","title":"...","desc":"..."},...] },\n'
        '  "card3": { "tag": "REVIEW", "headline": "...",\n'
        '             "reviews": [{"rating":5,"text":"..."},...],\n'
        '             "overall": "..." },\n'
        '  "card4": { "tag": "STAT", "intro": "...", "stat_number": "...",\n'
        '             "stat_desc": "...", "context": "..." },\n'
        '  "card5": { "tag": "SOLUTION", "product_name": "...", "brand": "...",\n'
        '             "price": "...", "discount": "", "highlight": "...",\n'
        '             "url": "..." },\n'
        '  "card6": { "tag": "CTA", "headline": "...", "subtext": "...",\n'
        '             "cta_button": "link in caption", "url_display": "..." },\n'
        '  "caption": { "hook_line": "...",\n'
        '               "body_lines": ["...", "...", "..."],\n'
        '               "hashtags": ["#태그1","#태그2","#태그3","#태그4","#태그5"] }\n'
        '}',
        'JSON 스켈레톤'
    )
    items.append(PageBreak())
    return items

# ── 섹션 5: scraper.js ─────────────────────────────────────────────────────

def section_scraper():
    items = []
    items.append(section_badge('05  스크래퍼 (scraper.js)', C_TEAL))
    items.append(space(8))
    items.append(body(
        'Playwright headless Chromium으로 오늘의집 / 쿠팡 제품 페이지에 접속해 '
        '필요한 데이터를 수집합니다. 결과는 JSON으로 stdout에 출력합니다.'
    ))
    items.append(space(6))
    items.append(h3('수집 대상 필드'))
    for f in [
        ('name', '제품명 (문자열)'),
        ('price', '가격 문자열 그대로 (예: "285,000원")'),
        ('discount', '할인율 문자열 (없으면 빈 문자열)'),
        ('brand', '브랜드명'),
        ('rating', '평점 (예: "4.8")'),
        ('imageUrls', '제품 이미지 URL 배열 (최대 8개 권장)'),
        ('reviews', '리뷰 배열. 각 항목: { rating, text }'),
        ('site', '"ohou" 또는 "coupang"'),
    ]:
        items.append(bullet(f'<font name="Courier">{f[0]}</font>  —  {f[1]}'))

    items.append(space(6))
    items += code_block(
        "// scraper.js\nconst { chromium } = require('playwright');\n\n"
        "async function scrape(url) {\n"
        "  const browser = await chromium.launch({ headless: true });\n"
        "  const page = await browser.newPage();\n\n"
        "  // 봇 탐지 우회를 위한 User-Agent 설정\n"
        "  await page.setExtraHTTPHeaders({\n"
        "    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '\n"
        "                  + 'AppleWebKit/537.36'\n"
        "  });\n\n"
        "  await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });\n\n"
        "  // ── 여기서 사이트별 셀렉터로 데이터 추출 ──\n"
        "  const name  = await page.$eval('.product-title', el => el.innerText)\n"
        "                      .catch(() => '');\n"
        "  const price = await page.$eval('.price', el => el.innerText)\n"
        "                      .catch(() => '');\n"
        "  const imageUrls = await page.$$eval('img.product-img',\n"
        "    imgs => imgs.map(i => i.src));\n\n"
        "  const reviews = [];  // 사이트별 리뷰 셀렉터 적용\n\n"
        "  await browser.close();\n\n"
        "  return { name, price, imageUrls, reviews, site: 'ohou' };\n"
        "}\n\n"
        "const url = process.argv[2];\n"
        "scrape(url)\n"
        "  .then(data => { process.stdout.write(JSON.stringify(data)); })\n"
        "  .catch(err => {\n"
        "    process.stderr.write(JSON.stringify({ error: err.message }));\n"
        "    process.exit(1);\n"
        "  });",
        'scraper.js 템플릿'
    )
    items.append(note(
        '오늘의집과 쿠팡은 HTML 구조가 다르므로 URL에 따라 셀렉터를 분기해서 처리해야 합니다. '
        '실제 셀렉터는 사이트 업데이트에 따라 변경될 수 있으니 주기적으로 점검하세요.'
    ))
    items.append(PageBreak())
    return items

# ── 섹션 6: extractor.py ───────────────────────────────────────────────────

def section_extractor():
    items = []
    items.append(section_badge('06  콘텐츠 추출기 (extractor.py)', C_PURPLE))
    items.append(space(8))
    items.append(body(
        'Claude API에 스크래핑 데이터를 전달하고 카드 6장 JSON을 반환받습니다. '
        'SNS 마케팅 전문가 역할의 시스템 프롬프트를 작성하는 것이 핵심입니다.'
    ))
    items.append(space(6))

    items.append(h3('시스템 프롬프트 설계 원칙'))
    for item in [
        '역할 부여: "한국 SNS 마케팅 전문가, 인스타그램 카드뉴스 전문"',
        '출력 형식 강제: "반드시 유효한 JSON만 반환하세요" 명시',
        '각 카드 목적 설명: HOOK(저장 유도) → COMBO(공감) → REVIEW(신뢰) → STAT(공유) → SOLUTION(구매) → CTA(팔로우)',
        '금지 사항 명시: 가격 언급, 막연한 표현, 중복 패턴 등',
        '리뷰는 스크래핑된 원문 기반으로 요약하도록 지시',
    ]:
        items.append(bullet(item))

    items.append(space(6))
    items += code_block(
        "# extractor.py\nimport json, re, anthropic\n\n"
        "SYSTEM_PROMPT = \"\"\"\n"
        "당신은 한국 SNS 마케팅 전문가입니다.\n"
        "인스타그램 카드뉴스를 제작하여 저장수·공유수·팔로워를 늘리는 것이 전문입니다.\n"
        "반드시 유효한 JSON만 반환하세요.\n"
        "\"\"\"\n\n"
        "USER_PROMPT_TEMPLATE = \"\"\"\n"
        "아래 제품 정보를 분석해 인스타그램 카드뉴스 6장 콘텐츠를 JSON으로 반환하라.\n\n"
        "제품 정보:\n{data}\n\n"
        "반환 형식 (섹션 4의 JSON 스켈레톤 그대로):\n"
        "{ \"product_slug\": ..., \"card1\": {...}, ..., \"caption\": {...} }\n"
        "\"\"\"\n\n"
        "def extract_card_content(scraped_data: dict, api_key: str) -> dict:\n"
        "    client = anthropic.Anthropic(api_key=api_key)\n\n"
        "    prompt = USER_PROMPT_TEMPLATE.format(\n"
        "        data=json.dumps(scraped_data, ensure_ascii=False, indent=2)\n"
        "    )\n\n"
        "    response = client.messages.create(\n"
        "        model='claude-sonnet-4-6',\n"
        "        max_tokens=2000,\n"
        "        system=SYSTEM_PROMPT,\n"
        "        messages=[{'role': 'user', 'content': prompt}]\n"
        "    )\n\n"
        "    raw = response.content[0].text.strip()\n"
        "    # 마크다운 코드블록 제거\n"
        "    if '```' in raw:\n"
        "        raw = re.sub(r'```(?:json)?\\s*', '', raw).replace('```', '')\n\n"
        "    return json.loads(raw.strip())",
        'extractor.py 템플릿'
    )
    items.append(PageBreak())
    return items

# ── 섹션 7: card_renderer.py ───────────────────────────────────────────────

def section_renderer():
    items = []
    items.append(section_badge('07  카드 렌더러 (card_renderer.py)', C_ORANGE))
    items.append(space(8))
    items.append(body(
        'Python Pillow로 1080×1080px PNG 카드 6장을 생성합니다. '
        '각 카드는 배경색 + 텍스트 + 제품 이미지로 구성됩니다. '
        '아래는 기본 구조이며, 디자인은 자유롭게 커스터마이징하세요.'
    ))

    items.append(space(4))
    items.append(h3('카드 레이아웃 기본 원칙'))
    for item in [
        '캔버스: 1080 × 1080px, RGB 또는 RGBA',
        '여백(padding): 상하좌우 최소 60px 권장',
        '폰트: Pillow ImageFont.truetype() — 한국어 지원 TTF 필요 (예: Malgun Gothic)',
        '텍스트 줄바꿈: textwrap 또는 직접 문자열 분할 처리',
        '이미지 삽입: img.paste() 또는 img.thumbnail() 후 합성',
        '저장: card.save(path, "PNG")',
    ]:
        items.append(bullet(item))

    items.append(space(6))
    items += code_block(
        "# card_renderer.py\nfrom PIL import Image, ImageDraw, ImageFont\nimport os\n\n"
        "SIZE = (1080, 1080)\nPAD  = 72  # 여백\n\n"
        "def load_font(path: str, size: int):\n"
        "    return ImageFont.truetype(path, size)\n\n"
        "def make_card_base(bg_color='#F7F6F3') -> tuple[Image.Image, ImageDraw.Draw]:\n"
        "    img  = Image.new('RGB', SIZE, bg_color)\n"
        "    draw = ImageDraw.Draw(img)\n"
        "    return img, draw\n\n"
        "def draw_text_wrapped(draw, text, font, x, y, max_width, fill='#1A1A1A'):\n"
        "    \"\"\"max_width 안에서 자동 줄바꿈\"\"\"\n"
        "    words = text.split()\n"
        "    line, lines = '', []\n"
        "    for word in words:\n"
        "        test = f'{line} {word}'.strip()\n"
        "        w = draw.textlength(test, font=font)\n"
        "        if w <= max_width:\n"
        "            line = test\n"
        "        else:\n"
        "            if line: lines.append(line)\n"
        "            line = word\n"
        "    if line: lines.append(line)\n"
        "    _, _, _, lh = draw.textbbox((0,0), 'A', font=font)\n"
        "    for i, l in enumerate(lines):\n"
        "        draw.text((x, y + i*(lh+8)), l, font=font, fill=fill)\n"
        "    return y + len(lines)*(lh+8)\n\n"
        "def render_card1(content: dict, img_path: str, out_path: str,\n"
        "                 font_path: str):\n"
        "    \"\"\"HOOK 카드: 후킹 문구 + 제품 이미지\"\"\"\n"
        "    card, draw = make_card_base('#1A1A1A')\n\n"
        "    # 제품 이미지 (우측 하단)\n"
        "    if img_path and os.path.exists(img_path):\n"
        "        prod = Image.open(img_path).convert('RGBA')\n"
        "        prod.thumbnail((580, 580))\n"
        "        card.paste(prod, (520, 480), prod)\n\n"
        "    # 헤드라인 텍스트\n"
        "    font_lg = load_font(font_path, 60)\n"
        "    font_sm = load_font(font_path, 32)\n"
        "    draw_text_wrapped(draw, content['headline'], font_lg,\n"
        "                      PAD, 120, 900, fill='#FFFFFF')\n"
        "    draw.text((PAD, 820), content['subtext'], font=font_sm,\n"
        "              fill='#AAAAAA')\n\n"
        "    card.save(out_path, 'PNG')\n\n"
        "# card2~6도 동일한 패턴으로 작성\n"
        "# render_card2, render_card3 ... render_card6\n\n"
        "def render_all_cards(content: dict, output_dir: str,\n"
        "                     img_paths: list, font_path: str) -> list:\n"
        "    slug = content.get('product_slug', 'product')\n"
        "    os.makedirs(output_dir, exist_ok=True)\n"
        "    paths = []\n"
        "    for i, render_fn in enumerate(\n"
        "        [render_card1, render_card2, render_card3,\n"
        "         render_card4, render_card5, render_card6], start=1\n"
        "    ):\n"
        "        out = os.path.join(output_dir, f'{slug}_card_{i}.png')\n"
        "        img = img_paths[min(i-1, len(img_paths)-1)] if img_paths else None\n"
        "        render_fn(content[f'card{i}'], img, out, font_path)\n"
        "        paths.append(out)\n"
        "    return paths",
        'card_renderer.py 템플릿'
    )
    items.append(PageBreak())
    return items

# ── 섹션 8: pipeline.py ────────────────────────────────────────────────────

def section_pipeline():
    items = []
    items.append(section_badge('08  파이프라인 (pipeline.py)', C_GREEN))
    items.append(space(8))
    items.append(body(
        '모든 단계를 하나로 연결하는 오케스트레이터입니다. '
        'URL을 받아 스크래핑 → 추출 → 렌더링을 순서대로 실행하고 '
        'yes/no/hold 응답을 처리합니다.'
    ))
    items.append(space(6))

    items += code_block(
        "# pipeline.py\nimport sys, os, json, subprocess\nfrom dotenv import load_dotenv\n"
        "from extractor import extract_card_content\nfrom card_renderer import render_all_cards\nimport requests, tempfile\n\n"
        "OUTPUT_DIR = 'output'\nPRODUCTS_JSON = 'products.json'\n\n"
        "def scrape(url: str) -> dict:\n"
        "    result = subprocess.run(\n"
        "        ['node', 'scraper.js', url],\n"
        "        capture_output=True, text=True, encoding='utf-8'\n"
        "    )\n"
        "    if result.returncode != 0:\n"
        "        raise RuntimeError(f'스크래퍼 오류: {result.stderr}')\n"
        "    return json.loads(result.stdout)\n\n"
        "def download_images(urls: list, max_n=5) -> list:\n"
        "    paths = []\n"
        "    for url in urls[:max_n]:\n"
        "        try:\n"
        "            r = requests.get(url, timeout=15)\n"
        "            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')\n"
        "            tmp.write(r.content); tmp.close()\n"
        "            paths.append(tmp.name)\n"
        "        except Exception:\n"
        "            pass\n"
        "    return paths\n\n"
        "def run(url: str):\n"
        "    load_dotenv()\n"
        "    api_key = os.getenv('ANTHROPIC_API_KEY')\n\n"
        "    # 1. 스크래핑\n"
        "    data = scrape(url)\n"
        "    print(f'제품명: {data[\"name\"]}')\n\n"
        "    # 2. 이미지 다운로드\n"
        "    img_paths = download_images(data.get('imageUrls', []))\n\n"
        "    # 3. Claude로 카드 콘텐츠 생성\n"
        "    content = extract_card_content(data, api_key)\n\n"
        "    # 4. PNG 렌더링\n"
        "    font = 'C:/Windows/Fonts/malgun.ttf'  # 폰트 경로 조정\n"
        "    out_paths = render_all_cards(content, OUTPUT_DIR, img_paths, font)\n\n"
        "    # 5. 임시 파일 정리\n"
        "    for p in img_paths:\n"
        "        os.unlink(p)\n\n"
        "    print(f'\\n생성 완료: {len(out_paths)}장')\n"
        "    for p in out_paths: print(f'  {p}')\n"
        "    return content, out_paths\n\n"
        "if __name__ == '__main__':\n"
        "    url = sys.argv[1]\n"
        "    run(url)",
        'pipeline.py 템플릿'
    )
    items.append(PageBreak())
    return items

# ── 섹션 9: Skill 설정 ─────────────────────────────────────────────────────

def section_skill():
    items = []
    items.append(section_badge('09  Claude Code 스킬 설정', C_BLUE))
    items.append(space(8))
    items.append(body(
        'Claude Code에서 <font name="Courier">/cardnews [URL]</font> 명령어로 '
        '파이프라인을 실행하려면 스킬 파일이 필요합니다.'
    ))
    items.append(space(6))

    items.append(h3('스킬 파일 위치'))
    items += code_block(
        '~/.claude/skills/cardnews/SKILL.md',
        '경로'
    )

    items.append(h3('SKILL.md 템플릿'))
    items += code_block(
        "---\n"
        "name: cardnews\n"
        "description: 가구 제품 URL을 받아 카드뉴스 6장 PNG를 자동 생성합니다.\n"
        "argument-hint: \"[오늘의집 또는 쿠팡 제품 URL]\"\n"
        "allowed-tools: Bash(python *), Bash(node *), Bash(cp *), Bash(rm *), Read, Edit\n"
        "---\n\n"
        "# 카드뉴스 생성기\n\n"
        "## Step 1 — 파이프라인 실행\n\n"
        "```bash\n"
        "cd /path/to/my-cardnews && python pipeline.py \"$ARGUMENTS\"\n"
        "```\n\n"
        "## Step 2 — 결과 보고\n\n"
        "실행 후 다음을 포함해 보고:\n"
        "1. 생성된 PNG 6개 파일 경로\n"
        "2. 각 카드 핵심 메시지 요약\n\n"
        "## Step 3 — 업로드 확인\n\n"
        "**업로드할까요?**\n"
        "- `yes` → card_1.png를 products/ 폴더에 저장 + products.json 업데이트\n"
        "- `no`  → output/ 폴더의 이번 생성 파일 전체 삭제\n"
        "- `hold` → 아무 작업 없이 output/ 폴더에 유지\n\n"
        "## Step 4 — yes 처리\n\n"
        "1. slug 확인 (파일명: {slug}_card_1.png)\n"
        "2. card_1.png → products/{slug}_card_1.png 복사\n"
        "3. products.json에 항목 추가/업데이트:\n"
        "   { slug, title, image, purchase_url, category, price }\n\n"
        "## Step 5 — no 처리\n\n"
        "output/{slug}_card_1~6.png 및 caption.txt 전부 삭제\n\n"
        "## Step 6 — hold 처리\n\n"
        "아무 작업 없이 완료 메시지 출력",
        'SKILL.md 템플릿'
    )

    items.append(h3('yes / no / hold 플로우'))
    flow_data = [
        [Paragraph('<b>명령</b>', ParagraphStyle('th', fontName='MalgunBd', fontSize=9, textColor=colors.white)),
         Paragraph('<b>동작</b>', ParagraphStyle('th', fontName='MalgunBd', fontSize=9, textColor=colors.white))],
        [Paragraph('<font name="Courier" color="#10B981">yes</font>', S['body_sm']),
         Paragraph('card_1.png → products/ 복사 | products.json 업데이트 | index.html 재생성', S['body_sm'])],
        [Paragraph('<font name="Courier" color="#EF4444">no</font>', S['body_sm']),
         Paragraph('output/ 폴더의 이번 생성 파일 전체 삭제', S['body_sm'])],
        [Paragraph('<font name="Courier" color="#F59E0B">hold</font>', S['body_sm']),
         Paragraph('output/ 폴더에 그대로 유지. 나중에 yes/no 결정', S['body_sm'])],
    ]
    col_w = W - 80*mm
    ftbl = Table(flow_data, colWidths=[col_w*0.18, col_w*0.82])
    ftbl.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0),  C_DARK),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [colors.white, C_BADGE_BG]),
        ('GRID',          (0,0), (-1,-1), 0.4, colors.HexColor('#E5E7EB')),
        ('LEFTPADDING',   (0,0), (-1,-1), 10),
        ('RIGHTPADDING',  (0,0), (-1,-1), 10),
        ('TOPPADDING',    (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
    ]))
    items.append(ftbl)
    items.append(PageBreak())
    return items

# ── 섹션 10: 실행 ─────────────────────────────────────────────────────────

def section_run():
    items = []
    items.append(section_badge('10  실행 & 테스트', C_GREEN))
    items.append(space(8))

    steps = [
        ('환경 설정 확인',
         'pip install anthropic pillow python-dotenv requests\n'
         'npm install playwright && npx playwright install chromium'),
        ('.env 파일 작성',
         '# .env\nANTHROPIC_API_KEY=sk-ant-...'),
        ('스킬 파일 복사',
         'mkdir -p ~/.claude/skills/cardnews\n'
         'cp SKILL.md ~/.claude/skills/cardnews/SKILL.md'),
        ('Claude Code에서 실행',
         '/cardnews https://store.ohou.se/goods/XXXXXX'),
        ('결과 확인 후 응답',
         '# 카드 6장 확인 후\nyes    # 카탈로그에 추가\nno     # 삭제\nhold   # 보류'),
    ]

    for i, (title, cmd) in enumerate(steps, 1):
        items.append(KeepTogether([
            space(4),
            Paragraph(f'<b>Step {i}. {title}</b>',
                      ParagraphStyle('sh', fontName='MalgunBd', fontSize=11,
                                     textColor=C_DARK, spaceBefore=8)),
        ] + code_block(cmd)))

    items.append(space(12))
    items.append(hr(C_DARK))
    items.append(space(8))

    items.append(Paragraph(
        '이 가이드가 도움이 되셨다면 팔로우 & 공유 부탁드립니다 🖤',
        ParagraphStyle('end', fontName='MalgunBd', fontSize=13,
                       textColor=C_DARK, alignment=TA_CENTER)))
    items.append(space(4))
    items.append(Paragraph(
        'Claude AI를 "같이 일하는 도구"로 활용하는 더 많은 콘텐츠를 준비 중입니다.',
        ParagraphStyle('end2', fontName='Malgun', fontSize=10,
                       textColor=C_MUTED, alignment=TA_CENTER)))

    return items

# ── 페이지 번호 ────────────────────────────────────────────────────────────

def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont('Malgun', 8)
    canvas.setFillColor(C_MUTED)
    canvas.drawCentredString(W/2, 18*mm,
        f'카드뉴스 자동화 에이전트 제작 가이드   |   {doc.page}')
    canvas.restoreState()

# ── 메인 ───────────────────────────────────────────────────────────────────

def build_pdf():
    out_path = 'C:/cardnews/카드뉴스_에이전트_제작가이드.pdf'
    doc = SimpleDocTemplate(
        out_path, pagesize=A4,
        leftMargin=40*mm, rightMargin=40*mm,
        topMargin=20*mm, bottomMargin=25*mm,
        title='카드뉴스 자동화 에이전트 제작 가이드',
        author='zipjibzip'
    )

    story = []
    story += cover_page()
    story += toc()
    story += section_overview()
    story += section_prerequisites()
    story += section_structure()
    story += section_card_spec()
    story += section_scraper()
    story += section_extractor()
    story += section_renderer()
    story += section_pipeline()
    story += section_skill()
    story += section_run()

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f'PDF 저장 완료: {out_path}')

if __name__ == '__main__':
    build_pdf()
