#!/bin/bash
# Deploy stage
# Saves a copy of the release, uploads the site to S3, and clears the CloudFront cache.
set -e

SITE_BUCKET="csce412-prra2413-site"
RELEASE_BUCKET="csce412-prra2413-releases"
DISTRIBUTION="E2XE8SGMTOFJIB"
RELEASE=$(python3 -c "import json; print(json.load(open('website/version.json'))['release'])")

echo "Deploying release $RELEASE"

# save a copy of this release for rollback
aws s3 sync website/ s3://$RELEASE_BUCKET/releases/$RELEASE/ --delete

# upload the site
aws s3 sync website/ s3://$SITE_BUCKET/ --delete

# clear the cache and wait for it to finish
INVALIDATION=$(aws cloudfront create-invalidation --distribution-id $DISTRIBUTION --paths "/*" --query Invalidation.Id --output text)
aws cloudfront wait invalidation-completed --distribution-id $DISTRIBUTION --id $INVALIDATION

echo "Done deploying $RELEASE"
