#!/usr/bin/env bash
# deploy.sh - upload the website to S3 and refresh CloudFront.
# Usage:
#   ./tools/deploy.sh dryrun   # show what would change, change nothing
#   ./tools/deploy.sh deploy   # upload changes and clear the CloudFront cache
set -euo pipefail

PROFILE="project5"
BUCKET="csce412-prra2413-site"
DIST_ID="E2XE8SGMTOFJIB"
SITE_DIR="website"
MODE="${1:-dryrun}"

if [ "$MODE" = "dryrun" ]; then
  echo "DRY RUN: changes that would be made to s3://$BUCKET"
  aws s3 sync "$SITE_DIR/" "s3://$BUCKET" --delete --dryrun --profile "$PROFILE"
  exit 0
fi

if [ "$MODE" = "deploy" ]; then
  echo "Uploading $SITE_DIR/ to s3://$BUCKET"
  aws s3 sync "$SITE_DIR/" "s3://$BUCKET" --delete --profile "$PROFILE"

  echo "Clearing the CloudFront cache"
  aws cloudfront create-invalidation \
    --distribution-id "$DIST_ID" \
    --paths "/*" \
    --profile "$PROFILE" \
    --query "Invalidation.{Id:Id,Status:Status}" \
    --output json
  exit 0
fi

echo "Unknown mode: $MODE (use dryrun or deploy)" >&2
exit 2
