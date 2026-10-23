# Packaged runner: live sample

22 newly collected records: two per each of the 11 requested categories. Product IDs, store pickup,
Walmart seller, current prices and required field structure passed the sample checks. All 22 have
UPCs, 17 have displayed PPM values; zero duplicate IDs/URLs. No production pointer was published.

`report.json.sample_validation.passed` is true. The top-level `passed` is false on purpose: the
500-record/full-queue publication conditions are not met by a limited sample. 1,412 discovered pages
and 299 candidate products remain outside this sample. This is not a complete catalog result.

This development run used checkpoints across fixes and intentional interruptions. Its accumulated
active time was 1,079.55 seconds; elapsed time was 1,299.71 seconds. These are not an uninterrupted
benchmark and must not be attributed to the separate historical 500-record collection.

See source-records.json for captured candidate/product responses and events.jsonl for the full
progress record. recovery-check.json in the parent folder confirms the three recorded completed
pages were not processed again after resume. overlap-check.txt records a second process rejected
by the active store lock.

Later small source refinements (promotion example handling, source evidence detail) were checked
separately; this is not a claim of final Azure acceptance or an exhaustive branch-coverage test.
