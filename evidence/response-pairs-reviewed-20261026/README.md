# Wrong-store / corrected-response pairs — ready for client review

Prepared from four complete, privately retained browser-Fetch response bodies. No new live request.
This folder supersedes the earlier “privacy review pending” status for these sharing copies only.
Nothing sent to the client. Client verification/acceptance is not claimed. No store-drift cure proven.

Agreed demonstration: Bentonville #100,406 S Walton Blvd,AR72712,PICKUP.

| Product | Sequence | Returned context | Current price | Capture source commit |
|---|---|---|---|---|
|14898365,Clorox wipes|94 →95|3520/07030/SHIPPING →100/72712/PICKUP|12.78 →12.78 USD|6f9284bfb698acfac62bc48106bb96bac37aa530|
|51237368,Clorox ToiletWand refills|72 →73|3081/95829/SHIPPING →100/72712/PICKUP|7.94 →7.57 USD|2a32583283d5a14a57f29857e17836c344bf6044|

Each pair is one wrong response followed by one identical-URL/settings diagnostic re-fetch in the
same browser session. Sequence numbers refer to saved request order within that separate run,
not a single shared sequence across both runs. Existing run was stopped/invalidated; corrected
responses did not rehabilitate its output. Cache-status was Miss for all four responses. These
examples do not show that retries prevent future errors; first pair shows unchanged price alone
cannot establish correct store context.

## Files

- `reviewed-pairs.json`: both pairs, exact capture source commits/module hashes, original private
  paths/hashes/lengths, redacted-file paths/hashes, preserved fields and safe request/response metadata.
- `controlled-500-20261025-wrong.redacted.html` / `controlled-500-20261025-refetch.redacted.html`.
- `controlled-500-continuation-20261025-wrong.redacted.html` / `controlled-500-continuation-20261025-refetch.redacted.html`.
- `offline-privacy-checks.json`: separate synthetic privacy tests, no retailer requests.
- `privacy-review.json`: review scope/results and limits.
- `SHA256SUMS.json`: sharing-file integrity manifest.

## What these copies contain

Original product identity/name/UPC/seller, full priceInfo already present in published pair metadata,
store/ZIP/city/state/intent and selected fulfillment/availability/quantity fields. All copied values
are compared directly with original response JSON. Request metadata retains method/cache/default
credentials policy/redirect/timeout/attempt number, redacted URL, timestamps, response status and
allowlisted response headers. “Credentials: same-origin” describes browser policy, not credentials.
Browser-managed request header/cookie values were never recorded and cannot be supplied.

All HTML attributes, unrelated visible text, other script contents and nonallowlisted JSON are
removed/replaced with [redacted]. Address identifiers/access-point identifiers, customer/session/
tracking data, script URLs, embedded configuration and page links are excluded. Redacted HTML is
reserialized, so bytes/length/hash differ from original. These are explicitly redacted response
copies, not untouched raw originals or compressed/TLS wire captures. No product value reconstructed.
Full original decoded bodies remain local, with hashes recorded here; they are not included in this
public folder. Independent verification of every omitted byte would require controlled private
access to originals. Client has not reviewed or accepted these copies yet.

To read preserved fields, open as text or parse the retained __NEXT_DATA__ JSON. Browser rendering
is unnecessary: external resources/actions/attributes and scripts have been removed or redacted.

## Reproduce offline with private captures available

```sh
python prepare_response_pairs.py
```

Requires original ignored data/controlled-500-20261025 and data/controlled-500-continuation-20261025
folders plus their existing public metadata. Verifies source commits/module hashes from Git, four
original-body hashes/lengths, same product, consecutive pair order and identical request settings.
Public checkout alone can inspect/hash sharing files; it cannot regenerate private originals.
