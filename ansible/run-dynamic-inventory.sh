#!/bin/bash
# Helper script for running Ansible with dynamic inventory

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INVENTORY_DIR="${SCRIPT_DIR}/inventory"
PLAYBOOKS_DIR="${SCRIPT_DIR}/playbooks"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

usage() {
    cat << EOF
Usage: $0 [command] [options]

Commands:
    list            List all discovered instances
    graph           Show instance hierarchy
    ping            Test connectivity to all instances
    playbook        Run a playbook against dynamic inventory
    update-cache    Force refresh of inventory cache

Options:
    -e, --env       Limit to specific environment (dev, prod)
    -r, --role      Limit to specific role (AttackBox, Guacamole)
    -p, --playbook  Playbook name (for playbook command)
    -t, --tags      Run specific playbook tags
    --check         Run in check mode (dry-run)

Examples:
    $0 list
    $0 graph
    $0 ping --env dev
    $0 playbook --playbook attackbox.yml
    $0 playbook --playbook attackbox.yml --env dev --check
    $0 playbook --playbook attackbox.yml --tags tools,vnc

EOF
    exit 1
}

# Parse arguments
COMMAND=""
ENV=""
ROLE=""
PLAYBOOK=""
TAGS=""
CHECK_MODE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        list|graph|ping|playbook|update-cache)
            COMMAND="$1"
            shift
            ;;
        -e|--env)
            ENV="$2"
            shift 2
            ;;
        -r|--role)
            ROLE="$2"
            shift 2
            ;;
        -p|--playbook)
            PLAYBOOK="$2"
            shift 2
            ;;
        -t|--tags)
            TAGS="$2"
            shift 2
            ;;
        --check)
            CHECK_MODE="--check"
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            ;;
    esac
done

# Validate command
if [ -z "$COMMAND" ]; then
    echo -e "${RED}Error: No command specified${NC}"
    usage
fi

# Build limit string
LIMIT=""
if [ -n "$ENV" ]; then
    LIMIT="env_${ENV}"
fi
if [ -n "$ROLE" ]; then
    if [ -n "$LIMIT" ]; then
        LIMIT="${LIMIT}:&role_${ROLE}"
    else
        LIMIT="role_${ROLE}"
    fi
fi

# Execute command
case $COMMAND in
    list)
        echo -e "${GREEN}Listing all discovered instances...${NC}"
        ansible-inventory -i "${INVENTORY_DIR}/aws_ec2.yml" --list
        ;;
    
    graph)
        echo -e "${GREEN}Showing instance hierarchy...${NC}"
        ansible-inventory -i "${INVENTORY_DIR}/aws_ec2.yml" --graph
        ;;
    
    ping)
        echo -e "${GREEN}Testing connectivity...${NC}"
        if [ -n "$LIMIT" ]; then
            ansible all -i "${INVENTORY_DIR}/aws_ec2.yml" -m ping --limit "$LIMIT"
        else
            ansible all -i "${INVENTORY_DIR}/aws_ec2.yml" -m ping
        fi
        ;;
    
    playbook)
        if [ -z "$PLAYBOOK" ]; then
            echo -e "${RED}Error: --playbook option required${NC}"
            usage
        fi
        
        PLAYBOOK_PATH="${PLAYBOOKS_DIR}/${PLAYBOOK}"
        if [ ! -f "$PLAYBOOK_PATH" ]; then
            echo -e "${RED}Error: Playbook not found: ${PLAYBOOK_PATH}${NC}"
            exit 1
        fi
        
        CMD="ansible-playbook -i ${INVENTORY_DIR}/aws_ec2.yml ${PLAYBOOK_PATH}"
        
        if [ -n "$LIMIT" ]; then
            CMD="${CMD} --limit ${LIMIT}"
        fi
        
        if [ -n "$TAGS" ]; then
            CMD="${CMD} --tags ${TAGS}"
        fi
        
        if [ -n "$CHECK_MODE" ]; then
            CMD="${CMD} ${CHECK_MODE}"
            echo -e "${YELLOW}Running in CHECK MODE (dry-run)${NC}"
        fi
        
        echo -e "${GREEN}Running playbook: ${PLAYBOOK}${NC}"
        echo -e "${YELLOW}Command: ${CMD}${NC}"
        eval "$CMD"
        ;;
    
    update-cache)
        echo -e "${GREEN}Clearing inventory cache...${NC}"
        rm -f /tmp/ansible-aws-ec2-cache*
        echo -e "${GREEN}Cache cleared. Next inventory query will refresh.${NC}"
        ;;
esac
