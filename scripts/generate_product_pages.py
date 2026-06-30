#!/usr/bin/env python3
"""
Trivino Parfums — Generador de páginas de producto estáticas
Cada archivo p/{sku}.html tiene OG tags correctos para WhatsApp
y redirige al usuario a la tienda principal con el modal abierto.
"""

import json
import os
import urllib.request

GRAPHQL_URL = "https://graphql.ecometri.shop/graphql"
ORIGIN      = "https://tokeperfumeria.ecometri.shop"
IMAGE_CDN   = "https://d1b50uin55dq3m.cloudfront.net/fit-in/800x800/"
BASE_URL    = "https://esteban-trivino-software-house.github.io/trivinoparfums"
OUTPUT_DIR  = "p"

QUERY = """
{
  store(url: "tokeperfumeria") {
    collections {
      slug
      products {
        id name sku active price discountPrice
        productImages { pictureUrl order }
      }
    }
  }
}
"""


def fetch():
    body = json.dumps({"query": QUERY}).encode()
    req = urllib.request.Request(
        GRAPHQL_URL, data=body,
        headers={"Content-Type": "application/json",
                 "origin": ORIGIN, "referer": ORIGIN + "/"}
    )
    return json.loads(urllib.request.urlopen(req, timeout=60).read()
                      )["data"]["store"]["collections"]


def image_url(pic):
    if not pic: return ""
    return pic if pic.startswith("http") else IMAGE_CDN + pic


def generate_page(sku, name, img, price):
    price_fmt = f"${price:,.0f}".replace(",", ".")
    desc = f"Fragancia premium · {price_fmt} · Duración 8-12 horas · Envíos a todo Colombia"
    page_url = f"{BASE_URL}/p/{sku}"
    store_url = f"{BASE_URL}/?p={sku}"

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>{name} – Trivino Parfums</title>
  <meta name="description" content="{desc}"/>

  <!-- Open Graph / WhatsApp -->
  <meta property="og:type"         content="product"/>
  <meta property="og:url"          content="{page_url}"/>
  <meta property="og:title"        content="{name}"/>
  <meta property="og:description"  content="{desc}"/>
  <meta property="og:image"        content="{img}"/>
  <meta property="og:image:width"  content="800"/>
  <meta property="og:image:height" content="800"/>
  <meta property="og:site_name"    content="Trivino Parfums"/>
  <meta property="og:locale"       content="es_CO"/>

  <!-- Redirige a la tienda con el producto abierto -->
  <meta http-equiv="refresh" content="0;url={store_url}"/>
</head>
<body>
  <script>window.location.replace({json.dumps(store_url)});</script>
  <p>Redirigiendo a <a href="{store_url}">Trivino Parfums</a>…</p>
</body>
</html>"""


def main():
    print("🔄 Consultando API del proveedor…")
    collections = fetch()

    all_map = {p["id"]: p for c in collections for p in c["products"]}
    todo     = {p["id"] for c in collections if c["slug"] == "" for p in c["products"]}

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    generated = 0
    for pid in todo:
        p = all_map[pid]
        if not p.get("active", True):
            continue
        sku = (p.get("sku") or "")[:6].lower()
        if not sku:
            continue
        name = (p.get("name") or "").strip().replace('"', "&quot;")
        wholesale = p.get("discountPrice") or p.get("price") or 0
        price = int(wholesale * 2)
        imgs = sorted(p.get("productImages") or [], key=lambda x: x.get("order", 0))
        img = image_url(imgs[0]["pictureUrl"]) if imgs else ""

        html = generate_page(sku, name, img, price)
        path = os.path.join(OUTPUT_DIR, f"{sku}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        generated += 1

    print(f"✅ {generated} páginas generadas en {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
