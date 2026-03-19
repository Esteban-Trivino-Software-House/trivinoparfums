# Trivino Parfums

Tienda web de fragancias exclusivas — Trivino Parfums.

Este repositorio contiene el código fuente de la tienda online de Trivino Parfums, construida con HTML, CSS y JavaScript puro, lista para publicar en GitHub Pages.

## 🚀 Publicar en GitHub Pages

1. Ve a **Settings** → **Pages** en este repositorio.
2. En "Source", selecciona la rama `main` y la carpeta `/ (root)`. 
3. Haz clic en **Save**.
4. En unos minutos tu tienda estará disponible en: `https://etrivinog.github.io/trivinoparfums/`

## 🛍️ Características

- Catálogo completo de perfumes con filtros por categoría
- Barra de búsqueda por nombre
- Carrito de compras persistente (localStorage)
- Pedidos directamente por WhatsApp con resumen formateado
- Diseño elegante, responsivo y mobile-first

## ✏️ Cómo actualizar productos

Edita el array `products` en el archivo `js/app.js`. Cada producto tiene esta estructura:

```js
{
  id: 1,
  name: "Nombre del Perfume",
  category: "dama", // dama | caballero | originales | estuches
  price: 116000,    // precio de venta al público (ya con tu margen)
  ml: "100ml"
}
```

## 📱 WhatsApp configurado

Los pedidos llegan al número: **+57 301 514 2547**

Para cambiarlo, edita la variable `WHATSAPP_NUMBER` al inicio de `js/app.js`.

## © 2026 Trivino Parfums
