# October 23 fresh local live sample

Run ID: `20261023T023324963917Z`. Started 02:33:24 UTC and completed 02:43:28 UTC
(04:43:28 CEST, Europe/Amsterdam). Parser, runner, browser, storage and validation source are
identical to commit `3b87f48`; subsequent review commits add documentation and evidence tools.

33 newly collected products, exactly three per each of the 11 configured parent categories.
Sample validation passed. Zero duplicate IDs/URLs; all 33 have UPCs, 26 have displayed PPM,
17 have extracted package weight, and two have ordinary sale prices. No live volume/digital
offers or retained unavailable products were observed in this sample.

Store 100, Bentonville, ZIP 72712, PICKUP. Captured product responses verify the local store,
Walmart seller and current listing/detail price. `source-records.json` holds corresponding captured
fields. `selected-store.png` shows the selection after resume. `environment.json` records local
Python/package versions; this ran on macOS arm64, not Azure.

## Recovery

An intentional SIGINT stopped collection between product requests after three committed records.
The same configuration was resumed. All three records remained, each was processed once, and all
20 previously completed listing/category pages had one completion event each. `recovery.json`
records these checks. This is live graceful-interruption recovery, not a mid-response hard kill.

`failure.json` and `products.partial.json` belong to that intentional interruption. They are retained
as evidence; the later `report.json`, `products.json` and final event describe the completed sample.

## Coverage and runtime limits

20 pages processed. 1,094 pages and 290 product candidates remain pending. `coverage.json` lists
every queued URL with its state. This is deliberately a small sample, not full category traversal.

597.81 accumulated active seconds; 603.99 elapsed seconds including the intentional stop/resume.
Do not use these numbers as the runtime of the historical 500-product dataset or a full catalog.

The outer report fails full publication checks because the count is below 500 and queues remain.
The nested `sample_validation.passed` is true. No `latest.json` production pointer was created.
Full HTML is retained locally; only its hashes are exported, avoiding browser session state in this
review package. Selected source fields and collection logs are included here.
