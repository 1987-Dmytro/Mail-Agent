#!/bin/bash
#
# Generate random secrets for Mail Agent
# Creates a .env.secrets file with generated values
#

set -e

echo "=================================================="
echo "  Mail Agent - Secrets Generator"
echo "=================================================="
echo ""

SECRETS_FILE=".env.secrets"

# Generate random secrets
JWT_SECRET=$(openssl rand -base64 32)
ENCRYPTION_KEY=$(openssl rand -base64 32)

# Create secrets file
cat > "$SECRETS_FILE" << EOF
# Generated secrets for Mail Agent
# Generated at: $(date)
#
# ⚠️  IMPORTANT: DO NOT COMMIT THIS FILE!
# Add this file to .gitignore immediately!

# Application Secrets (auto-generated)
JWT_SECRET_KEY=$JWT_SECRET
ENCRYPTION_KEY=$ENCRYPTION_KEY

# ==============================================
# FILL IN THE VALUES BELOW MANUALLY:
# ==============================================

# Oracle Cloud VMs (get from Oracle Console → Compute → Instances)
STAGING_VM_IP=
PRODUCTION_VM_IP=

# Oracle SSH Private Key (your SSH private key content)
# To get it: cat ~/.ssh/oracle_key
ORACLE_SSH_PRIVATE_KEY=

# Database URLs (get from Oracle Console → Autonomous Database → DB Connection)
# Format: postgresql://admin:password@host:1522/database_name
STAGING_DATABASE_URL=
PRODUCTION_DATABASE_URL=

# Gmail OAuth (get from Google Cloud Console → APIs & Services → Credentials)
GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=

# AI API Keys
GEMINI_API_KEY=
GROQ_API_KEY=

# Frontend URLs
STAGING_API_URL=http://\${STAGING_VM_IP}:8000
PRODUCTION_API_URL=http://\${PRODUCTION_VM_IP}:8000

# ==============================================
# After filling in all values, run:
# bash scripts/upload-secrets.sh
# ==============================================
EOF

echo "✅ Secrets generated!"
echo ""
echo "Generated secrets:"
echo "  - JWT_SECRET_KEY: ✓"
echo "  - ENCRYPTION_KEY: ✓"
echo ""
echo "📝 Created file: $SECRETS_FILE"
echo ""
echo "Next steps:"
echo "  1. Add to .gitignore:"
echo "     echo '.env.secrets' >> .gitignore"
echo ""
echo "  2. Fill in remaining values in $SECRETS_FILE:"
echo "     vim $SECRETS_FILE"
echo ""
echo "  3. Upload to GitHub:"
echo "     bash scripts/upload-secrets.sh"
echo ""

# Add to .gitignore if not already there
if ! grep -q ".env.secrets" .gitignore 2>/dev/null; then
    echo ".env.secrets" >> .gitignore
    echo "✅ Added .env.secrets to .gitignore"
fi
