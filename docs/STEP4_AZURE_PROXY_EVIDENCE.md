# Step 4 — Azure and proxy evidence correction

## Requirement check

| Client request | Status | Evidence |
|---|---|---|
| Redacted output proving both Azure resource groups no longer exist | Blocked | The original cleanup and `group wait --deleted` commands exited successfully, but the original `group exists` stdout was not retained. Fresh read-only checks on 31 October were blocked by Azure login security defaults. See `evidence/azure-sequence-20261027/RESOURCE_GROUP_CHECK.json`. |
| Exact diagnostic source | Complete | Exact source snapshots are under `evidence/azure-sequence-20261027/source/`, with SHA-256 hashes in `COMMANDS.md`. |
| Correct command and source commit | Complete | West US 2 used `9101c818a5c6f1c498cea5574dd428787b8b4420`. East US 2 and the fresh-session option used `8f9a5c6e4933afb9f5c6986e3f604fd12e73e855`. Commands are in `COMMANDS.md`. |
| Provider usage evidence | Complete | `evidence/transport-correction-20261031/PROVIDER_USAGE.json` links the Oxylabs, Scrape.do and Bright Data usage results. |
| One cumulative paid-test limit | Complete as a proposal; not executed | `evidence/transport-correction-20261031/CUMULATIVE_LIMIT.json` covers all provider requests, browser assets, location checks, retries, traffic, runtime and cost. |
| Explain browser proxy, Web Unblocker and Web Scraper API | Complete | `docs/TRANSPORT_TYPES.md`. |
| No new Azure spending or deployment | Complete | Only two read-only Azure CLI checks were attempted. Both were blocked before returning resource state. No Azure resources were created or changed. |

## Remaining action

After Azure login is restored, run this read-only command once for each redacted group and save the literal output:

```text
az group exists --name <resource-group> --output tsv
```

Both outputs must be `false` before the deletion-proof requirement can be marked complete. No deployment is needed.
