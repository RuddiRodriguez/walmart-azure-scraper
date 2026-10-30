# Web Unblocker bounded result — 30 October 2026

Web Unblocker loaded the known control product and Art Sets listing without a challenge page. It did
not preserve the required local store context.

- Control product ID was correct, but response showed Store 1631, ZIP 23666 and SHIPPING.
- Art Sets listing showed Store 5867 and no verified PICKUP facet.
- Both responses were rejected.
- No product was accepted and no full collection was started.
- Web Unblocker used 20.47 MB and cost $0.15. Total account spending, including the earlier
  residential-proxy test, was $0.23.

This result confirms access improved, but access alone is not enough. Store 100, ZIP 72712 and
PICKUP must be present in every accepted response. Web Unblocker does not support ZIP targeting for
this Walmart flow, so it does not pass the required safety gate.

Privacy-safe evidence is in `evidence/web-unblocker-bounded-20261030/RESULT.json`. Raw HTML and
credentials remain private.
