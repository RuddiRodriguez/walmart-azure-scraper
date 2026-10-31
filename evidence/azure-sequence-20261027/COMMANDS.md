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
git checkout 9101c818a5c6f1c498cea5574dd428787b8b4420
.venv/bin/python -m tools.run_azure_sequence --output <private-output-directory>

git checkout 8f9a5c6e4933afb9f5c6986e3f604fd12e73e855
.venv/bin/python -m tools.run_azure_sequence --output <private-output-directory>
.venv/bin/python -m tools.run_azure_sequence --output <private-output-directory> --skip-listing
```

Exact source snapshots are included at:

```text
evidence/azure-sequence-20261027/source/run_azure_sequence-westus2-9101c81.py
evidence/azure-sequence-20261027/source/run_azure_sequence-eastus2-8f9a5c6.py
```

Their SHA-256 hashes are:

```text
bddab4fe91f7e749f07838e8bc4ce5ab1849aa36201b7165a1adc5bc9f678642  west-us-2 source
7f3f97327b82d48e98bd5278cf054f98ce80513d6bd9f76abd2367126cc4209a  east-us-2 source
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

On 31 October, fresh read-only checks for both groups could not run because the existing login
was blocked by the account's current security policy. The redacted result is in
`RESOURCE_GROUP_CHECK.json`. It does not prove either group is absent.
