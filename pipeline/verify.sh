#!/bin/bash
# Verify stage
# Checks the live site.
# Pass: save this release as the known-good one.
# Fail: roll back to the last known-good release and fail the pipeline.

RELEASE_BUCKET="csce412-prra2413-releases"
RELEASE=$(python3 -c "import json; print(json.load(open('website/version.json'))['release'])")

if python3 pipeline/check_live.py $RELEASE; then
    echo $RELEASE | aws s3 cp - s3://$RELEASE_BUCKET/known-good.txt
    echo "Release $RELEASE passed and is now the known-good release"
    exit 0
fi

echo "Release $RELEASE failed. Rolling back."
cp reports/verify-results.json reports/verify-failed.json
bash pipeline/rollback.sh
exit 1
