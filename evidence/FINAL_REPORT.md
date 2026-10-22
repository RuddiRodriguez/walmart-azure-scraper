# Walmart feasibility sample

## Result

500 unique products passed the implemented checks across all 11 configured top-level categories. Collected locally using free Python libraries and a local Chrome browser, without paid scraping services or proxies.

Store: 100, Bentonville S Walton Blvd Supercenter, 406 S Walton Blvd, Bentonville, AR 72712. Pickup was selected in the website and rechecked in each accepted product response. This is the trial store used in this feasibility test; client assignment remains unconfirmed.

## Category counts

| Category | Accepted products |
|---|---:|
| Food | 36 |
| Personal Care | 49 |
| Beauty | 55 |
| Diapering | 34 |
| Feeding | 46 |
| Health & Wellness | 52 |
| Pets | 54 |
| Balloons | 28 |
| Office Supplies | 52 |
| Household Essentials | 54 |
| Art Supplies | 40 |

## Checks performed

- Exact 22-field order; string values; missing values represented by empty strings; crawl_date last.
- Zero duplicate product IDs and zero duplicate URLs in the accepted export.
- Sponsored placements excluded using listing flags and visible labels.
- Walmart seller and explicit Store 100 pickup checked in listings and product details.
- Product IDs and current prices matched between listings and product details.
- Unrelated category recommendations excluded using the retailer category path.
- UPC copied unchanged when supplied by the product response.
- Price per measure copied verbatim from the listing; never calculated.
- Approximate or variable-weight listings excluded; gupc and unit_price left empty.
- Records saved after each detail check, with source evidence. Processing continued from saved records after intentional stops.

## Field completeness

| Field | Nonempty / 500 |
|---|---:|
| zipcode | 500 |
| store_name | 500 |
| store_location | 500 |
| store_logo | 500 |
| store_brand | 500 |
| category | 500 |
| sub_category | 500 |
| product_title | 500 |
| weight | 244 |
| regular_price | 500 |
| sale_price | 28 |
| volume_deals_description | 0 |
| volume_deals_price | 0 |
| digital_deals_description | 0 |
| digital_deals_price | 0 |
| image_url | 500 |
| url | 500 |
| upc | 468 |
| gupc | 0 |
| ppm | 381 |
| unit_price | 0 |
| crawl_date | 500 |

Missing weight values mean no package weight was extracted from the title; this test did not exhaustively parse product specifications. Missing UPC values mean the inspected product response supplied none. Empty promotion fields do not establish that all possible offers were absent: ambiguous promotions were excluded.

## Exclusions

Listing-stage counts are rejected occurrences, not necessarily distinct products:

- sponsored: 269
- no_store100_pickup: 134
- non_walmart_seller: 122
- not_rendered: 677
- duplicate: 35
- approx_or_variable_weight: 1
- promotion_needs_detail_review: 1

Detail/scope-stage exclusions:

- promotion_needs_review: 15
- category_recommendation_outside_scope: 142

## Price per measure examples

- Crest Toothpaste, Premium Plus Scope Outlast Fluoride Toothpaste, Mint, 5.2 oz, 3 pack: 57.5 ¢/oz
- Hard Candy Eye Def Eyeshadow Stick, Shimmer, Creamy, Blendable Color. Metallic Champagne: $35.12/oz
- Luvs Platinum Protection Baby Diapers, Size 5, 72 Count ( Select for more options): 23.6 ¢/count
- Little Bellies Organic Strawberry Pick-Me Sticks Puff Snack, 0.56 oz: $3.82/oz
- Premier Protein Shake, Chocolate, 30g Protein, 11 Fl Oz, 12 Ct: 20.3 ¢/fl oz
- Pedigree High Protein Grilled Steak & Vegetable Flavor Adult Dry Dog Food, 40 lb Bag: 59.0 ¢/lb

## What remains unproven

- Full traversal of every subcategory and every catalog page. This sample covers all 11 parent categories but uses selected subcategory pages.
- Complete promotion extraction and volume/digital deal examples. Ambiguous promotions were deliberately omitted.
- Long-duration and repeated complete 500-product runs. Earlier separate store/pagination checks passed twice; this is one accumulated sample with resumed detail checks.
- Azure execution, unattended scheduling, multiple-store configuration, overlap protection, monitoring, and observed client acceptance.
- Complete weight extraction from product specifications and broader private-label recognition.
- A precise uninterrupted end-to-end runtime: collection and enrichment were separate passes, with intentional restarts. The saved 68-second collection timer is only the retry pass and must not be presented as total runtime.

## Evidence files

- validated_500_products.json: final accepted records.
- final_validation.json: machine-readable validation results.
- evidence.json and saved category HTML: listing data and displayed text.
- details/proofs.json and details/<product-id>.json: product response, location, price and UPC evidence.
- progress.json: visited pages, discovered links and rejection counters.
- selected_store.png: store selection screenshot.
- ../store-check/: the earlier two-session store and pagination check.

Conclusion: free local Python collection is feasible for this sample. The full contest requirements are not yet proven, and the production project has not been built.
