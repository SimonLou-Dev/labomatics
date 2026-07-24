#!/bin/bash
# Cloud-init Proxmox-compatible pour VM Alpine - labomatics
# Minimale: juste installer les basics, le reste se fait via SSH

set -e

echo "labomatics cloud-init starting..."

# Mettre à jour les packages
apk update
apk add --no-cache curl openssh-client openssh-server bash

# Démarrer SSH
rc-update add sshd default
rc-service sshd start

# Marquer comme provisionné
touch /etc/labomatics-cloudinit-done

echo "labomatics cloud-init complete"
