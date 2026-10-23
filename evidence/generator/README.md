# Original feasibility generators

These scripts generated the preceding sample. They deliberately sample selected pages, not the full
catalog. They are included as provenance, not as the production entrypoint. Use the root scrape.py
for the packaged implementation. Their historical checkpoint paths are relative to this folder.

Historical sequence: collect_sample.py, then --resume to recover Household Essentials;
enrich_sample.py, then resume after checkpointing to include all categories; validate_final.py.
Before the final enrichment pass, recommendations whose retailer category path did not match the
configured parent were marked `category_recommendation_outside_scope` in rejected.json. This excluded
143 candidates (142 newly classified and one already excluded for a promotion). The resulting
500 accepted records and selected captured retailer fields are in ../products-500.json and
../source-records.json. The final validator now checks category scope explicitly.

The original local run folder contains full HTML and earlier logs. The private repository includes
selected product/listing evidence without browser session state. A fresh run may differ as stock,
prices and website access change. No uninterrupted total runtime was recorded for the historical
multi-pass collection, so none is invented.
