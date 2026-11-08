"""verify.py - check that the live website is up and secure.

Runs the seven checks the project requires and prints the results as JSON.
Exit code 0 means every check passed, 1 means at least one failed.

Usage:
    python3 tools/verify.py
"""
import http.client
import json
import socket
import ssl
import sys
from datetime import datetime, timezone

DOMAIN = "csce412prra2413.me"
BUCKET = "csce412-prra2413-site"
PAGES = ["/", "/index.html", "/about.html", "/events.html", "/mission.html", "/signin.html"]
TIMEOUT = 10


def request(scheme, host, path="/"):
    """Send one GET request without following redirects. Returns (status, headers)."""
    if scheme == "https":
        conn = http.client.HTTPSConnection(host, timeout=TIMEOUT)
    else:
        conn = http.client.HTTPConnection(host, timeout=TIMEOUT)
    try:
        conn.request("GET", path, headers={"User-Agent": "csce412-verify"})
        resp = conn.getresponse()
        headers = {k.lower(): v for k, v in resp.getheaders()}
        resp.read()
        return resp.status, headers
    finally:
        conn.close()


def check_dns():
    ips = sorted({info[4][0] for info in socket.getaddrinfo(DOMAIN, 443, proto=socket.IPPROTO_TCP)})
    return len(ips) > 0, {"addresses": ips}


def check_https():
    status, _ = request("https", DOMAIN, "/")
    return status == 200, {"url": f"https://{DOMAIN}/", "status": status}


def check_redirect():
    status, headers = request("http", DOMAIN, "/")
    location = headers.get("location", "")
    passed = status in (301, 302, 307, 308) and location.startswith("https://")
    return passed, {"url": f"http://{DOMAIN}/", "status": status, "location": location}


def check_certificate():
    context = ssl.create_default_context()  # checks the chain and that the name matches
    with socket.create_connection((DOMAIN, 443), timeout=TIMEOUT) as sock:
        with context.wrap_socket(sock, server_hostname=DOMAIN) as tls:
            cert = tls.getpeercert()
    names = [value for kind, value in cert.get("subjectAltName", ()) if kind == "DNS"]
    issuer = dict(item[0] for item in cert.get("issuer", ()))
    expires = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
    passed = DOMAIN in names and expires > datetime.now(timezone.utc)
    return passed, {
        "names": names,
        "issuer": issuer.get("organizationName", ""),
        "expires": expires.isoformat(),
    }


def check_pages():
    results = {}
    for page in PAGES:
        status, _ = request("https", DOMAIN, page)
        results[page] = status
    return all(code == 200 for code in results.values()), {"pages": results}


def check_s3_private():
    host = f"{BUCKET}.s3.amazonaws.com"
    status, _ = request("https", host, "/index.html")
    return status == 403, {"url": f"https://{host}/index.html", "status": status}


def check_cloudfront():
    _, headers = request("https", DOMAIN, "/")
    via = headers.get("via", "")
    x_cache = headers.get("x-cache", "")
    passed = "cloudfront" in via.lower() or "cloudfront" in x_cache.lower()
    return passed, {"via": via, "x-cache": x_cache}


CHECKS = [
    ("domain_resolves", check_dns),
    ("https_works", check_https),
    ("http_redirects_to_https", check_redirect),
    ("certificate_matches_domain", check_certificate),
    ("pages_load", check_pages),
    ("s3_direct_access_denied", check_s3_private),
    ("cloudfront_serves_content", check_cloudfront),
]


def run_checks():
    results = []
    for name, check in CHECKS:
        try:
            passed, evidence = check()
        except Exception as error:  # a crash counts as a failed check, with the reason recorded
            passed, evidence = False, {"error": f"{type(error).__name__}: {error}"}
        results.append({"check": name, "passed": passed, "evidence": evidence})
    return {
        "time": datetime.now(timezone.utc).isoformat(),
        "domain": DOMAIN,
        "passed": sum(r["passed"] for r in results),
        "total": len(results),
        "results": results,
    }


if __name__ == "__main__":
    report = run_checks()
    print(json.dumps(report, indent=2))
    sys.exit(0 if report["passed"] == report["total"] else 1)
