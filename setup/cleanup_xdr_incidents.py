"""
cleanup_xdr_incidents.py
Resolves Defender XDR-native incidents (e.g. the Defender for Cloud jailbreak
alert) that cannot be touched via the Sentinel ARM API or az rest user tokens.

Requires an app registration with Incident.ReadWrite.All on the Defender XDR API.
Run setup_cleanup_app.py ONCE first to create the app and write .soclab_xdr_creds.json.

Usage:
  python cleanup_xdr_incidents.py              # resolve matching XDR incidents
  python cleanup_xdr_incidents.py --dry-run    # preview without changes
  python cleanup_xdr_incidents.py --filter "Jailbreak"   # custom keyword filter
  python cleanup_xdr_incidents.py --all        # resolve ALL active XDR incidents

Requires:
  - .soclab_xdr_creds.json in the same directory (created by setup_cleanup_app.py)
  - OR --tenant-id, --client-id, --client-secret flags
"""

import json
import sys
import os
import argparse
import time
import urllib.request
import urllib.parse
import urllib.error

# ── Defaults ──────────────────────────────────────────────────────────────────
CREDS_FILE      = os.path.join(os.path.dirname(__file__), ".soclab_xdr_creds.json")
XDR_BASE        = "https://api.security.microsoft.com"
TOKEN_URL_TMPL  = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
XDR_SCOPE       = "https://api.security.microsoft.com/.default"

# Keywords used to identify lab-seeded XDR incidents when --all is not set
DEFAULT_FILTERS = [
    "Jailbreak",
    "jailbreak",
    "Azure AI model",
]
# ─────────────────────────────────────────────────────────────────────────────


def load_creds(args):
    """Load credentials from CLI args or .soclab_xdr_creds.json."""
    if args.tenant_id and args.client_id and args.client_secret:
        return {
            "tenantId":     args.tenant_id,
            "clientId":     args.client_id,
            "clientSecret": args.client_secret,
        }
    if os.path.exists(CREDS_FILE):
        with open(CREDS_FILE, encoding="utf-8") as f:
            return json.load(f)
    print(
        "ERROR: No credentials found.\n"
        "  Run setup_cleanup_app.py first, OR supply --tenant-id, --client-id, --client-secret."
    )
    sys.exit(1)


def get_token(creds):
    """Acquire an access token via client credentials flow."""
    url  = TOKEN_URL_TMPL.format(tenant=creds["tenantId"])
    data = urllib.parse.urlencode({
        "grant_type":    "client_credentials",
        "client_id":     creds["clientId"],
        "client_secret": creds["clientSecret"],
        "scope":         XDR_SCOPE,
    }).encode()

    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            token_data = json.loads(resp.read())
            return token_data["access_token"]
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"ERROR acquiring token: {e.code} {body}")
        sys.exit(1)


def xdr_get(token, path):
    url = f"{XDR_BASE}{path}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  ERROR GET {path}: {e.code} {body}")
        return None


def xdr_patch(token, path, body):
    url  = f"{XDR_BASE}{path}"
    data = json.dumps(body).encode()
    req  = urllib.request.Request(
        url, data=data, method="PATCH",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        }
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  ERROR PATCH {path}: {e.code} {body}")
        return None


def list_active_incidents(token):
    """Return all active XDR incidents (status != Resolved)."""
    results = []
    # OData filter with spaces/quotes must be percent-encoded for urllib
    path    = "/api/incidents?%24filter=status%20ne%20%27Resolved%27&%24top=100"
    while path:
        data = xdr_get(token, path)
        if not data:
            break
        results.extend(data.get("value", []))
        next_link = data.get("@odata.nextLink", "")
        path = next_link.replace(XDR_BASE, "") if next_link else None
    return results


def is_target(incident, filters, match_all):
    if match_all:
        return True
    title = incident.get("incidentName", "") or incident.get("displayName", "")
    return any(kw in title for kw in filters)


def resolve_incident(token, incident_id, dry_run):
    path = f"/api/incidents/{incident_id}"
    if dry_run:
        print(f"    [dry-run] would PATCH {incident_id} → Resolved / Informational / SecurityTesting")
        return True
    result = xdr_patch(token, path, {
        "status":         "Resolved",
        "classification": "TruePositive",
        "determination":  "SecurityTesting",
        "severity":       "informational",
    })
    if result:
        print(f"    Resolved {incident_id}")
        return True
    return False


def main():
    parser = argparse.ArgumentParser(description="Resolve SOC Lab XDR incidents in Defender.")
    parser.add_argument("--dry-run",       action="store_true", help="Preview without changes")
    parser.add_argument("--all",           action="store_true", help="Resolve ALL active XDR incidents")
    parser.add_argument("--filter",        default=None,        help="Custom keyword to match incident titles")
    parser.add_argument("--tenant-id",     default=None)
    parser.add_argument("--client-id",     default=None)
    parser.add_argument("--client-secret", default=None)
    args = parser.parse_args()

    filters   = [args.filter] if args.filter else DEFAULT_FILTERS
    match_all = args.all
    dry       = args.dry_run

    mode = "[DRY RUN] " if dry else ""
    print("=" * 65)
    print(f"SOC Lab — {mode}Defender XDR Incident Cleanup")
    if match_all:
        print("Mode: ALL active incidents")
    else:
        print(f"Filter: title contains any of {filters}")
    print("=" * 65)

    creds = load_creds(args)
    print(f"\nAcquiring token for tenant {creds['tenantId']} ...")
    token = get_token(creds)
    print("  Token acquired.")

    print("\nFetching active XDR incidents ...")
    incidents = list_active_incidents(token)
    print(f"  Found {len(incidents)} active incident(s).")

    targets = [i for i in incidents if is_target(i, filters, match_all)]

    if not targets:
        kw = "all active" if match_all else f"matching {filters}"
        print(f"  No {kw} XDR incidents found — nothing to do.")
    else:
        print(f"\n  {len(targets)} incident(s) to resolve:")
        for inc in targets:
            title    = inc.get("incidentName") or inc.get("displayName", "?")
            inc_id   = inc.get("incidentId") or inc.get("id")
            severity = inc.get("severity", "?")
            status   = inc.get("status", "?")
            print(f"    • [{severity} / {status}] {title}  (id: {inc_id})")

        if not dry:
            print("\nResolving ...")
        ok = fail = 0
        for i, inc in enumerate(targets):
            inc_id = inc.get("incidentId") or inc.get("id")
            if resolve_incident(token, inc_id, dry):
                ok += 1
            else:
                fail += 1
            if not dry and i < len(targets) - 1:
                time.sleep(1.0)

        if not dry:
            print(f"\n  Resolved : {ok}")
            if fail:
                print(f"  Failed   : {fail}")

    print("\nDone.")


if __name__ == "__main__":
    main()
