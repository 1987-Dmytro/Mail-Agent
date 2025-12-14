#!/bin/bash
#
# Upload secrets to GitHub repository
# Requires GitHub CLI (gh) to be installed and authenticated
#

set -e

SECRETS_FILE=".env.secrets"
REPO="1987-Dmytro/Mail-Agent"

echo "=================================================="
echo "  GitHub Secrets Uploader"
echo "=================================================="
echo ""

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) is not installed!"
    echo ""
    echo "Install it:"
    echo "  macOS:   brew install gh"
    echo "  Linux:   curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg"
    echo "  Windows: winget install --id GitHub.cli"
    echo ""
    echo "Then authenticate:"
    echo "  gh auth login"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ Not authenticated with GitHub!"
    echo ""
    echo "Run: gh auth login"
    exit 1
fi

# Check if secrets file exists
if [ ! -f "$SECRETS_FILE" ]; then
    echo "❌ Secrets file not found: $SECRETS_FILE"
    echo ""
    echo "Generate it first:"
    echo "  bash scripts/generate-secrets.sh"
    exit 1
fi

echo "📁 Loading secrets from: $SECRETS_FILE"
echo ""

# Source the secrets file
source "$SECRETS_FILE"

# Function to upload secret
upload_secret() {
    local name=$1
    local value=$2

    if [ -z "$value" ]; then
        echo "⚠️  Skipping $name (empty value)"
        return
    fi

    echo "📤 Uploading: $name"
    echo "$value" | gh secret set "$name" --repo "$REPO"
}

echo "Uploading secrets to GitHub repository: $REPO"
echo ""

# Upload all secrets
upload_secret "STAGING_VM_IP" "$STAGING_VM_IP"
upload_secret "PRODUCTION_VM_IP" "$PRODUCTION_VM_IP"
upload_secret "ORACLE_SSH_PRIVATE_KEY" "$ORACLE_SSH_PRIVATE_KEY"
upload_secret "STAGING_DATABASE_URL" "$STAGING_DATABASE_URL"
upload_secret "PRODUCTION_DATABASE_URL" "$PRODUCTION_DATABASE_URL"
upload_secret "JWT_SECRET_KEY" "$JWT_SECRET_KEY"
upload_secret "ENCRYPTION_KEY" "$ENCRYPTION_KEY"
upload_secret "GMAIL_CLIENT_ID" "$GMAIL_CLIENT_ID"
upload_secret "GMAIL_CLIENT_SECRET" "$GMAIL_CLIENT_SECRET"
upload_secret "GEMINI_API_KEY" "$GEMINI_API_KEY"
upload_secret "GROQ_API_KEY" "$GROQ_API_KEY"
upload_secret "STAGING_API_URL" "$STAGING_API_URL"
upload_secret "PRODUCTION_API_URL" "$PRODUCTION_API_URL"

echo ""
echo "=================================================="
echo "  ✅ Secrets Upload Complete!"
echo "=================================================="
echo ""
echo "Verify secrets on GitHub:"
echo "  https://github.com/$REPO/settings/secrets/actions"
echo ""
echo "⚠️  Remember to delete $SECRETS_FILE after upload:"
echo "  rm $SECRETS_FILE"
echo ""
