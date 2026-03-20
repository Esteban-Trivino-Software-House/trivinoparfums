#!/usr/bin/env python3
"""
Trivino Parfums — Generador de catálogo en PDF
Produce un PDF buscable con todos los productos activos del catálogo,
incluyendo una imagen por cada perfume.
"""

import io
import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph,
    Spacer, Table, TableStyle, HRFlowable, NextPageTemplate, PageBreak
)
from reportlab.platypus import Image as RLImage
from PIL import Image as PILImage

# ── Colores ──
DARK       = colors.HexColor("#0D0D0D")
DARK2      = colors.HexColor("#141414")
DARK3      = colors.HexColor("#1E1E1E")
GOLD       = colors.HexColor("#C9A84C")
GOLD_LIGHT = colors.HexColor("#E8C96A")
TEXT       = colors.HexColor("#F0EDE8")
TEXT_MUTED = colors.HexColor("#8A8178")
BORDER     = colors.HexColor("#2A2A2A")

GRAPHQL_URL = "https://graphql.ecometri.shop/graphql"
ORIGIN      = "https://tokeperfumeria.ecometri.shop"
IMAGE_CDN   = "https://d1b50uin55dq3m.cloudfront.net/fit-in/200x200/"
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


def fetch_collections():
    body = json.dumps({"query": QUERY}).encode()
    req = urllib.request.Request(
        GRAPHQL_URL, data=body,
        headers={"Content-Type": "application/json",
                 "origin": ORIGIN, "referer": ORIGIN + "/"}
    )
    return json.loads(urllib.request.urlopen(req, timeout=60).read()
                      )["data"]["store"]["storeCatalogs"][0]["collections"]


def classify(pid, by_slug):
    if pid in by_slug.get("originales", set()):          return "originales"
    if pid in by_slug.get("relojes", set()):              return "relojes"
    if pid in by_slug.get("combos-pago-de-contado", set()): return "combos"
    if pid in by_slug.get("arabes", set()):               return "arabes"
    in_d = pid in by_slug.get("dama", set())
    in_c = pid in by_slug.get("caballero", set())
    if in_d and in_c: return "unisex"
    if in_d:          return "mujer"
    if in_c:          return "hombre"
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
        imgs = sorted(p.get("productImages") or [], key=lambda x: x.get("order", 0))
        first_img = imgs[0]["pictureUrl"] if imgs else None
        img_url = (IMAGE_CDN + first_img) if first_img and not first_img.startswith("http") else first_img
        products.append({
            "name":    (p.get("name") or "").strip(),
            "sku":     (p.get("sku") or "")[:6].upper(),
            "gender":  classify(pid, by_slug),
            "price":   int(wholesale * 2),
            "img_url": img_url,
            "img_data": None,
        })
    return products


def download_image(product):
    """Download and resize image to 120x120 JPEG bytes. Returns (idx, bytes_or_None)."""
    url = product.get("img_url")
    if not url:
        return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        raw = urllib.request.urlopen(req, timeout=10).read()
        img = PILImage.open(io.BytesIO(raw)).convert("RGB")
        img.thumbnail((120, 120), PILImage.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=70, optimize=True)
        return buf.getvalue()
    except Exception:
        return None


def fetch_images(products, workers=30):
    print(f"  Descargando {len(products)} imágenes ({workers} en paralelo)…")
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(download_image, p): i for i, p in enumerate(products)}
        done = 0
        for fut in as_completed(futures):
            idx = futures[fut]
            products[idx]["img_data"] = fut.result()
            done += 1
            if done % 50 == 0 or done == len(products):
                print(f"    {done}/{len(products)}", end="\r")
    ok = sum(1 for p in products if p["img_data"])
    print(f"\n  ✅ {ok} imágenes descargadas, {len(products)-ok} sin imagen")


# ── PDF Builder ──
def build_pdf(products):
    W, H = A4
    IMG_SIZE = 18 * mm   # tamaño imagen en el PDF
    COLS     = 3
    COL_W    = (W - 28*mm) / COLS   # 14mm margen c/lado

    doc = BaseDocTemplate(
        OUTPUT_PATH, pagesize=A4,
        leftMargin=14*mm, rightMargin=14*mm,
        topMargin=18*mm, bottomMargin=12*mm,
        title="Catálogo Trivino Parfums",
        author="Trivino Parfums",
        subject="Catálogo de fragancias premium",
    )

    frame = Frame(doc.leftMargin, doc.bottomMargin,
                  W - 28*mm, H - 30*mm, id="main")

    def draw_header(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(GOLD)
        canvas.rect(0, H - 10*mm, W, 10*mm, fill=1, stroke=0)
        canvas.setFillColor(DARK)
        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawCentredString(W/2, H - 6.5*mm, "TRIVINO PARFUMS  ·  CATÁLOGO DE FRAGANCIAS")
        canvas.setFillColor(DARK3)
        canvas.rect(0, 0, W, 8*mm, fill=1, stroke=0)
        canvas.setFillColor(TEXT_MUTED)
        canvas.setFont("Helvetica", 6.5)
        canvas.drawString(14*mm, 2.8*mm, "trivinoparfums  ·  WhatsApp +57 312 304 2983")
        canvas.drawRightString(W - 14*mm, 2.8*mm, f"Pág. {doc.page}")
        canvas.restoreState()

    def draw_cover(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(DARK)
        canvas.rect(0, 0, W, H, fill=1, stroke=0)
        canvas.setFillColor(GOLD)
        canvas.rect(0, H - 3*mm, W, 3*mm, fill=1, stroke=0)
        canvas.rect(0, 0, W, 3*mm, fill=1, stroke=0)
        canvas.setFillColor(GOLD)
        canvas.setFont("Helvetica-Bold", 40)
        canvas.drawCentredString(W/2, H/2 + 38*mm, "TRIVINO")
        canvas.setFont("Helvetica", 30)
        canvas.drawCentredString(W/2, H/2 + 20*mm, "P A R F U M S")
        canvas.setStrokeColor(GOLD)
        canvas.setLineWidth(0.5)
        canvas.line(40*mm, H/2 + 12*mm, W - 40*mm, H/2 + 12*mm)
        canvas.setFillColor(TEXT_MUTED)
        canvas.setFont("Helvetica", 11)
        canvas.drawCentredString(W/2, H/2, "CATÁLOGO DE FRAGANCIAS PREMIUM")
        canvas.setFont("Helvetica", 9)
        canvas.drawCentredString(W/2, H/2 - 11*mm,
            f"{len(products)} fragancias disponibles  ·  Envíos a todo Colombia")
        canvas.setFillColor(GOLD)
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawCentredString(W/2, H/2 - 28*mm, "📱 +57 312 304 2983")
        canvas.setFillColor(TEXT_MUTED)
        canvas.setFont("Helvetica", 8)
        canvas.drawCentredString(W/2, H/2 - 37*mm, "Contáctanos por WhatsApp para hacer tu pedido")
        canvas.restoreState()

    cover_frame = Frame(0, 0, W, H, id="cover")
    doc.addPageTemplates([
        PageTemplate(id="cover",  frames=[cover_frame], onPage=draw_cover),
        PageTemplate(id="normal", frames=[frame],        onPage=draw_header),
    ])

    # ── Styles ──
    cat_style = ParagraphStyle(
        "cat", fontName="Helvetica-Bold", fontSize=11,
        textColor=GOLD, spaceAfter=3, spaceBefore=8,
    )
    name_style = ParagraphStyle(
        "name", fontName="Helvetica-Bold", fontSize=6.8,
        textColor=TEXT, leading=9,
    )
    sub_style = ParagraphStyle(
        "sub", fontName="Helvetica", fontSize=6,
        textColor=TEXT_MUTED, leading=8,
    )
    price_style = ParagraphStyle(
        "price", fontName="Helvetica-Bold", fontSize=7.5,
        textColor=GOLD_LIGHT,
    )

    story = [NextPageTemplate("normal"), PageBreak()]

    grouped = {g: [] for g in CATEGORY_ORDER}
    for p in products:
        grouped.setdefault(p["gender"], []).append(p)

    for gender in CATEGORY_ORDER:
        items = grouped.get(gender, [])
        if not items:
            continue

        story.append(Paragraph(CATEGORY_LABELS.get(gender, gender), cat_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=GOLD, spaceAfter=5))

        rows = [items[i:i+COLS] for i in range(0, len(items), COLS)]
        table_data = []

        for row in rows:
            cells = []
            for item in row:
                # Image
                if item["img_data"]:
                    img = RLImage(io.BytesIO(item["img_data"]),
                                  width=IMG_SIZE, height=IMG_SIZE)
                    img.hAlign = "CENTER"
                else:
                    img = Spacer(IMG_SIZE, IMG_SIZE)

                cell = [
                    img,
                    Spacer(1, 2),
                    Paragraph(item["name"], name_style),
                    Paragraph(f"Cód. {item['sku']}", sub_style),
                    Paragraph(fmt_price(item["price"]), price_style),
                ]
                cells.append(cell)
            while len(cells) < COLS:
                cells.append("")
            table_data.append(cells)

        t = Table(table_data, colWidths=[COL_W] * COLS)
        t.setStyle(TableStyle([
            ("VALIGN",       (0,0), (-1,-1), "TOP"),
            ("ALIGN",        (0,0), (-1,-1), "CENTER"),
            ("TOPPADDING",   (0,0), (-1,-1), 7),
            ("BOTTOMPADDING",(0,0), (-1,-1), 8),
            ("LEFTPADDING",  (0,0), (-1,-1), 5),
            ("RIGHTPADDING", (0,0), (-1,-1), 5),
            ("ROWBACKGROUNDS",(0,0),(-1,-1), [DARK2, DARK3]),
            ("GRID",         (0,0), (-1,-1), 0.3, BORDER),
        ]))
        story.append(t)
        story.append(Spacer(1, 5))

    doc.build(story)


def main():
    print("🔄 Consultando API del proveedor…")
    collections = fetch_collections()
    print("⚙️  Procesando productos…")
    products = build_products(collections)
    print(f"✅ {len(products)} productos activos")
    fetch_images(products)
    print("📄 Generando PDF…")
    build_pdf(products)
    print(f"🎉 PDF generado: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
