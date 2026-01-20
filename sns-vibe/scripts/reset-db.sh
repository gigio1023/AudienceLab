#!/bin/bash

# SNS-Vibe DB Reset & Seed Script
# Usage: ./scripts/reset-db.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=== SNS-Vibe DB Reset ==="

# Remove existing database
if [ -f "sns.db" ]; then
    echo "Removing existing database..."
    rm sns.db
    echo "Database removed."
else
    echo "No existing database found."
fi

# Run seed script
echo "Seeding database..."
npx tsx src/lib/server/seed.ts

echo "=== DB Reset Complete ==="
echo "You can now start the dev server with: npm run dev"
