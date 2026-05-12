#!/usr/bin/env bash
# Phase G optional hardening helpers for Hetzner VPS.
# Review each block before running — misconfiguration can lock SSH access.

set -euo pipefail

echo "== Queenswarm Phase G — security helpers =="
echo "This script only prints guidance; it does not mutate the system by default."
echo
echo "1) SSH keys only (disable password auth) — AFTER verifying key login:"
echo "   sudo sed -i 's/^#\\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config"
echo "   sudo sed -i 's/^#\\?ChallengeResponseAuthentication.*/ChallengeResponseAuthentication no/' /etc/ssh/sshd_config"
echo "   sudo systemctl restart ssh || sudo systemctl restart sshd"
echo
echo "2) fail2ban quick jail:"
echo "   sudo apt-get update && sudo apt-get install -y fail2ban"
echo "   printf '[DEFAULT]\\nbantime = 3600\\nmaxretry = 3\\n[sshd]\\nenabled = true\\n' | sudo tee /etc/fail2ban/jail.local"
echo "   sudo systemctl enable --now fail2ban"
echo
echo "3) UFW:"
echo "   sudo ufw allow 22/tcp && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp"
echo "   sudo ufw --force enable"
echo
echo "4) Daily DB backups — install /root/backup_db.sh separately (see repo docs)."
echo
echo "Done (no changes performed)."
