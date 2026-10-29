# Azure test result

Two bounded Azure tests ran on 27 October 2026, one in West US 2 and one in East US 2.
Each used a fresh Ubuntu 24.04 virtual machine with Chrome under Xvfb.

The Store 100/PICKUP control product passed in both regions with the expected product ID,
ZIP 72712 and `$3.97` price. The immediately following Art Sets listing was redirected to
Walmart's `Robot or human?` page in both regions. A separate fresh West US 2 session loaded
the normal homepage but could not confirm the store banner, so it stopped before product requests.

The result shows that Azure access was not completely blocked, but changing region and IP did
not make the collection reliable. The cleaned candidate product was never reached. No invalid
data was published. Both Azure environments were deleted and zero Azure resources remained.

Reviewed public evidence: `evidence/azure-sequence-20261027/`.
