# Finite taxonomy strategy

Problem: broad link discovery treated sibling, brand, filter and promotional pages as new subcategories. Queue could grow faster than pages were reviewed.

Applied rules:

1. Keep retailer category identifiers as canonical identities.
2. Accept a discovered category only when its identifier continues the current category path.
3. Keep pagination separate from category discovery.
4. Preserve rejected links with explicit reasons; never erase evidence.
5. Stop after two consecutive batches where new pages equal or exceed processed pages.
6. Find genuine offers through a separate targeted review, not broad taxonomy crawling.

Offline result: 137 definite bad pending entries reclassified, 2,443 pending reduced to 2,306. No retailer request used.

Research basis:

- Google: faceted navigation can generate effectively infinite URL spaces and waste crawl resources: https://developers.google.com/crawling/docs/faceted-navigation
- Google: manage URL inventory and consolidate duplicates: https://developers.google.com/crawling/docs/crawl-budget
- Scrapy: filter extracted links by allowed patterns and keep duplicate filtering enabled: https://docs.scrapy.org/en/latest/topics/link-extractors.html
- Python: split and rebuild URLs by their structural parts: https://docs.python.org/3/library/urllib.parse.html
