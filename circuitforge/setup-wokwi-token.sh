#!/bin/bash

# CircuitForge - Wokwi CLI Token Setup
# This script helps you set up Wokwi CLI authentication

echo "🔧 CircuitForge - Wokwi CLI Token Setup"
echo "========================================"
echo ""

# Check if wokwi-cli is installed
if ! command -v wokwi-cli &> /dev/null; then
    if [ -f "$HOME/bin/wokwi-cli" ]; then
        echo "✅ Found wokwi-cli at $HOME/bin/wokwi-cli"
    else
        echo "❌ Wokwi CLI not found"
        echo ""
        echo "Install Wokwi CLI first:"
        echo "Visit: https://docs.wokwi.com/wokwi-ci/getting-started"
        exit 1
    fi
else
    echo "✅ Wokwi CLI is installed"
fi

echo ""
echo "📝 Steps to get your token:"
echo "1. Open: https://wokwi.com/dashboard/ci"
echo "2. Sign in to your Wokwi account"
echo "3. Copy your CLI token"
echo ""

# Check if token is already set
if [ -n "$WOKWI_CLI_TOKEN" ]; then
    echo "✅ WOKWI_CLI_TOKEN is already set in your current session"
    echo "   Current value: ${WOKWI_CLI_TOKEN:0:10}..."
    echo ""
    read -p "Do you want to update it? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Keeping existing token."
        exit 0
    fi
fi

# Prompt for token
echo "Paste your Wokwi CLI token:"
read -s WOKWI_TOKEN
echo ""

if [ -z "$WOKWI_TOKEN" ]; then
    echo "❌ No token provided"
    exit 1
fi

echo "Token received!"
echo ""

# Decide where to save
echo "Where do you want to save the token?"
echo "1) Current session only (temporary)"
echo "2) ~/.zshrc (persist for all sessions)"
echo "3) .env file in this project"
echo ""
read -p "Choose (1-3): " choice

case $choice in
    1)
        export WOKWI_CLI_TOKEN="$WOKWI_TOKEN"
        echo "✅ Token set for current session"
        echo "   Run: export WOKWI_CLI_TOKEN='your-token'"
        echo "   Then restart the backend: cd apps/backend && python3 main.py"
        ;;
    2)
        echo "" >> ~/.zshrc
        echo "# Wokwi CLI Token (added by CircuitForge)" >> ~/.zshrc
        echo "export WOKWI_CLI_TOKEN='$WOKWI_TOKEN'" >> ~/.zshrc
        echo "✅ Token added to ~/.zshrc"
        echo "   Run: source ~/.zshrc"
        echo "   Then restart the backend"
        ;;
    3)
        echo "WOKWI_CLI_TOKEN=$WOKWI_TOKEN" >> .env
        echo "✅ Token added to .env file"
        echo "   Make sure to load it: set -a && source .env && set +a"
        echo "   Then restart the backend"
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Restart your backend server"
echo "2. Try simulation again"
echo ""
echo "For more info: https://docs.wokwi.com/wokwi-ci/getting-started"
