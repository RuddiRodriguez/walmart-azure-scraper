# Proposed Azure diagnostic — not yet approved or executed

## Purpose and fixed source

This is one three-product Store 100 / ZIP 72712 / PICKUP interruption-and-resume diagnostic. It does not publish production output.

- Repository: https://github.com/RuddiRodriguez/walmart-azure-scraper
- Source commit: `f251aa0fbd8c2a3b9f3ba889a3f3780f19a6865b`
- Review tag: `review-20261027-evidence-correction`
- Plan: `evidence/step8-controlled-recovery-20261026/plan.json`
- Product/listing request ceiling: 12 product + 2 listing requests = 14 total.
- Collection deadline: 600 seconds shared by the first process and resumed process. Restart does not reset the recorded start time or counters.
- Saved response-body ceiling: 256 MiB for this proposed run.

No Azure access or spending is approved by this document.

## Smallest environment

- One temporary resource group: `rg-walmart-ruddi-diagnostic`
- Region: `centralus`
- One pay-as-you-go VM: `Standard_B2ls_v2` — 2 vCPU, 4 GiB RAM
- Image: `Canonical:ubuntu-24_04-lts:server:latest` — Ubuntu Server 24.04 LTS x64 Gen2
- OS disk: 32 GiB Standard SSD LRS, no data disk
- One Standard static public IPv4 address
- One inbound rule: TCP 22 from Ruddi's current public IPv4 `/32` only
- No paid proxy, scraping API, database, load balancer or monitoring workspace
- Maximum resource lifetime: 60 minutes from VM creation. Auto-shutdown at 55 minutes; whole resource group deleted by 60 minutes.

The client creates and owns the temporary resource group. Ruddi needs no Azure RBAC role. Access is only SSH to the temporary VM. This is the minimum access arrangement. The client deletes the resource group after evidence export.

Dedicated public SSH key:

```text
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMMpeXcCaQrZS79H6PQseEMi781jYetRv6Dqzn1m0bc/ ruddi-walmart-azure-diagnostic-2026
```

Fingerprint:

```text
SHA256:RAe/daw64+LDj2ofTOqz+GMxuFkzHPMaJJ78TM+8pAc
```

## Client-side creation commands

Run after approval. Replace `RUDDI_PUBLIC_IP` with the current IPv4 address before creation.

```bash
set -euo pipefail

RG=rg-walmart-ruddi-diagnostic
REGION=centralus
VM=walmart-ruddi-diag-01
ADMIN=ruddi
RUDDI_PUBLIC_IP=REPLACE_WITH_APPROVED_IPV4
IMAGE=Canonical:ubuntu-24_04-lts:server:latest
SIZE=Standard_B2ls_v2
SSH_KEY='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMMpeXcCaQrZS79H6PQseEMi781jYetRv6Dqzn1m0bc/ ruddi-walmart-azure-diagnostic-2026'

az group create --name "$RG" --location "$REGION"

az vm list-skus --location "$REGION" --size "$SIZE" --all \
  --query "[?name=='$SIZE' && restrictions==null].name" --output tsv | grep -qx "$SIZE"

az vm image show --location "$REGION" --urn "$IMAGE" --query name --output tsv

az vm create \
  --resource-group "$RG" \
  --name "$VM" \
  --location "$REGION" \
  --size "$SIZE" \
  --image "$IMAGE" \
  --security-type Standard \
  --admin-username "$ADMIN" \
  --ssh-key-values "$SSH_KEY" \
  --os-disk-size-gb 32 \
  --storage-sku StandardSSD_LRS \
  --public-ip-sku Standard \
  --nsg-rule NONE

NIC_ID=$(az vm show --resource-group "$RG" --name "$VM" \
  --query 'networkProfile.networkInterfaces[0].id' --output tsv)
NSG_ID=$(az network nic show --ids "$NIC_ID" \
  --query 'networkSecurityGroup.id' --output tsv)

az network nsg rule create \
  --resource-group "$RG" \
  --nsg-name "${NSG_ID##*/}" \
  --name allow-ruddi-ssh \
  --priority 100 \
  --access Allow \
  --protocol Tcp \
  --direction Inbound \
  --source-address-prefixes "$RUDDI_PUBLIC_IP/32" \
  --destination-port-ranges 22

SHUTDOWN_UTC=$(date -u -d '+55 minutes' +%H%M)
az vm auto-shutdown --resource-group "$RG" --name "$VM" --time "$SHUTDOWN_UTC"

az vm show --show-details --resource-group "$RG" --name "$VM" \
  --query '{publicIp:publicIps,powerState:powerState}' --output json
```

If the requested SKU or image is unavailable, stop. Do not silently substitute another VM, image or region.

## Installation commands on the VM

```bash
set -euo pipefail

sudo install -d -o "$USER" -g "$USER" /opt/walmart-scraper
git clone https://github.com/RuddiRodriguez/walmart-azure-scraper.git /opt/walmart-scraper
cd /opt/walmart-scraper
git checkout --detach f251aa0fbd8c2a3b9f3ba889a3f3780f19a6865b
test "$(git rev-parse HEAD)" = 'f251aa0fbd8c2a3b9f3ba889a3f3780f19a6865b'
sudo ./deploy/install-ubuntu.sh
```

Installation downloads Ubuntu packages, Chrome and Python packages. No browser is opened during installation.

## Diagnostic command

The runner starts the collector, sends SIGKILL after one committed product while the next product is being processed, then resumes the same checkpoint automatically.

```bash
set -euo pipefail
cd /opt/walmart-scraper

RUN="data/azure-diagnostic-$(date -u +%Y%m%dT%H%M%SZ)"
printf '%s\n' "$RUN" > /tmp/walmart-diagnostic-run-path

timeout --signal=TERM 620s xvfb-run -a \
  .venv/bin/python run_controlled_recovery.py \
  --output "$RUN" \
  --plan evidence/step8-controlled-recovery-20261026/plan.json
```

The 620-second shell guard allows up to 20 seconds for process termination and final file writes. Network collection remains limited by the plan's original shared 600-second deadline. The plan separately caps 12 product requests and 2 listing requests, so their combined maximum is 14 across the interruption and restart.

## Stop conditions

Stop without publishing if any of these occurs:

- Store, ZIP, PICKUP intent or product identity does not match.
- HTTP 401, 403, 412 or 429, CAPTCHA or access challenge.
- Combined 14 product/listing requests reached.
- Shared 600-second collection deadline reached.
- Saved response bodies exceed 256 MiB.
- Free disk falls below 8 GiB.
- Source commit, plan or checkpoint signature changes.
- Required hashes fail after export.
- Resource lifetime or estimated $1 allowance could be exceeded.

Rejected local-price data never enters output. Existing last-good data is not replaced. Eligible unavailable products remain represented with empty current values and dated history.

## Privacy-reviewed export and hash check

Raw response bodies stay private on the temporary VM. Export only the report, products, events and redacted request/response metadata. Do not export cookies, browser profiles, raw HTML or `.body` files.

```bash
set -euo pipefail
cd /opt/walmart-scraper
RUN=$(cat /tmp/walmart-diagnostic-run-path)
EXPORT="$RUN/reviewed-export"
mkdir -p "$EXPORT/captures"

cp "$RUN/recovery-result.json" "$EXPORT/"
cp "$RUN/interrupted-checkpoint.json" "$EXPORT/"
cp "$RUN/collection/report.json" "$EXPORT/"
cp "$RUN/collection/products.json" "$EXPORT/"
cp "$RUN/collection/events.jsonl" "$EXPORT/"
cp "$RUN/collection/selected-store.json" "$EXPORT/"
cp evidence/step8-controlled-recovery-20261026/plan.json "$EXPORT/plan.json"
find "$RUN/collection/captures" -maxdepth 1 -type f -name '*.json' \
  -exec cp {} "$EXPORT/captures/" \;

find "$EXPORT" -type f ! -name SHA256SUMS.txt -print0 \
  | sort -z | xargs -0 sha256sum > "$EXPORT/SHA256SUMS.txt"

(cd "$EXPORT" && sha256sum --check SHA256SUMS.txt)
tar -C "$RUN" -czf "$RUN/azure-diagnostic-reviewed.tar.gz" reviewed-export
sha256sum "$RUN/azure-diagnostic-reviewed.tar.gz" \
  > "$RUN/azure-diagnostic-reviewed.tar.gz.sha256"
du -h "$RUN/azure-diagnostic-reviewed.tar.gz"
```

Download both archive and hash file, then verify locally:

```bash
sha256sum --check azure-diagnostic-reviewed.tar.gz.sha256
tar -xzf azure-diagnostic-reviewed.tar.gz
(cd reviewed-export && sha256sum --check SHA256SUMS.txt)
```

If either check fails, do not use the export. Repeat export once from the same VM. If it fails again, mark the diagnostic failed and delete the resource group.

## Cleanup

After verified export, or immediately after any failure:

```bash
RG=rg-walmart-ruddi-diagnostic
az vm deallocate --resource-group "$RG" --name walmart-ruddi-diag-01
az group delete --name "$RG" --yes --no-wait
```

The client confirms deletion:

```bash
az group exists --name rg-walmart-ruddi-diagnostic
```

Expected final value: `false`. VM, disk, network interface, network security group and public IP are all inside the same temporary resource group, so group deletion removes them together.

## Cost boundary

Public Azure retail prices checked on 27 October 2026 for Central US:

- `Standard_B2ls_v2` Linux VM: $0.047/hour.
- 32 GiB E4 Standard SSD: $2.40/month plus $0.32/month mount charge, prorated hourly.
- Standard static IPv4: $0.005/hour.

At the 60-minute maximum, VM, disk and IP are about $0.056 before network transfer. Setup downloads and browser page/assets are inbound to Azure. Reviewed export is capped below 300 MiB. Even using a conservative $0.10/GB outbound allowance, total remains below $0.10. The test stops rather than adding services or exceeding $1.

Price source:

https://prices.azure.com/api/retail/prices

VM specification:

https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/general-purpose/bsv2-series

Ubuntu image reference:

https://learn.microsoft.com/en-us/azure/virtual-machines/linux/quick-create-cli
