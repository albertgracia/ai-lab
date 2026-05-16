#!/bin/bash
# Pre-commit hook: block commit if Astro docs site doesn't build.
# Install:  ln -sf ../../scripts/pre-commit.sh .git/hooks/pre-commit

DOCS_DIR="apps/ialab-docs"

STAGED_DOCS=$(git diff --cached --name-only | grep "^${DOCS_DIR}/" | head -1)
if [ -z "$STAGED_DOCS" ]; then
    exit 0
fi

echo "🔨 Docs files changed → running astro build..."
cd "$DOCS_DIR" || exit 1
npm run build 2>&1
BUILD_EXIT=$?
cd - > /dev/null

if [ $BUILD_EXIT -ne 0 ]; then
    echo ""
    echo "❌ ASTRO BUILD FAILED — commit bloqueado."
    echo "   Corrige el error antes de hacer commit."
    echo "   (usa git commit --no-verify para saltar esta comprobación)"
    exit 1
fi

echo "✅ Astro build OK — commit permitido."
