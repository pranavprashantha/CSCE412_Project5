"""aws_inspect.py - read-only look at the AWS settings behind the website.

Used by the Security/Validator agent when a check fails. Nothing here changes AWS.

Usage:
    python3 tools/aws_inspect.py
"""
import json
import sys

from common import aws, settings


def bucket_policy():
    ok, out = aws("s3api", "get-bucket-policy", "--bucket", settings()["bucket"])
    if not ok:
        return {"present": False, "error": out}
    return {"present": True, "policy": json.loads(json.loads(out)["Policy"])}


def public_access_block():
    ok, out = aws("s3api", "get-public-access-block", "--bucket", settings()["bucket"])
    return json.loads(out)["PublicAccessBlockConfiguration"] if ok else {"error": out}


def cloudfront():
    ok, out = aws("cloudfront", "get-distribution-config", "--id", settings()["distribution_id"])
    if not ok:
        return {"error": out}
    cfg = json.loads(out)["DistributionConfig"]
    origin = cfg["Origins"]["Items"][0]
    return {
        "enabled": cfg["Enabled"],
        "aliases": cfg.get("Aliases", {}).get("Items", []),
        "default_root_object": cfg.get("DefaultRootObject", ""),
        "viewer_protocol_policy": cfg["DefaultCacheBehavior"]["ViewerProtocolPolicy"],
        "origin_domain": origin["DomainName"],
        "origin_access_control_id": origin.get("OriginAccessControlId", ""),
        "certificate_arn": cfg["ViewerCertificate"].get("ACMCertificateArn", ""),
        "custom_error_responses": [
            {"code": e["ErrorCode"], "page": e.get("ResponsePagePath", ""), "response": e.get("ResponseCode", "")}
            for e in cfg.get("CustomErrorResponses", {}).get("Items", [])
        ],
    }


def dns_records():
    domain = settings()["domain"] + "."
    ok, out = aws("route53", "list-hosted-zones")
    if not ok:
        return {"error": out}
    zones = [z for z in json.loads(out)["HostedZones"] if z["Name"] == domain]
    if not zones:
        return {"error": f"no hosted zone named {domain}"}
    ok, out = aws("route53", "list-resource-record-sets", "--hosted-zone-id", zones[0]["Id"])
    if not ok:
        return {"error": out}
    records = []
    for r in json.loads(out)["ResourceRecordSets"]:
        if r["Name"] == domain and r["Type"] in ("A", "AAAA"):
            records.append({"type": r["Type"], "alias_target": r.get("AliasTarget", {}).get("DNSName", "")})
    return {"records": records}


def inspect_all():
    return {
        "bucket_policy": bucket_policy(),
        "public_access_block": public_access_block(),
        "cloudfront": cloudfront(),
        "dns": dns_records(),
    }


if __name__ == "__main__":
    print(json.dumps(inspect_all(), indent=2))
    sys.exit(0)
