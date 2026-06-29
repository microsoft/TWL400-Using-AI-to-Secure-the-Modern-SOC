"""
seed_events.py
Injects the SOC Lab attack-chain and noise events into the SocLabEvents_CL
custom table in Log Analytics via the Data Collector API.

Replaces the manual Invoke-WebRequest commands from the runbook.

Timestamps are calculated dynamically at run time so events always appear
"recent" in the Defender portal (no stale fixed dates).

Usage:
  python seed_events.py                        # attack starts 2 hours ago
  python seed_events.py --hours-ago 4          # attack starts 4 hours ago
  python seed_events.py --dry-run              # print events, no POST

Requires:
  - az CLI signed in with Owner access to the subscription.
  - No external Python packages (uses stdlib only).
"""

import subprocess
import json
import sys
import argparse
import hashlib
import hmac
import base64
import datetime
import urllib.request
import urllib.error
import os
import tempfile

# ── Lab config ────────────────────────────────────────────────────────────────
RESOURCE_GROUP = "rg-soclab"
LOG_TYPE        = "SocLabEvents"    # Sentinel appends _CL automatically → SocLabEvents_CL
EVENTS_FILE     = os.path.join(os.path.dirname(__file__), "events.json")
# ─────────────────────────────────────────────────────────────────────────────


def az(args, check=True):
    result = subprocess.run(["az"] + args, capture_output=True, text=True, shell=True)
    if check and result.returncode != 0:
        print(f"  ERROR: {result.stderr.strip()}")
        sys.exit(1)
    return result.stdout.strip()


def discover_workspace_name():
    """Discover the Log Analytics workspace name from the resource group at runtime."""
    name = az(["monitor", "log-analytics", "workspace", "list",
               "-g", RESOURCE_GROUP, "--query", "[0].name", "-o", "tsv"])
    if not name:
        print(f"ERROR: No Log Analytics workspace found in {RESOURCE_GROUP}.")
        sys.exit(1)
    return name


def get_workspace_credentials(workspace_name):
    """Fetch workspace ID (customerId) and primary shared key via az CLI."""
    print("Fetching workspace credentials...")

    workspace_id = az([
        "monitor", "log-analytics", "workspace", "show",
        "--resource-group", RESOURCE_GROUP,
        "--workspace-name", workspace_name,
        "--query", "customerId",
        "--output", "tsv"
    ])

    shared_key = az([
        "monitor", "log-analytics", "workspace", "get-shared-keys",
        "--resource-group", RESOURCE_GROUP,
        "--workspace-name", workspace_name,
        "--query", "primarySharedKey",
        "--output", "tsv"
    ])

    if not workspace_id or not shared_key:
        print("ERROR: Could not retrieve workspace credentials.")
        sys.exit(1)

    print(f"  Workspace ID : {workspace_id}")
    print(f"  Shared key   : {'*' * 20}  (retrieved)")
    return workspace_id, shared_key


def build_signature(workspace_id, shared_key, date_str, content_length):
    """Build the HMAC-SHA256 SharedKey signature for the Data Collector API."""
    string_to_hash = (
        f"POST\n"
        f"{content_length}\n"
        f"application/json\n"
        f"x-ms-date:{date_str}\n"
        f"/api/logs"
    )
    decoded_key = base64.b64decode(shared_key)
    signature = base64.b64encode(
        hmac.new(decoded_key, string_to_hash.encode("utf-8"), digestmod=hashlib.sha256).digest()
    ).decode("utf-8")
    return f"SharedKey {workspace_id}:{signature}"


def post_events(workspace_id, shared_key, events_batch, dry_run):
    """POST a batch of events to the Log Analytics Data Collector API."""
    body = json.dumps(events_batch, default=str).encode("utf-8")
    date_str = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
    content_length = len(body)

    if dry_run:
        print(f"  [dry-run] would POST {len(events_batch)} event(s):")
        for e in events_batch:
            print(f"    [{e.get('Stage','?')}] {e.get('Action','?')} — {e.get('Account','?')}  (T={e.get('TimeGenerated','?')})")
        return True

    auth = build_signature(workspace_id, shared_key, date_str, content_length)
    url = f"https://{workspace_id}.ods.opinsights.azure.com/api/logs?api-version=2016-04-01"

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Log-Type": LOG_TYPE,
            "Authorization": auth,
            "x-ms-date": date_str,
            "time-generated-field": "TimeGenerated"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
            body_resp = resp.read().decode("utf-8")
            print(f"  HTTP {status}: {body_resp[:200] if body_resp else '(no body)'}")
            return status in (200, 204)
    except urllib.error.HTTPError as e:
        body_err = e.read().decode("utf-8")
        print(f"  HTTP {e.code}: {body_err[:300]}")
        return False
    except Exception as ex:
        print(f"  Error: {ex}")
        return False


def load_events(hours_ago, domain, subscription_id):
    """Load events.json, substitute domain, and calculate concrete UTC timestamps."""
    with open(EVENTS_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)

    attack_start = datetime.datetime.utcnow() - datetime.timedelta(hours=hours_ago)
    events = []

    for item in raw:
        # Skip comment-only objects
        if "_comment" in item and "Stage" not in item:
            continue

        offset_minutes = item.get("TimeOffsetMinutes", 0)
        event_time = attack_start + datetime.timedelta(minutes=offset_minutes)

        # Substitute {DOMAIN} / {SUBSCRIPTION} placeholders
        account = item.get("Account", "").replace("{DOMAIN}", domain)
        recipient = item.get("Recipient", "").replace("{DOMAIN}", domain)
        azure_resource_id = item.get("AzureResourceId", "").replace("{SUBSCRIPTION}", subscription_id)

        events.append({
            "TimeGenerated":    event_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "Stage":            item.get("Stage", ""),
            "Account":          account,
            "Device":           item.get("Device", ""),
            "SourceIP":         item.get("SourceIP", ""),
            "Action":           item.get("Action", ""),
            "Severity":         item.get("Severity", "Informational"),
            "Sender":           item.get("Sender", ""),
            "Recipient":        recipient,
            "Subject":          item.get("Subject", ""),
            "NetworkMessageId": item.get("NetworkMessageId", ""),
            "AzureResourceId":  azure_resource_id,
            "ServicePrincipal": item.get("ServicePrincipal", ""),
            "Details":          item.get("Details", ""),
        })

    return events


def main():
    parser = argparse.ArgumentParser(description="Seed SOC Lab events into SocLabEvents_CL.")
    parser.add_argument("--hours-ago", type=float, default=2.0,
                        help="How many hours ago the attack chain starts (default: 2)")
    parser.add_argument("--domain", type=str, default=None,
                        help="Tenant domain to substitute for {DOMAIN} in Account fields "
                             "(e.g. contoso.onmicrosoft.com). If omitted, fetched via az CLI.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print events without posting")
    args = parser.parse_args()

    # Resolve domain
    domain = args.domain
    if not domain:
        print("No --domain supplied; fetching from az CLI...")
        domain = az([
            "ad", "signed-in-user", "show",
            "--query", "userPrincipalName",
            "--output", "tsv"
        ], check=False)
        if domain and "@" in domain:
            domain = domain.split("@")[1].strip()
        else:
            print("  ERROR: Could not determine tenant domain automatically.")
            print("  Re-run with: python seed_events.py --domain <your-tenant-domain>")
            sys.exit(1)
        print(f"  Resolved domain: {domain}")

    workspace_name = discover_workspace_name()
    subscription_id = az(["account", "show", "--query", "id", "-o", "tsv"])
    if not subscription_id:
        print("ERROR: Could not determine subscription ID. Is az CLI signed in?")
        sys.exit(1)

    print("=" * 60)
    print("SOC Lab — Event Seeding")
    print(f"Workspace    : {workspace_name}")
    print(f"Domain       : {domain}")
    print(f"Attack start : {args.hours_ago} hours ago")
    print(f"Mode         : {'DRY RUN' if args.dry_run else 'LIVE'}")
    print("=" * 60)

    events = load_events(args.hours_ago, domain, subscription_id)

    print(f"\nLoaded {len(events)} event(s) (attack stages interleaved with noise).")

    if not args.dry_run:
        workspace_id, shared_key = get_workspace_credentials(workspace_name)
    else:
        workspace_id = shared_key = None

    # Post all events in a single batch — preserves chronological interleaving
    print("\n── All events ───────────────────────────────────────�