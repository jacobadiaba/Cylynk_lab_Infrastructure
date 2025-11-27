#!/bin/bash
# Wrapper script to run Ansible playbook with correct paths
# This handles the OneDrive world-writable directory issue

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Use absolute paths to avoid OneDrive world-writable issues
export ANSIBLE_CONFIG="$SCRIPT_DIR/ansible.cfg"
export ANSIBLE_ROLES_PATH="$SCRIPT_DIR/roles"
export ANSIBLE_INVENTORY="$SCRIPT_DIR/inventory/hosts.yml"

# Run the playbook
ansible-playbook \
  -i "$ANSIBLE_INVENTORY" \
  playbooks/attackbox.yml \
  "$@"

