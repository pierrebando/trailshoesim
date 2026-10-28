# Phase 1 report — retailer listings

Date: 2026-10-28. Details of each site: `docs/sources.md`.

## Per site

| Site | Status | Products | With price | With rating | With review count | Parsing failures |
|---|---|---|---|---|---|---|
| Tradeinn (Runnerinn, FR) | collected | 924 | 924 | 487 | 487 | 2 |
| Glisshop (added later the same day) | collected | 304 | 304 | 155 | 155 | 0 |
| Le Pape | **stopped**: Cloudflare bot challenge on every page | – | – | – | – | – |
| i-Run | **stopped**: terms forbid extracting content | – | – | – | – | – |

- 17 category pages read (main trail category + 16 brand × trail pages), 944 pages in the
  cache (76 MB gzipped, gitignored). A re-run sends 0 requests.
- Gender: Homme 486, Femme 379, Garçon (kids) 30, missing 29.
- The 2 failures are product pages with no product data at all (only shop-level JSON-LD).

Glisshop: 17 category pages + 314 product pages (27 MB cache). 13 traction overshoes
("Semelle Antidérapante") listed among the trail shoes were excluded. All 304 shoes have a
model name without colour (from the product page), a gender and a brand; 298 show a
recommended price, so `original_price_eur` is known. Ratings have one decimal (2.5 to 5.0).
Le Pape and i-Run stay stopped; eight other French retailers were checked and are
blocked by bot protection or restrictive terms (`docs/sources.md`).

## Sample records (Tradeinn)

| Title | Gender | Price € | Rating | Reviews |
|---|---|---|---|---|
| Joma Chaussures de trail running TR-6 | Homme | 117.99 | – | – |
| Altra Chaussures de trail running Olympus 6 | Femme | 122.99 | 5.0 | 6 |
| La Sportiva Chaussures de trail running Prodigio 2 GORE-TEX® | Femme | 144.00 | – | – |
| New Balance Chaussures de trail running Tektrel | Femme | 67.99 | 5.0 | 3 |
| adidas Chaussures de trail running Terrex Agravic Speed 2 | Homme | 104.00 | 5.0 | 6 |

## Sample records (Glisshop)

| Brand | Model name (from product page) | Gender | Price € | Before discount € | Rating | Reviews |
|---|---|---|---|---|---|---|
| Salomon | Xa Pro 3D V9 Gore-Tex Equipe | Homme | 109.90 | 169.90 | 5.0 | 1 |
| Scott | Kinabalu Mtn | Homme | 129.90 | 149.90 | – | – |
| Salomon | Xa Pro 3D V9 Gore-Tex W | Femme | 119.90 | 169.90 | 5.0 | 5 |
| Saucony | Peregrine 16 Wmn | Femme | 127.90 | 159.90 | 5.0 | 1 |
| VEJA | Harpie Trail | Homme, Femme | 174.90 | – | – | – |

## Known problems

1. **Two retailers instead of three.** Le Pape and i-Run are blocked; Glisshop replaces
   them. Glisshop does not show stock on its cards (`in_stock` is null).
2. **Coverage is partial.** Five category pages hit the 96-card server limit (main page,
   adidas, Salomon, Altra, New Balance), so some of their shoes are missing. Only 16 brands
   were discovered; HOKA, Scarpa, Inov-8, The North Face... were not found (either not sold
   there or not discoverable without the JavaScript backend we do not use).
3. **Ratings carry little information.** Tradeinn rounds ratings to whole stars: every
   real rating is 4 or 5.
4. **Two parser bugs were found and fixed during phase 2** (both from Tradeinn's JSON-LD):
   `bestRating` equals the rating itself, so it is not used as the scale; and 437 pages
   show a default "1 review, 4 stars" with no review in the page, which is now stored as
   null with a reason.
5. Original (pre-discount) prices are not available (filled in by JavaScript).

## What to verify

- Open 3-4 product URLs and compare price, rating and review count with the page.
- Decide whether to ask Le Pape and i-Run for permission (see `docs/sources.md`).
- Before publishing anything, ask Tradeinn about reuse of its data.
