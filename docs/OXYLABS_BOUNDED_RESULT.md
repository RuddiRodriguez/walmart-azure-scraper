# Oxylabs bounded result — 30 October 2026

We tested the smallest paid transport change without changing the collector's store checks.

- Residential proxy targeted US ZIP 72712.
- The provider location check reached Bentonville/72712.
- Spending was limited to $1 per day and the dashboard displayed $0.09 spent after the test.
- The first Walmart session stopped because the store banner did not load.
- One fresh proxy session retry stopped for the same reason.
- No listing or product response was accepted, and no production output was published.

The provider dashboard reported 14.38 MB and 55 total proxy requests. That includes browser assets and the location check, not 55 scraper product requests. The collector itself made zero listing captures and zero product/control captures because both attempts stopped during store selection.

This result does not support starting a paid full collection. Changing from the direct connection to this residential proxy did not solve the missing-store-context problem in the bounded test.

Privacy-safe evidence is in `evidence/oxylabs-bounded-20261030/RESULT.json`. Raw local reports remain private. Credentials are stored in the macOS Keychain and are not in Git or logs.
