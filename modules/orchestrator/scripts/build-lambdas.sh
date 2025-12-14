#!/bin/bash
# Build Lambda deployment packages for the orchestrator module

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_DIR="$(dirname "$SCRIPT_DIR")"
LAMBDA_DIR="$MODULE_DIR/lambda"
PACKAGES_DIR="$LAMBDA_DIR/packages"
LAYERS_DIR="$LAMBDA_DIR/layers"

echo "Building Lambda packages..."
echo "Module directory: $MODULE_DIR"

# Create output directories
mkdir -p "$PACKAGES_DIR"
mkdir -p "$LAYERS_DIR"

# Build common layer
echo "Building common layer..."
LAYER_BUILD_DIR=$(mktemp -d)
mkdir -p "$LAYER_BUILD_DIR/python"
cp "$LAMBDA_DIR/common/"*.py "$LAYER_BUILD_DIR/python/"

# Install dependencies if requirements.txt exists
if [ -f "$LAMBDA_DIR/common/requirements.txt" ]; then
    pip install -r "$LAMBDA_DIR/common/requirements.txt" -t "$LAYER_BUILD_DIR/python/" --quiet
fi

cd "$LAYER_BUILD_DIR"
zip -r "$LAYERS_DIR/common.zip" python/ -x "*.pyc" -x "__pycache__/*"
rm -rf "$LAYER_BUILD_DIR"
echo "Created: $LAYERS_DIR/common.zip"

# Build individual Lambda packages
FUNCTIONS=("create-session" "get-session-status" "terminate-session" "pool-manager" "get-usage" "usage-history" "admin-sessions")

for func in "${FUNCTIONS[@]}"; do
    echo "Building $func..."
    FUNC_DIR="$LAMBDA_DIR/$func"
    
    if [ -d "$FUNC_DIR" ] && [ -f "$FUNC_DIR/index.py" ]; then
        BUILD_DIR=$(mktemp -d)
        cp "$FUNC_DIR/"*.py "$BUILD_DIR/"
        
        # Install function-specific dependencies if any
        if [ -f "$FUNC_DIR/requirements.txt" ]; then
            pip install -r "$FUNC_DIR/requirements.txt" -t "$BUILD_DIR/" --quiet
        fi
        
        cd "$BUILD_DIR"
        zip -r "$PACKAGES_DIR/$func.zip" . -x "*.pyc" -x "__pycache__/*"
        rm -rf "$BUILD_DIR"
        echo "Created: $PACKAGES_DIR/$func.zip"
    else
        echo "Warning: $FUNC_DIR/index.py not found, skipping..."
    fi
done

echo ""
echo "Build complete! Packages created:"
ls -la "$PACKAGES_DIR/"
ls -la "$LAYERS_DIR/"

