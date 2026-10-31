# Transport types

These three services are different and their results must not be mixed.

## Browser proxy

Chrome runs normally, but all of its traffic passes through the proxy. One page can create many provider requests because images, scripts and other browser files also pass through it. Browser cookies and the store-selection session can continue between pages. Every accepted response must still prove Store 100, ZIP 72712 and PICKUP.

## Web Unblocker

The target URL is sent to a provider that tries to return unblocked page content. It is not automatically the same continuous browser session. Store cookies and pickup state may be missing or changed. Each returned page must prove the required store, ZIP and fulfillment context before use.

## Web Scraper API

The provider reads the retailer page and returns structured fields. The provider decides which fields to return. A response can omit PICKUP or silently return another store. The scraper must reject it unless product ID, Store 100, ZIP 72712, PICKUP and price are present together.

None of the bounded provider tests produced an accepted product for publication.
