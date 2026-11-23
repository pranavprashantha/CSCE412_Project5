#!/bin/bash
# Rollback
# Puts the last known-good release back on the site and checks it again.
set -e

SITE_BUCKET="csce412-prra2413-site"
RELEASE_BUCKET="csce412-prra2413-releases"
DISTRIBUTION="E2XE8SGMTOFJIB"

GOOD=$(aws s3 cp s3://$RELEASE_BUCKET/known-good.txt -)
echo "Rolling back to release $GOOD"

# copy the whole good release back to the site
aws s3 sync s3://$RELEASE_BUCKET/releases/$GOOD/ s3://$SITE_BUCKET/ --delete

# clear the cache and wait for it to finish
INVALIDATION=$(aws cloudfront create-invalidation --distribution-id $DISTRIBUTION --paths "/*" --query Invalidation.Id --output text)
aws cloudfront wait invalidation-completed --distribution-id $DISTRIBUTION --id $INVALIDATION

# check the site again
python3 pipeline/check_live.py $GOOD
echo "Rollback to $GOOD worked"
