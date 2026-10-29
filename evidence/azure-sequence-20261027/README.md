# Azure diagnostic evidence — 27 October 2026

Two small live diagnostics ran on fresh Ubuntu virtual machines in West US 2 and East US 2.
Chrome ran under a virtual display. Both tests used Bentonville Store 100, ZIP 72712 and PICKUP.

In both regions, control product `47428850` passed the product, store, ZIP, fulfillment and
price checks at `$3.97`. The next Art Sets listing navigation was redirected to Walmart's
`Robot or human?` page before any candidate product was reached.

A second fresh West US 2 browser session loaded the normal Walmart homepage but did not show
the required store banner. It stopped before making product requests.

These tests show that Azure access was not completely blocked, but changing region and IP did
not make collection reliable. They do not prove that Azure IP reputation alone caused the block.
No invalid data was published. Both Azure environments were deleted, and the cleanup check found
zero remaining resources.

The public [result](RESULT.json) contains reviewed metadata only. Raw pages, cookies, browser
sessions and credentials are not included.
