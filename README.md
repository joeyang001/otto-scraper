# Otto.de Scraper — Products, Prices & Ratings

**Scrape Otto.de — Germany's #2 online retailer — into a clean, normalized, de-duplicated dataset.**

Get product name, brand, price, currency, normalized availability & condition, rating, review count, main image, product id, variation id and **search rank/position** — across search and category pages, paginated.

> Built on Otto's own schema.org product data (fast, no browser, no proxy). Ideal for **price monitoring, assortment research and catalog enrichment** in the German market.

## What you get

- **Products from any Otto.de search or category page** — pass terms or full URLs.
- **Normalized fields** — price as a number, `availability` (`in_stock`/`out_of_stock`/…), `condition` (`new`/`used`/…).
- **Merchandising signals** — rating, review count, `position` (rank on the page), `page`.
- **Identifiers** — `product_id`, `variation_id`, direct product `url`.
- **De-duplicated** by product + variation, with provenance (`search_url`, `fetched_at`, `schema_version`).

## Output fields (18 per row)

`product_id`, `variation_id`, `name`, `brand`, `price`, `currency`, `availability`, `condition`, `rating`, `review_count`, `image`, `url`, `position`, `page`, `search_term`, `search_url`, `schema_version`, `fetched_at`.

### Sample row

```json
{
  "product_id": "2085076160",
  "variation_id": "2085076237",
  "name": "Apple Macbook 13\" Notebook (…)",
  "brand": "Apple",
  "price": 699.00,
  "currency": "EUR",
  "availability": "in_stock",
  "condition": "new",
  "rating": 5,
  "review_count": 124,
  "image": "https://i.otto.de/i/otto/…?$responsive_ft2$",
  "url": "https://www.otto.de/p/apple-macbook-…-2085076160/",
  "position": 1,
  "page": 1,
  "search_term": "laptop",
  "schema_version": "1.0.0",
  "fetched_at": "2026-10-16T04:00:00+00:00"
}
```

## Input

- **Search terms** — e.g. `["laptop", "kaffeemaschine"]`.
- **Search / category URLs** — paste any Otto.de listing URL.
- **Max pages** per search, **Max products** total.

## Use cases

- **Price monitoring** — track prices and discounts across repeated runs.
- **Assortment research** — see which brands/products rank for a search.
- **Catalog enrichment** — add names, brands, ids, images, prices to your catalog.
- **Competitive tracking** — monitor Otto's German retail assortment.

## Pricing

Pay per result — **$0.70 per 1,000 products** (+ $0.005 per run start). Only pay for products returned. Free plan covers testing.

## Notes

- Public Otto.de product data only; no login.
- Only structured product data Otto.de publishes is captured; missing attributes are returned as `null`.
