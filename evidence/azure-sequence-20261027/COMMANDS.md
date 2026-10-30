# Sanitized Azure test commands

The temporary VM setup used these Azure CLI command forms. Account, resource, network and SSH
values are redacted:

```text
az group create --name <redacted> --location <westus2-or-eastus2>
az vm create --resource-group <redacted> --name <redacted> --image Ubuntu2404 --size <reviewed-size> --admin-username <redacted> --ssh-key-values <redacted>
az network nsg rule create --resource-group <redacted> --nsg-name <redacted> --name <redacted> --priority <redacted> --source-address-prefixes <redacted> --destination-port-ranges 22 --access Allow --protocol Tcp
az vm auto-shutdown --resource-group <redacted> --name <redacted> --time <redacted>
```

The repository installer and reviewed diagnostic commands on each VM were:

```text
sudo bash deploy/install-ubuntu.sh
.venv/bin/python -m tools.run_azure_sequence --output <private-output-directory>
.venv/bin/python -m tools.run_azure_sequence --output <private-output-directory> --skip-listing
```

The test code fixed the limits at four product requests, one listing request, 600 seconds and
128 MiB of captured response bodies. The actual two listing sequences stopped after one control
product and one blocked listing. The later fresh West US 2 session stopped during store selection
and made no product or listing requests.

The cleanup sequence recorded by Azure CLI was:

```text
az vm deallocate --resource-group <redacted> --name <redacted>
az group delete --name <redacted> --yes --no-wait
az group wait --name <redacted> --deleted --interval <redacted> --timeout <redacted>
az group exists --name <redacted>
```

The local Azure CLI logs recorded exit code 0 for all four commands. Resource names, account
details, IP addresses, SSH settings and credentials are intentionally omitted.

On 30 October, a new read-only Azure check could not run because the existing login was blocked
by the account's current security policy. This does not change the 27 October cleanup receipt,
but it means the zero-resource state was not independently refreshed on 30 October.
