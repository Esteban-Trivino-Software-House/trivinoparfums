#!/usr/bin/env python3
"""
Trivino Parfums — Sincronización automática del catálogo
Consulta la API del proveedor (TOKE Perfumería) y actualiza el array de
productos en index.html, conservando la lógica de precios y categorías.
"""

import json
import re
import sys
import urllib.request

GRAPHQL_URL = "https://graphql.ecometri.shop/graphql"
STORE_URL = "tokeperfumeria"
ORIGIN = "https://tokeperfumeria.ecometri.shop"
IMAGE_CDN = "https://d1b50uin55dq3m.cloudfront.net/fit-in/800x800/"
WHATSAPP_PRICE_MULTIPLIER = 2

HTML_PATH = "index.html"

QUERY = """
{
  store(url: "%s") {
    collections {
      id
      name
      slug
      products {
        id
        name
        sku
        description
        price
        discountPrice
        active
        productImages {
          pictureUrl
          order
        }
      }
    }
  }
}
""" % STORE_URL


def fetch():
    body = json.dumps({"query": QUERY}).encode()
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "origin": ORIGIN,
            "referer": ORIGIN + "/",
        },
    )
    resp = urllib.request.urlopen(req, timeout=60)
    return json.loads(resp.read())


def image_url(pic):
    if not pic:
        return ""
    if pic.startswith("http"):
        return pic
    return IMAGE_CDN + pic


def clean_desc(html):
    if not html:
        return ""
    # Escape backslash-quotes for embedding in JS string
    return html.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")


def build_products(data):
    collections = data["data"]["store"]["collections"]

    # Build sets of product IDs per collection slug
    by_slug = {}
    all_products_map = {}  # id -> product dict

    for col in collections:
        slug = col["slug"]
        by_slug[slug] = set()
        for p in col["products"]:
            by_slug[slug].add(p["id"])
            if p["id"] not in all_products_map:
                all_products_map[p["id"]] = p

    dama = by_slug.get("dama", set())
    caballero = by_slug.get("caballero", set())
    arabes = by_slug.get("arabes", set())
    relojes = by_slug.get("relojes", set())
    combos = by_slug.get("combos-pago-de-contado", set())
    originales = by_slug.get("originales", set())

    def classify(pid):
        if pid in originales:
            return "originales"
        if pid in relojes:
            return "relojes"
        if pid in combos:
            return "combos"
        if pid in arabes:
            return "arabes"
        in_d = pid in dama
        in_c = pid in caballero
        if in_d and in_c:
            return "unisex"
        if in_d:
            return "mujer"
        if in_c:
            return "hombre"
        return "unisex"

    # Use "todo" collection (slug="") as the master list, solo productos activos
    todo = {pid for pid in by_slug.get("", set()) if all_products_map[pid].get("active", True)}
    if not todo:
        # Fallback: union of all
        todo = set(all_products_map.keys())

    # Sort: originales first, then by id for determinism
    def sort_key(pid):
        g = classify(pid)
        order = ["originales", "mujer", "hombre", "unisex", "arabes", "combos", "relojes"]
        try:
            return (order.index(g), pid)
        except ValueError:
            return (99, pid)

    sorted_ids = sorted(todo, key=sort_key)

    products = []
    for num, pid in enumerate(sorted_ids, 1):
        p = all_products_map[pid]
        wholesale = p.get("discountPrice") or p.get("price") or 0
        our_price = int(wholesale * WHATSAPP_PRICE_MULTIPLIER)

        images = sorted(p.get("productImages") or [], key=lambda x: x.get("order", 0))
        img_urls = [image_url(i["pictureUrl"]) for i in images if i.get("pictureUrl")]

        sku = (p.get("sku") or "")[:6]
        name = (p.get("name") or "").strip()
        brand = name.split()[0].title() if name else ""
        desc = clean_desc(p.get("description") or "")
        gender = classify(pid)

        products.append({
            "num": num,
            "name": name,
            "sku": sku,
            "brand": brand,
            "gender": gender,
            "price": our_price,
            "images": img_urls,
            "desc": desc,
        })

    return products


def products_to_js(products):
    lines = []
    for p in products:
        imgs = json.dumps(p["images"])
        # Inline template literal for desc to handle multiline HTML safely
        desc_escaped = p["desc"].replace("\n", " ").replace("\r", "")
        lines.append(
            f'    {{id:{p["num"]},name:{json.dumps(p["name"])},sku:{json.dumps(p["sku"])},'
            f'brand:{json.dumps(p["brand"])},gender:{json.dumps(p["gender"])},'
            f'price:{p["price"]},images:{imgs},desc:{json.dumps(desc_escaped)}}}'
        )
    return "[\n" + ",\n".join(lines) + "\n  ]"


def update_html(js_array):
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    pattern = r"(const products\s*=\s*)\[[\s\S]*?\];"
    if not re.search(pattern, html):
        print("⚠️  No se encontró el array de productos en index.html")
        sys.exit(1)

    # Replace the products array between markers
    new_html = re.sub(
        pattern,
        lambda m: m.group(1) + js_array + ";",
        html,
        count=1,
    )

    if new_html == html:
        print("ℹ️  Catálogo sin cambios, no se requiere actualización.")
        return

    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(new_html)


def main():
    print("🔄 Consultando API del proveedor…")
    data = fetch()

    print("⚙️  Procesando productos…")
    products = build_products(data)
    print(f"✅ {len(products)} productos encontrados")

    js_array = products_to_js(products)

    print("✍️  Actualizando index.html…")
    update_html(js_array)
    print("🎉 ¡index.html actualizado exitosamente!")


if __name__ == "__main__":
    main()
