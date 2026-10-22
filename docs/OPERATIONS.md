# Operation and recovery

## Existing Azure Ubuntu VM

Use an existing x86_64 Ubuntu 24.04 VM with Chrome support, initially 2 vCPU / 4 GB RAM or larger.
This is a sizing starting point, not a measured capacity guarantee. No inbound port is needed by the
scraper. Use your existing approved VM administration method. No Azure resources were created here.

Copy this project to `/opt/walmart-scraper`, review `deploy/install-ubuntu.sh`, then run it with sudo.
Run a manual sample as the dedicated user:

```bash
sudo -u walmart env HOME=/var/lib/walmart-scraper xvfb-run -a \
  /opt/walmart-scraper/.venv/bin/python /opt/walmart-scraper/scrape.py \
  --config /opt/walmart-scraper/config/stores.json \
  --categories /opt/walmart-scraper/config/categories.csv \
  --output /var/lib/walmart-scraper/data --store 100 --sample 2
```

After a full acceptance run, enable twice-weekly scheduling:

```bash
sudo systemctl enable --now walmart-scraper@100.timer
systemctl list-timers 'walmart-scraper@*'
journalctl -u walmart-scraper@100.service
```

Timer: Monday/Thursday 02:00 UTC, plus up to 15 minutes random delay. Local Amsterdam time changes
with daylight saving. The timer does not overlap its own service; a per-store OS lock also prevents
manual overlap on this same machine. Do not run two machines against the same output directory.

## Restart

A killed process releases the OS lock. SQLite commits a page and its newly discovered work together;
a product is marked complete only with its record or explicit rejection. Resume skips committed
work, not merely the last URL attempted. An interrupted response is retried. Review logs first.
Use `--resume` with identical mode/configuration. Start fresh when checkpoint age exceeds 48 hours.

## Monitoring

Each run writes `events.jsonl`, `checkpoint.sqlite`, raw sources and `report.json` where completed.
Process failure produces a nonzero exit. Publication failures must also be monitored via `report.json`
and `latest.json` age. A sample intentionally has no production publication.
Alert externally if the systemd service fails, latest data exceeds four days, categories disappear,
or a full report fails. Connect these outputs to the client's existing Azure Monitor setup during
installation; this project does not invent a workspace or credentials.

## Adding stores/categories

Add an observed store number, name, ZIP, address and stable locally available canary product URL to
`config/stores.json`. Canary URLs must come from that store's actual product pages. Validate pickup
and the store response manually before enabling a timer instance for its number.
Add category rows to `config/categories.csv`. For unusual retailer category names, update the explicit
mapping in `extract.scope`. Verify discovered children and exclusions before production publication.

## Retention

Retain latest successful run and evidence needed for auditing. Archive older completed run folders
according to client retention policy. Never remove the run referenced by latest.json.

## Costs

Paid scraping APIs/proxies: $0. Existing VM: incremental compute can be $0 if spare capacity already
paid for; storage/network still apply. For budgeting only, assuming a VM rate of $0.05/hour gives
$36.50/month at 730 hours, plus disk, network and monitoring. This is an illustrative assumption,
not an Azure quote. Validate actual region/size on the official Azure calculator:
https://azure.microsoft.com/en-us/pricing/calculator/
https://azure.microsoft.com/en-us/pricing/details/virtual-machines/linux/
Twice-weekly jobs alone do not stop VM billing; VM deallocation must be separately arranged if desired.

Browser integration reference:
https://seleniumbase.io/examples/cdp_mode/ReadMe/
