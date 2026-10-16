"""
Otto.de Scraper — Germany's #2 online retailer (Otto.de) product listings.

Dependency-free (stdlib + Apify REST). Reads the schema.org JSON-LD `Product`
blocks that Otto.de server-renders on search/category pages, with pagination:
  https://www.otto.de/suche/{term}/?page=N
Normalized, de-duplicated, with rank/position + provenance on every row.
"""
from __future__ import annotations
import json, os, re, ssl, uuid
from datetime import datetime, timezone
from urllib import request as urlrequest
from urllib.parse import urlencode, quote
from urllib.error import HTTPError, URLError

SCHEMA_VERSION = "1.0.0"
API = "https://api.apify.com/v2"
UA = {"User-Agent": "otto-de-scraper/1.0 (+https://apify.com)",
      "Accept": "text/html,application/xhtml+xml", "Accept-Language": "de-DE,de;q=0.9,en;q=0.6"}
_CTX = ssl.create_default_context()
HERE = os.path.dirname(os.path.abspath(__file__))
_LD = re.compile(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', re.S)
_BASE = "https://www.otto.de"


def log(*a):
    print(*a, flush=True)


def _u(path):
    return f"{API}{path}{'&' if '?' in path else '?'}" + urlencode({"token": os.environ.get("APIFY_TOKEN", "")})


def get_input() -> dict:
    store = os.environ.get("ACTOR_DEFAULT_KEY_VALUE_STORE_ID")
    if store and os.environ.get("APIFY_TOKEN"):
        try:
            return json.loads(_get(_u(f"/key-value-stores/{store}/records/{os.environ.get('ACTOR_INPUT_KEY','INPUT')}")))
        except Exception as e:
            log(f"input fetch failed: {e}")
    if os.path.exists("input.json"):
        return json.load(open("input.json"))
    return {}


def push_items(items):
    token = os.environ.get("APIFY_TOKEN"); ds = os.environ.get("ACTOR_DEFAULT_DATASET_ID")
    if not (token and ds):
        with open("dataset_local.jsonl", "a") as f:
            for it in items:
                f.write(json.dumps(it) + "\n")
        return len(items)
    n = 0
    for i in range(0, len(items), 300):
        chunk = items[i:i + 300]
        req = urlrequest.Request(_u(f"/datasets/{ds}/items"), data=json.dumps(chunk).encode(),
                                 method="POST", headers={"Content-Type": "application/json"})
        urlrequest.urlopen(req, timeout=120, context=_CTX).read()
        n += len(chunk)
    return n


def charge(event_name, count):
    token = os.environ.get("APIFY_TOKEN"); rid = os.environ.get("ACTOR_RUN_ID")
    if not (token and rid) or count <= 0:
        return
    body = json.dumps({"eventName": event_name, "count": int(count)}).encode()
    req = urlrequest.Request(_u(f"/actor-runs/{rid}/charge"), data=body, method="POST",
                             headers={"Content-Type": "application/json", "idempotency-key": uuid.uuid4().hex})
    try:
        urlrequest.urlopen(req, timeout=30, context=_CTX).read()
    except HTTPError as e:
        try: log(f"charge {event_name} failed: {e.code} {e.read().decode()[:160]}")
        except Exception: log(f"charge {event_name} failed: {e.code}")
    except Exception as e:
        log(f"charge {event_name} failed: {e}")


def _get(url, timeout=35):
    with urlrequest.urlopen(urlrequest.Request(url, headers=UA), timeout=timeout, context=_CTX) as r:
        return r.read().decode("utf-8", "ignore")


def _now():
    return datetime.now(timezone.utc).isoformat()


def _abs(u):
    if not u:
        return None
    return u if u.startswith("http") else _BASE + u


def _pid(url):
    m = re.search(r"/p/([^/?]+)", url or "")
    if not m:
        return None
    slug = m.group(1).rstrip("/")
    return slug.rsplit("-", 1)[-1] or None


def _num(v):
    if v is None:
        return None
    s = str(v).strip()
    try:
        return float(s)  # schema.org JSON-LD uses '.' as decimal separator
    except Exception:
        pass
    try:
        return float(s.replace(".", "").replace(",", "."))  # German format fallback
    except Exception:
        return None


def _avail(v):
    return {"https://schema.org/InStock": "in_stock", "https://schema.org/OutOfStock": "out_of_stock",
            "https://schema.org/PreOrder": "preorder", "https://schema.org/BackOrder": "backorder"}.get(v, v)


def _cond(v):
    return {"https://schema.org/NewCondition": "new", "https://schema.org/UsedCondition": "used",
            "https://schema.org/RefurbishedCondition": "refurbished"}.get(v, v)


def parse_products(html, search_url, search_term, page):
    out = []
    pos = 0
    for s in _LD.findall(html):
        try:
            d = json.loads(s)
        except Exception:
            continue
        if not (isinstance(d, dict) and d.get("@type") == "Product"):
            continue
        pos += 1
        offers = d.get("offers") or {}
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        price = _num(offers.get("price"))
        var = None
        for ap in (d.get("additionalProperty") or []):
            if isinstance(ap, dict) and ap.get("name") == "variationId":
                var = ap.get("value")
        url = _abs(offers.get("url") or d.get("url"))
        ar = d.get("aggregateRating") or {}
        brand = d.get("brand")
        if isinstance(brand, dict):
            brand = brand.get("name")
        out.append({
            "product_id": _pid(url),
            "variation_id": var,
            "name": d.get("name"),
            "brand": brand,
            "price": price,
            "currency": offers.get("priceCurrency") or "EUR",
            "availability": _avail(offers.get("availability")),
            "condition": _cond(offers.get("itemCondition")),
            "rating": ar.get("ratingValue"),
            "review_count": ar.get("reviewCount"),
            "image": d.get("image"),
            "url": url,
            "position": pos,
            "page": page,
            "search_term": search_term,
            "search_url": search_url,
            "schema_version": SCHEMA_VERSION,
            "fetched_at": _now(),
        })
    return out


def build_targets(inp):
    targets = []
    for u in (inp.get("searchUrls") or []):
        if u:
            targets.append((u, None))
    for q in (inp.get("searchQueries") or []):
        q = str(q).strip()
        if q:
            targets.append((f"{_BASE}/suche/{quote(q)}/", q))
    if not targets:
        targets = [(f"{_BASE}/suche/laptop/", "laptop")]
    return targets


def main():
    inp = get_input() or {}
    targets = build_targets(inp)
    max_pages = int(inp.get("maxPages") or 5)
    max_products = int(inp.get("maxProducts") or 100000)
    seen = set(); rows = []; errors = []; pages_ok = 0
    charge("actor-start", 1)
    for base, term in targets:
        for page in range(1, max_pages + 1):
            sep = "&" if "?" in base else "?"
            u = f"{base}{sep}page={page}"
            try:
                html = _get(u)
                items = parse_products(html, base, term, page)
                pages_ok += 1
                if not items:
                    break
                for r in items:
                    k = (r.get("product_id"), r.get("variation_id"))
                    if k != (None, None) and k not in seen:
                        seen.add(k); rows.append(r)
            except (HTTPError, URLError, ValueError, KeyError) as e:
                errors.append(f"{u[:60]}: {str(e)[:60]}")
                break
    rows = rows[:max_products]
    pushed = push_items(rows)
    charge("product", len(rows))
    log(f"FINISHED pages_ok={pages_ok} pushed={pushed} errors={len(errors)}")
    if errors:
        log("Errors: " + "; ".join(errors[:15]))


if __name__ == "__main__":
    main()
