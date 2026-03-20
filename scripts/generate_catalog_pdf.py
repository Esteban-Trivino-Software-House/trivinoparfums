#!/usr/bin/env python3
"""
Trivino Parfums — Generador de catálogo en PDF
Produce un PDF buscable con todos los productos activos del catálogo.
"""

import json
import re
import urllib.request
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph,
    Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Colores ──
DARK       = colors.HexColor("#0D0D0D")
DARK2      = colors.HexColor("#141414")
DARK3      = colors.HexColor("#1E1E1E")
GOLD       = colors.HexColor("#C9A84C")
GOLD_LIGHT = colors.HexColor("#E8C96A")
TEXT       = colors.HexColor("#F0EDE8")
TEXT_MUTED = colors.HexColor("#8A8178")
BORDER     = colors.HexColor("#2A2A2A")
WHITE      = colors.white

GRAPHQL_URL = "https://graphql.ecometri.shop/graphql"
ORIGIN      = "https://tokeperfumeria.ecometri.shop"
OUTPUT_PATH = "catalogo-trivino-parfums.pdf"

CATEGORY_LABELS = {
    "originales": "💎 Originales",
    "mujer":      "♀ Mujer",
    "hombre":     "♂ Hombre",
    "unisex":     "⚥ Unisex",
    "arabes":     "🌙 Árabes",
    "combos":     "🎁 Combos",
    "relojes":    "⌚ Relojes",
}
CATEGORY_ORDER = ["originales", "mujer", "hombre", "unisex", "arabes", "combos", "relojes"]

QUERY = """
{
  store(url: "tokeperfumeria") {
    storeCatalogs {
      collections {
        slug
        products {
          id name sku active price discountPrice
          productImages { pictureUrl order }
        }
      }
    }
  }
}
"""


def fetch_products():
    body = json.dumps({"query": QUERY}).encode()
    req = urllib.request.Request(
        GRAPHQL_URL, data=body,
        headers={"Content-Type": "application/json",
                 "origin": ORIGIN, "referer": ORIGIN + "/"}
    )
    data = json.loads(urllib.request.urlopen(req, timeout=60).read())
    return data["data"]["store"]["storeCatalogs"][0]["collections"]


def classify(pid, by_slug):
    originales = by_slug.get("originales", set())
    relojes    = by_slug.get("relojes", set())
    combos     = by_slug.get("combos-pago-de-contado", set())
    arabes     = by_slug.get("arabes", set())
    dama       = by_slug.get("dama", set())
    caballero  = by_slug.get("caballero", set())

    if pid in originales: return "originales"
    if pid in relojes:    return "relojes"
    if pid in combos:     return "combos"
    if pid in arabes:     return "arabes"
    in_d, in_c = pid in dama, pid in caballero
    if in_d and in_c:     return "unisex"
    if in_d:              return "mujer"
    if in_c:              return "hombre"
    return "unisex"


def fmt_price(p):
    return f"${p:,.0f}".replace(",", ".")


def build_products(collections):
    by_slug = {c["slug"]: {p["id"] for p in c["products"]} for c in collections}
    all_map = {p["id"]: p for c in collections for p in c["products"]}
    todo    = by_slug.get("", set())

    products = []
    for pid in todo:
        p = all_map[pid]
        if not p.get("active", True):
            continue
        wholesale = p.get("discountPrice") or p.get("price") or 0
        price = int(wholesale * 2)
        gender = classify(pid, by_slug)
        products.append({
            "name":   (p.get("name") or "").strip(),
            "sku":    (p.get("sku") or "")[:6].upper(),
            "gender": gender,
            "price":  price,
        })
    return products


def strip_html(html):
    return re.sub(r"<[^>]+>", "", html or "").strip()


# ── PDF Builder ──
def build_pdf(products):
    W, H = A4  # 210 x 297 mm

    doc = BaseDocTemplate(
        OUTPUT_PATH,
        pagesize=A4,
        leftMargin=14*mm,
        rightMargin=14*mm,
        topMargin=14*mm,
        bottomMargin=14*mm,
        title="Catálogo Trivino Parfums",
        author="Trivino Parfums",
        subject="Catálogo de fragancias premium",
    )

    frame = Frame(
        doc.leftMargin, doc.bottomMargin,
        W - doc.leftMargin - doc.rightMargin,
        H - doc.topMargin - doc.bottomMargin,
        id="main"
    )

    def draw_header(canvas, doc):
        canvas.saveState()
        # Top gold line
        canvas.setFillColor(GOLD)
        canvas.rect(0, H - 8*mm, W, 8*mm, fill=1, stroke=0)
        # Brand
        canvas.setFillColor(DARK)
        canvas.setFont("Helvetica-Bold", 13)
        canvas.drawCentredString(W/2, H - 5.8*mm, "TRIVINO PARFUMS")
        # Bottom bar
        canvas.setFillColor(DARK3)
        canvas.rect(0, 0, W, 7*mm, fill=1, stroke=0)
        canvas.setFillColor(TEXT_MUTED)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(14*mm, 2.5*mm, "Fragancias Premium · Envíos a todo Colombia")
        canvas.drawRightString(W - 14*mm, 2.5*mm, f"Pág. {doc.page}")
        canvas.restoreState()

    def draw_cover(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(DARK)
        canvas.rect(0, 0, W, H, fill=1, stroke=0)
        # Gold accent top
        canvas.setFillColor(GOLD)
        canvas.rect(0, H - 3*mm, W, 3*mm, fill=1, stroke=0)
        canvas.rect(0, 0, W, 3*mm, fill=1, stroke=0)
        # Title
        canvas.setFillColor(GOLD)
        canvas.setFont("Helvetica-Bold", 38)
        canvas.drawCentredString(W/2, H/2 + 35*mm, "TRIVINO")
        canvas.setFont("Helvetica", 28)
        canvas.drawCentredString(W/2, H/2 + 18*mm, "P A R F U M S")
        # Divider
        canvas.setStrokeColor(GOLD)
        canvas.setLineWidth(0.5)
        canvas.line(50*mm, H/2 + 10*mm, W - 50*mm, H/2 + 10*mm)
        # Subtitle
        canvas.setFillColor(TEXT_MUTED)
        canvas.setFont("Helvetica", 11)
        canvas.drawCentredString(W/2, H/2 - 2*mm, "CATÁLOGO DE FRAGANCIAS PREMIUM")
        canvas.setFont("Helvetica", 9)
        canvas.drawCentredString(W/2, H/2 - 12*mm, f"{len(products)} fragancias disponibles · Envíos a todo Colombia")
        # WhatsApp
        canvas.setFillColor(GOLD)
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawCentredString(W/2, H/2 - 28*mm, "📱 +57 312 304 2983")
        canvas.setFillColor(TEXT_MUTED)
        canvas.setFont("Helvetica", 8)
        canvas.drawCentredString(W/2, H/2 - 36*mm, "trivinoparfums · Contáctanos por WhatsApp")
        canvas.restoreState()

    cover_frame = Frame(0, 0, W, H, id="cover")
    cover_template  = PageTemplate(id="cover",  frames=[cover_frame], onPage=draw_cover)
    normal_template = PageTemplate(id="normal", frames=[frame],        onPage=draw_header)
    doc.addPageTemplates([cover_template, normal_template])

    # ── Styles ──
    cat_style = ParagraphStyle(
        "cat", fontName="Helvetica-Bold", fontSize=11,
        textColor=GOLD, spaceAfter=4, spaceBefore=10,
    )
    name_style = ParagraphStyle(
        "name", fontName="Helvetica-Bold", fontSize=7.5,
        textColor=TEXT, leading=10,
    )
    sub_style = ParagraphStyle(
        "sub", fontName="Helvetica", fontSize=6.5,
        textColor=TEXT_MUTED, leading=9,
    )
    price_style = ParagraphStyle(
        "price", fontName="Helvetica-Bold", fontSize=8,
        textColor=GOLD_LIGHT,
    )

    # ── Build story ──
    from reportlab.platypus import NextPageTemplate, PageBreak

    story = []

    # Cover page
    story.append(NextPageTemplate("normal"))
    story.append(PageBreak())

    # Group by category
    grouped = {g: [] for g in CATEGORY_ORDER}
    for p in products:
        grouped.setdefault(p["gender"], []).append(p)

    COLS = 3
    COL_W = (W - doc.leftMargin - doc.rightMargin) / COLS

    for gender in CATEGORY_ORDER:
        items = grouped.get(gender, [])
        if not items:
            continue

        # Category header
        story.append(Paragraph(CATEGORY_LABELS.get(gender, gender), cat_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=GOLD, spaceAfter=6))

        # Build rows of COLS items
        rows = [items[i:i+COLS] for i in range(0, len(items), COLS)]

        table_data = []
        for row in rows:
            cells = []
            for item in row:
                cell = [
                    Paragraph(item["name"], name_style),
                    Spacer(1, 2),
                    Paragraph(f"Cód. {item['sku']}", sub_style),
                    Paragraph(fmt_price(item["price"]), price_style),
                ]
                cells.append(cell)
            # Pad row if less than COLS
            while len(cells) < COLS:
                cells.append("")
            table_data.append(cells)

        col_widths = [COL_W] * COLS
        t = Table(table_data, colWidths=col_widths, repeatRows=0)
        t.setStyle(TableStyle([
            ("VALIGN",      (0,0), (-1,-1), "TOP"),
            ("TOPPADDING",  (0,0), (-1,-1), 6),
            ("BOTTOMPADDING",(0,0),(-1,-1), 8),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
            ("RIGHTPADDING",(0,0), (-1,-1), 6),
            ("BACKGROUND",  (0,0), (-1,-1), DARK2),
            ("ROWBACKGROUNDS",(0,0),(-1,-1), [DARK2, DARK3]),
            ("GRID",        (0,0), (-1,-1), 0.3, BORDER),
            ("LINEBELOW",   (0,0), (-1,-1), 0.3, BORDER),
        ]))
        story.append(t)
        story.append(Spacer(1, 6))

    doc.build(story)


def main():
    print("🔄 Consultando API del proveedor…")
    collections = fetch_products()

    print("⚙️  Procesando productos…")
    products = build_products(collections)
    print(f"✅ {len(products)} productos activos")

    print("📄 Generando PDF…")
    build_pdf(products)
    print(f"🎉 PDF generado: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
