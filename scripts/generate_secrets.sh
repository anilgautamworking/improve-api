#!/bin/bash
# Generate strong secrets for .env file

echo "Generating strong secrets..."
echo ""

DASHBOARD_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
JWT_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')

echo "Add these to your .env file:"
echo ""
echo "DASHBOARD_SECRET_KEY=${DASHBOARD_SECRET}"
echo "JWT_SECRET=${JWT_SECRET}"
echo ""

