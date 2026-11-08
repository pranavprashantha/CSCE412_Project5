"""apply_fix.py - apply ONE fix from a short, fixed list.

Only the orchestrator calls this, and only after a human types "yes".
The agents can suggest a fix by name, but they cannot invent new commands.

Usage:
    python3 tools/apply_fix.py restore_bucket_policy
"""
import json
import os
import sys
import tempfile

from common import ROOT, aws, settings


def restore_bucket_policy():
    path = os.path.join(ROOT, "config", "bucket-policy.json")
    return aws("s3api", "put-bucket-policy", "--bucket", settings()["bucket"], "--policy", f"file://{path}")


def _update_cloudfront(change):
    dist = settings()["distribution_id"]
    ok, out = aws("cloudfront", "get-distribution-config", "--id", dist)
    if not ok:
        return ok, out
    data = json.loads(out)
    config = data["DistributionConfig"]
    change(config)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(config, f)
    try:
        return aws("cloudfront", "update-distribution", "--id", dist, "--if-match", data["ETag"],
                   "--distribution-config", f"file://{f.name}")
    finally:
        os.remove(f.name)


def set_default_root_object():
    return _update_cloudfront(lambda c: c.update(DefaultRootObject="index.html"))


def set_https_redirect():
    return _update_cloudfront(lambda c: c["DefaultCacheBehavior"].update(ViewerProtocolPolicy="redirect-to-https"))


FIXES = {
    "restore_bucket_policy": (restore_bucket_policy, "Put back the saved S3 bucket policy that lets CloudFront read the files"),
    "set_default_root_object": (set_default_root_object, "Set CloudFront's default root object to index.html"),
    "set_https_redirect": (set_https_redirect, "Set CloudFront to redirect HTTP to HTTPS"),
}


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else ""
    if name not in FIXES:
        print(json.dumps({"ok": False, "error": f"unknown fix '{name}'", "allowed": list(FIXES)}))
        sys.exit(2)
    ok, out = FIXES[name][0]()
    print(json.dumps({"ok": ok, "fix": name, "output": out[:500]}))
    sys.exit(0 if ok else 1)
