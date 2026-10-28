# Data sources: access checks and methods

Checked on **2026-10-28** (phase 1 reconnaissance). Re-check before every new collection
campaign: robots.txt files and terms change.

Summary:

| Site | robots.txt | Terms of use | Technical access | Decision |
|---|---|---|---|---|
| Le Pape (lepape.com) | allows category/product pages | could not be read automatically (blocked) | **Cloudflare bot challenge on every page, sitemap included** | **STOPPED** |
| i-Run (i-run.fr) | allows category/product pages | **explicitly forbids extracting or reusing any part of the site content** | open | **STOPPED** |
| Tradeinn / Runnerinn (tradeinn.com/runnerinn/fr) | allows category/product pages; explicitly welcomes many bots | forbids reproducing/distributing content publicly without written permission; no clause on automated access | open, server-rendered HTML + JSON-LD | **collected** (see restrictions) |

---

## Le Pape — `www.lepape.com`

**robots.txt** (`https://www.lepape.com/robots.txt`, read OK): disallows search,
customer, checkout pages and filter parameters (`?lepape_gender=`, `?price...=`, ...);
allows `?page=`; declares a sitemap at `/media/sitemap/1_sitemap_index.xml`.

**Access**: every other URL we tried returned **HTTP 403 with a Cloudflare
"Just a moment..." managed challenge** (JavaScript + cookies required), including the
homepage and the sitemap declared in robots.txt.

**Decision: STOPPED.** A bot challenge is the site telling automated clients not to
come in. Getting past it (headless browser, spoofed browser User-Agent, challenge
solving) would be working around an access restriction, which the project rules forbid.
No collector was written.

What the project owner could do instead:
- read Le Pape's terms of use in a normal browser and ask Le Pape for permission or a
  product feed;
- check whether Le Pape publishes an affiliate product feed (e.g. through an affiliate
  network), which is an official, permitted channel.

## i-Run — `www.i-run.fr`

(`irun.fr` does not serve a valid certificate; the shop lives at `i-run.fr`.)

**robots.txt** (`https://www.i-run.fr/robots.txt`): disallows `/client/`, `/panier.html`,
`/ajax/` and filter parameters (`fids=`, `cids=`, `tids=`...); declares sitemaps,
including `/chaussures_homme/sitemap.xml` and `/chaussures_femme/sitemap.xml`. Trail shoe
categories exist at `/chaussures_homme/Trail_c15/` and `/chaussures_femme/Trail_c20/`.

**Terms** (`https://www.i-run.fr/infos-pratiques/cgv.html`, intellectual property
clause): i-Run states that it is the producer of the site's databases (article L.342-1
of the French Intellectual Property Code) and *"interdit l'extraction ou la réutilisation
de tout ou partie du contenu de son Site Internet"*.

**Decision: STOPPED.** This is an explicit prohibition of exactly what a collector does
(extracting part of the content). No collector was written.

What the project owner could do instead: ask i-Run for written permission (explaining
the non-commercial school context), or drop i-Run as a source.

## Tradeinn (Runnerinn store) — `www.tradeinn.com/runnerinn/fr`

**robots.txt** (`https://www.tradeinn.com/robots.txt`): for `User-agent: *` it disallows
account, cart and checkout pages, `*/listado.php*`, `*products_search*`, `*query=*`,
`*/menu_marcas/*`, `*/ofertas*`, several image folders, and terms pages under
`*/terminos/*`. It explicitly `Allow: /` for GPTBot, ClaudeBot, CCBot, Bingbot and
others. Category pages (`.../s`, `.../sm`) and product pages (`.../p`) are allowed. No
sitemap is declared (`/sitemap.xml` returns an HTML page).

**Terms** (`/runnerinn/fr/terms/st` and `/runnerinn/fr/legal_notice/st`, both allowed by
robots.txt): no clause about robots or automated access. The intellectual property
clauses forbid reproducing, communicating to the public or distributing "all or part"
of the site content *for public or commercial purposes* without Tradeinn's express
authorisation; the legal notice says any total or partial reproduction or use of the
content needs prior written permission.

**Decision: collected**, with these restrictions:
- we store only facts (price, rating, review count, brand, title, gender, breadcrumb,
  product and image URLs), never descriptions, reviews or images;
- raw pages stay in the gitignored cache `data/raw/tradeinn/`;
- **before publishing the web app or pushing `data/interim/` to a public repository, the
  project owner should ask Tradeinn for permission**, because the legal notice can be
  read as covering any reuse of the content, including facts copied from it.

### Method

Priority list from the phase 1 brief, and what we found:

1. **Sitemap**: none declared, none found at the usual locations.
2. **Structured data**: yes. Category pages embed a schema.org `ItemList` (only the first
   30 products). Product pages embed a schema.org `ProductGroup` with `brand`,
   `aggregateRating`, `category` and one `Product` variant per colour/size with its
   `Offer` (price, availability).
3. **The JSON endpoint the site's own pages use**: the "Voir plus de produits" button
   queries Tradeinn's search backend (`sr.tradeinn.com` and an Elasticsearch Cloud
   cluster, with an authorisation header). **Not used**: it is an internal backend with
   embedded credentials, not a public API, and robots.txt disallows search URLs.
4. **HTML parsing**: **chosen**, combined with the JSON-LD of point 2.
5. **Headless browser**: not needed, and not used.

### Entry URLs and listing strategy

- Main trail category: `https://www.tradeinn.com/runnerinn/fr/chaussures-chaussures-trail-running/10005/s`
- Brand × trail category pages: `https://www.tradeinn.com/runnerinn/fr/chaussures-chaussures-trail-running/<brand-slug>/10005-<brand-id>/sm`
- Brand ids come from the store homepage (`/runnerinn/fr`, links `/<slug>/<id>/m`) and
  from the link every product page has to its own brand × trail page.

The server renders **at most 96 product cards** per category page; more are loaded by
JavaScript from the backend we don't use. So the collector:

1. reads the main trail category (96 cards);
2. reads the brand × trail page of every brand it knows (most brands have fewer than 96
   trail products, so their page is complete);
3. reads every product page found, and adds any newly discovered brand to step 2;
4. flags every category page that shows exactly 96 cards as **possibly truncated**.

### Fields and where they are

| Field | Where |
|---|---|
| product_url, raw_title, image_url | listing card (`li.product-listing-wrapper`), also JSON-LD |
| retailer product id | number in the URL `/.../<id>/p` |
| brand | product page JSON-LD `ProductGroup.brand.name` |
| gender | product page "Caractéristiques" list, item `Genre` (Homme / Femme / Unisexe...) |
| price_eur | product page JSON-LD: lowest `offers.price` among in-stock variants (fallback: listing card price) |
| original_price_eur | **not available**: the "Prix conseillé" element is empty in the HTML and filled by JavaScript, so it is stored as null with a reason |
| rating (0-5), review_count | product page JSON-LD `ProductGroup.aggregateRating` (`ratingValue` / `bestRating`, `reviewCount`). The page also has an `Organization` rating for the whole shop, which must **not** be used. |
| category breadcrumb | product page JSON-LD `BreadcrumbList` |
| retailer attributes | product page "Caractéristiques" list (drop range, weight range, width...), kept as short key/value facts for phase 2 |

### Results and data quirks (2026-10-28 run)

- 924 products from 17 category pages; 5 pages hit the 96-card limit (main page, adidas,
  Salomon, Altra, New Balance). 16 brands discovered.
- `aggregateRating.bestRating` equals `ratingValue` on almost every page, so it is not
  the scale maximum; ratings are read as 0-5 directly.
- Ratings are rounded to whole stars (all real ratings are 4 or 5).
- 437 pages show a default "1 review, 4 stars" while the page contains no review at all;
  these are stored as null with a reason, not as a rating.

### Known risks

- **Coverage**: brands that are neither on the homepage nor in any discovered product
  page are missed, and brands with more than 96 trail products are truncated. Both are
  reported by the collector.
- **Mixed category**: the trail category also contains other shoes (e.g. "running pour
  gravier"). We keep the breadcrumb and title so phase 2 can filter.
- **Variants**: Tradeinn often has one product page per gender or colour, so one model
  appears several times. Phase 2 merges them.
- **Ratings**: some ratings may come from reviews shared across Tradeinn stores.
- **Prices** depend on the delivery country (France assumed, via the `/fr` store) and on
  promotions.

---

## Replacement retailer search (2026-10-28)

Le Pape and i-Run being stopped, ten other French retailers selling trail shoes were
checked (robots.txt, homepage with our User-Agent, terms). Reconnaissance only: a few
requests per site, nothing collected.

| Retailer | robots.txt | Homepage with our User-Agent | Terms | Verdict |
|---|---|---|---|---|
| Alltricks (alltricks.fr) | 403, Cloudflare challenge | – | – | **blocked** |
| Running Conseil (running-conseil.com) | 403, Cloudflare | – | – | **blocked** |
| Decathlon (decathlon.fr) | open (product sitemaps; asks ClaudeBot for a 5 s delay) | 403, Cloudflare challenge | – | **blocked** |
| Ekosport (ekosport.fr) | open | 403, Cloudflare challenge | – | **blocked** |
| Snowleader (snowleader.com) | disallows `/fr/` | 403, Cloudflare challenge | – | **blocked** |
| Intersport (intersport.fr), incl. Endurance Shop | 403, DataDome captcha | – | – | **blocked** |
| Sport 2000 (sport2000.fr) | open | Anubis proof-of-work challenge | – | **blocked** |
| Bergfreunde (bergfreunde.fr) | timed out | – | – | not checked further |
| Au Vieux Campeur (auvieuxcampeur.fr) | open, `Crawl-delay: 15` | 200 OK | legal notice: content may only be extracted and displayed on screen or printed **for private use**; any partial reproduction or exploitation needs written permission | **stopped (terms)** |
| **Glisshop (glisshop.com)** | open (only cart, account, search and `?sortBy` disallowed) | 200 OK (needs a normal `Accept: text/html` header) | CGV and legal notice: **no clause** on extraction, reproduction or automated access | **collected** |

### Glisshop — method (implemented in `pipeline/collect/glisshop.py`)

- **Method: HTML parsing.** No sitemap. Category pages give every retail field; each
  product page is also read once, because its embedded JSON
  (`window.__change[...] = {...}`) gives the **model name without colour**
  (`rootProduct.common.title`, e.g. "Prodigio" for "Prodigio Yellow Black"), the gender
  and short facts (terrain, distance, foot width, runner weight, type). About 340
  requests in total.
- **Entry URLs:** `https://www.glisshop.com/trail-running/chaussures-trail/homme/` and
  `.../femme/` (gender comes from the category), plus
  `/trail-running/chaussures-gravel-running/` (gravel, to flag). Pagination:
  `?pageNumber-10=N`, followed through `rel="next"`. 24 cards per page; 321 trail shoes
  in total, 182 for men.
- **Fields on each card** (`div.product-list-item`): brand (`.product-brand span`),
  title (`.product-label_title`), product URL (ends with a numeric product id), image
  URL, rating (`title="Note : 4.8 sur 5"`, one decimal), review count (`"6 avis"`),
  current price (`.price-value`) and recommended price (`.advice-price__price`, so
  `original_price_eur` is available here), discount %.
- **Brands:** Asics, Dynafit, La Sportiva, Lowa, Merrell, Millet, Mizuno, Rossignol,
  Salomon, Saucony, Scarpa, Scott (+ adidas). Overlap with Tradeinn: Asics, La Sportiva,
  Salomon, adidas, Merrell, Mizuno, Saucony. New: Dynafit, Scarpa, Scott, Rossignol,
  Lowa, Millet.
- **Traps:**
  - The page JSON-LD has a `Product` with `aggregateRating` 4.8 / 18 822 reviews. That
    is the **shop's** "Avis vérifiés" rating, not a product rating: never use it.
  - Titles include marketing colour names ("Black Phantom Pewter", "Sunburn Fortune
    yellow N.atlant"). Solved with the model name from the product page JSON (above).
  - Stock is not shown on cards: `in_stock` is null.
  - A shoe can be listed in several categories (men's, women's, gravel); it is kept
    once. A gravel shoe listed under "trail" is recognised by its "Type" fact.
  - Cards have a short marketing description: not stored.

---

## Manufacturer sites (phase 3, checked 2026-10-28)

One site per brand of the catalogue (25 brands). For each: robots.txt, the homepage with
our User-Agent, and the terms of use. The machine-readable version of this table is
`pipeline/config/manufacturers.yaml`.

**Rule added in phase 3:** a robots.txt that disallows AI crawlers by name (ClaudeBot,
anthropic-ai, Claude-Web) is respected even though our User-Agent is different, because
an AI assistant is doing the collection. Likewise a robots.txt that bans scripted
clients (Python-requests, curl) applies to us.

| Brand | Models | Verdict | Why |
|---|---|---|---|
| Merrell | 15 | **allowed** | robots.txt allows ClaudeBot; terms forbid collecting **prices** by robot: we read specs only |
| Saucony | 8 | **allowed** | same group and terms as Merrell: specs only, no prices |
| Mizuno | 13 | **allowed** | open robots.txt, no clause on automated access |
| Puma | 8 | **allowed** | open robots.txt, no clause found |
| Scarpa | 7 | **allowed** | open robots.txt, no clause found |
| NNormal | 6 | **allowed** | open robots.txt, legal notice (PDF) has no such clause |
| Dynafit | 4 | **allowed** | open robots.txt, no clause found |
| Lowa | 4 | **allowed** | open robots.txt, no clause found |
| VEJA | 2 | allowed, not collected | no sitemap published; discovery not implemented |
| La Sportiva | 19 | blocked | robots.txt itself returns HTTP 403 |
| Altra, Asics, adidas, Brooks | 16, 16, 15, 7 | blocked | Akamai bot protection (403) |
| New Balance | 10 | blocked | 403 error page |
| Salomon | 9 | blocked | PerimeterX ("Access to this page has been denied") |
| Scott | 8 | blocked | Incapsula bot challenge |
| Joma | 14 | blocked | robots.txt disallows Python-requests, curl, Python-urllib |
| Craft | 8 | blocked | robots.txt disallows ClaudeBot and anthropic-ai |
| Inov-8 | 4 | blocked | robots.txt disallows ClaudeBot, Claude-Web, anthropic-ai |
| Rossignol | 5 | blocked | terms forbid systematic extraction and robots/scrapers |
| Vibram FiveFingers | 9 | blocked | terms page behind a Cloudflare challenge: terms could not be checked |
| Under Armour, Millet | 7, 3 | blocked | terms pages rendered by JavaScript: could not be checked |
| Tecnica | 3 | blocked | site unreachable (TLS certificate error) |

Method for allowed sites: the brand's sitemap (French locale) lists product URLs; a model
is matched by the words and version in the URL slug; the page text from the product
title onwards is read with label-based rules, and every value keeps a verbatim snippet
(see `pipeline/specs/`).

---

## Specialist review sources (phase 4, step A — checked 2026-10-28)

Same checks as before (robots.txt incl. AI-crawler bans, homepage with our User-Agent,
terms), then a coverage estimate: the review URLs of each source (sitemap, or the
RunRepeat catalogue) were matched against **all 220 catalogue models** with the strict
rule of phase 3 (model words in order, then the exact version: "Speedgoat 5" never
matches "Speedgoat 6"). A 20-model sample (Peregrine 16, XA Pro 3D V9, Bushido 3, Lone
Peak 9+, Cascadia 20, Kjerag 2...) was also checked by hand. Only sitemaps, catalogue
pages and 2 review pages were downloaded.

### English sources

| Source | robots.txt | Terms | Discovery | Coverage (220 models) | Content |
|---|---|---|---|---|---|
| **RunRepeat** | allowed (only search and filter parameters disallowed) | short legal disclaimer, no clause on automated access; the site sells **"Data licensing"** | trail catalogue `/catalog/trail-running-shoes?page=N` (6 pages, 178 shoes; the sitemap in robots.txt is 404) | **44 (20 %)**; sample 9/20 | score /100 + sub-scores ("Our verdict 88, Gravel 94, Technical 62"), "Who should buy", **lab measurements** (heel/forefoot stack measured vs brand, drop, weight, lug depth, durability tests) |
| **Believe in the Run** | allowed | no robots/scraping clause; forbids copying or reproducing "any part" of the platform | sitemap (`/shoe-reviews/` URLs: 1 588) | **69 (31 %)**; sample 8/20 (+2 video reviews) | letter grades (Design / Value / Performance), stated specs; no lab measurements seen |
| Doctors of Running | **disallows `anthropic-ai` and `Claude-Web`** | – | – | – | **blocked** (AI-crawler ban, see the phase 3 rule) |

RunRepeat or Believe in the Run: **84 models (38 %)**, 29 covered by both.

### French-language candidates

| Candidate | Access | Terms | Test articles in sitemap | Coverage (220 models) | Notes |
|---|---|---|---|---|---|
| **Esprit Trail** (esprit-trail.com) | open | legal notice: no clause on reuse or automation | 44 tests (`/test-...`) | **9 (4 %)**, adds 2 models not covered by the English sources | real trail-shoe tests (Tomir 2.0, Peregrine 13, Spin Planet, Kinabalu 3...) |
| **u-Trail** (u-trail.com) | open (`Allow: /`) | no legal notice found | 56 tests | **5 (2 %)**, adds 0 | many shoe pages are news (launches, deals), not tests |
| **Jogging International** | open | forbids any reproduction **and deep links** to its pages | 418 test/shoe URLs, mostly road | **6 (3 %)**, adds 1 | deep-link ban conflicts with storing review links |
| Running Addict | open | forbids reproduction of articles, welcomes links | 159 tests, road-focused | 0 | not useful for trail |
| Lepape-info | open (separate domain from lepape.com) | not checked | 187, mostly old/road | 0 | not useful |
| Génération Trail | sitemaps answer **410 Gone** | – | – | – | site seems repurposed |
| Runactu | times out | – | – | – | unreliable |
| runners.fr | HTTP 401 on every page | – | – | – | blocked |
| Trail Session | parked domain | – | – | – | not a source |

**Recommendation for the French source: Esprit Trail** (most real trail-shoe tests, no
restrictive clause found). Whatever the choice, the French source adds little coverage
(0-2 models); its value is a second opinion and French text for phase 5.

Expected distribution with RunRepeat + Believe in the Run + Esprit Trail:
0 tests: 134 models, 1: 53, 2: 30, 3: 3.

Caveats to settle before publication: RunRepeat sells its lab data (publishing its
measurements in the web app is redistribution); Believe in the Run's terms forbid
reproducing any part (we would store <= 30-word excerpts and links only).
