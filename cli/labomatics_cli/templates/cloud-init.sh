#!/bin/sh
# Alpine Linux Cloud-init script for labomatics

set -e

# Mark that cloud-init has run
touch /etc/labomatics-cloudinit-done

# Update system
apk update
apk upgrade

# Install base packages
apk add --no-cache \
  curl \
  bash \
  openssh \
  openssh-client \
  ca-certificates \
  docker \
  docker-cli-compose \
  python3 \
  py3-pip

# Start and enable SSH
rc-service sshd start
rc-update add sshd

# Start and enable Docker
rc-service docker start
rc-update add docker

# Create labomatics directory
mkdir -p /etc/labomatics

# Setup root SSH access
mkdir -p /root/.ssh
chmod 700 /root/.ssh

echo "Cloud-init completed successfully"
