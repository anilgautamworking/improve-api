#!/bin/bash
# Script to prepare code for GitHub push
# Run this before pushing to ensure everything is ready

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}📦 Preparing Deployment for GitHub${NC}"
echo "=========================================="

# Get project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$PROJECT_ROOT"

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo -e "${RED}❌ Not a git repository${NC}"
    exit 1
fi

# Check current branch
CURRENT_BRANCH=$(git branch --show-current)
echo -e "${BLUE}Current branch: ${CURRENT_BRANCH}${NC}"

# Check for uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}⚠️  You have uncommitted changes:${NC}"
    git status --short
    echo ""
    read -p "Do you want to commit these changes? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Staging all changes...${NC}"
        git add .
        echo -e "${BLUE}Enter commit message (or press Enter for default):${NC}"
        read -r COMMIT_MSG
        if [ -z "$COMMIT_MSG" ]; then
            COMMIT_MSG="Deploy: Update admin features, migrations, and Prefect setup"
        fi
        git commit -m "$COMMIT_MSG"
        echo -e "${GREEN}✓ Changes committed${NC}"
    else
        echo -e "${YELLOW}Skipping commit...${NC}"
    fi
fi

# Check if migrations are up to date
echo -e "${BLUE}Checking migrations...${NC}"
if [ -f "alembic.ini" ]; then
    LATEST_MIGRATION=$(ls -t alembic/versions/*.py 2>/dev/null | head -1 | xargs basename | cut -d'_' -f1)
    echo -e "${GREEN}✓ Latest migration: ${LATEST_MIGRATION}${NC}"
else
    echo -e "${YELLOW}⚠️  No alembic.ini found${NC}"
fi

# Check for .env file (should not be committed)
if [ -f ".env" ]; then
    if git ls-files --error-unmatch .env >/dev/null 2>&1; then
        echo -e "${RED}⚠️  WARNING: .env file is tracked in git!${NC}"
        echo "Consider adding .env to .gitignore"
    fi
fi

# Show what will be pushed
echo ""
echo -e "${BLUE}Files ready to push:${NC}"
git status --short

# Show remote info
REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "No remote")
echo ""
echo -e "${BLUE}Remote: ${REMOTE_URL}${NC}"

# Ask for confirmation
echo ""
read -p "Ready to push to GitHub? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}Pushing to GitHub...${NC}"
    git push origin "$CURRENT_BRANCH"
    echo ""
    echo -e "${GREEN}✅ Code pushed to GitHub successfully!${NC}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. SSH into your server"
    echo "2. Run: ./scripts/server_deploy.sh"
    echo "   OR follow the manual steps in DEPLOYMENT_GUIDE.md"
else
    echo -e "${YELLOW}Push cancelled${NC}"
fi

