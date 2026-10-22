#!/usr/bin/env bash
set -euo pipefail
# Run on an existing Ubuntu x86_64 VM after copying source to /opt/walmart-scraper.
# Installs packages but does not start collection or enable the timer.
apt-get update
apt-get install -y python3-venv xvfb xauth wget ca-certificates fonts-liberation
if ! command -v google-chrome >/dev/null; then
  package=$(mktemp --suffix=.deb)
  wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb -O "$package"
  apt-get install -y "$package"
  rm "$package"
fi
id walmart >/dev/null 2>&1 || useradd --system --create-home --home-dir /var/lib/walmart-scraper --shell /usr/sbin/nologin walmart
cd /opt/walmart-scraper
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
install -d -o walmart -g walmart /var/lib/walmart-scraper/data
install -m 644 deploy/walmart-scraper@.service deploy/walmart-scraper@.timer /etc/systemd/system/
systemctl daemon-reload
printf '%s\n' 'Installed. Run a manual validation before enabling walmart-scraper@100.timer.'
