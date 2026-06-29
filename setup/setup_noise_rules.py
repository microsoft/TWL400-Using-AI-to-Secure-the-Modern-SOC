"""
setup_noise_rules.py
Creates (or deletes) 25 Sentinel scheduled analytics rules — one per noise event
in events.json — so that noise incidents appear in the Defender portal alongside
the cross-layer attack incident.

WHY THIS APPROACH:
  The unified Defender portal only surfaces Sentinel incidents that have a backing
  alert created by an analytics rule. Incidents created directly via the Sentinel
  ARM API (our old seed_noise_incidents.py approach) exist in Sentinel but are
  invisible in Defender. The ONLY working path is:

    events.json  →  seed_events.py  →  SocLabEvents_CL
                                              ↓  (30 events seeded)
    25 noise rules fire  →  25 alerts  →  25 Defender incidents
    1 attack rule fires  →   1 alert   →   1 Defender incident

Each noise rule targets exactly one Stage_s value (noise-01 through noise-25),
which maps to one row in SocLabEvents_CL after seeding.

IDEMPOTENT: Rule IDs are derived deterministically from the Stage_s value
(uuid5), so running this script twice creates/overwrites the same 25 rules.

Usage:
  python setup_noise_rules.py           # create all 25 noise rules
  python setup_noise_rules.py --delete  # delete all 25 noise rules
  python setup_noise_rules.py --dry-run # show what would be created

Run this ONCE after deploying the tenant.
Run seed_events.py (and update_rule_frequency.py PT5M) each time you re-seed.

Requires: az CLI signed in with Owner access to the subscription.
"""

import subprocess
import json
import sys
import argparse
import uuid
import tempfile
import os
import time

# ── Lab config ────────────────────────────────────────────────────────────────
RESOURCE_GROUP = "rg-soclab"
API_VERSION    = "2023-02-01"
# ─────────────────────────────────────────────────────────────────────────────

# ── One entry per noise event in events.json ──────────────────────────────────
# stage:         matches Stage_s value in SocLabEvents_CL
# displayName:   incident title seen in the Defender portal
# severity:      "Informational" | "Low" | "Medium"
#
# Distribution: ~7 Informational, ~10 Low, ~8 Medium
# Medium noise incidents are deliberately alarming so students can't just
# filter to Medium severity to find the real cross-layer attack — they have
# to investigate each one.
# ─────────────────────────────────────────────────────────────────────────────
NOISE_RULES = [
    {
        "stage":       "noise-01",
        "displayName": "SOC Lab — Build Pipeline: Automated VM Scale Event",
        "severity":    "Low",
    },
    {
        "stage":       "noise-02",
        "displayName": "SOC Lab — Sign-in: MFA Satisfied via Authenticator",
        "severity":    "Informational",
    },
    {
        "stage":       "noise-03",
        "displayName": "SOC Lab — Sign-in: Conditional Access Policy Satisfied",
        "severity":    "Informational",
    },
    {
        "stage":       "noise-04",
        "displayName": "SOC Lab — Patch Deployment: Server Reboot Deferred",
        "severity":    "Low",
    },
    {
        "stage":       "noise-05",
        "displayName": "SOC Lab — Sign-in: HR Portal and SharePoint Accessed",
        "severity":    "Informational",
    },
    {
        "stage":       "noise-06",
        "displayName": "SOC Lab — Finance Document Library Accessed",
        "severity":    "Low",
    },
    {
        "stage":       "noise-07",
        "displayName": "SOC Lab — Sign-in from Known Corporate Network",
        "severity":    "Informational",
    },
    {
        "stage":       "noise-08",
        "displayName": "SOC Lab — Large Archive Download: Procurement Records",
        "severity":    "Medium",
    },
    {
        "stage":       "noise-09",
        "displayName": "SOC Lab — Sign-in via FIDO2 Hardware Key",
        "severity":    "Informational",
    },
    {
        "stage":       "noise-10",
        "displayName": "SOC Lab — MFA Verification: VPN Reconnect",
        "severity":    "Low",
    },
    {
        "stage":       "noise-11",
        "displayName": "SOC Lab — Teams Message Sent to External Domain Contact",
        "severity":    "Low",
    },
    {
        "stage":       "noise-12",
        "displayName": "SOC Lab — API Health Check: Elevated Response Volume",
        "severity":    "Low",
    },
    {
        "stage":       "noise-13",
        "displayName": "SOC Lab — Self-Service Password Reset Completed",
        "severity":    "Informational",
    },
    {
        "stage":       "noise-14",
        "displayName": "SOC Lab — Large File Upload to Personal OneDrive",
        "severity":    "Low",
    },
    {
        "stage":       "noise-15",
        "displayName": "SOC Lab — IT Runbook Library Accessed",
        "severity":    "Low",
    },
    {
        "stage":       "noise-16",
        "displayName": "SOC Lab — Email Received from Unverified External Domain",
        "severity":    "Medium",
    },
    {
        "stage":       "noise-17",
        "displayName": "SOC Lab — Teams Call: External Guest from Unmanaged Device",
        "severity":    "Medium",
    },
    {
        "stage":       "noise-18",
        "displayName": "SOC Lab — Teams Meeting: IT Operations Group",
        "severity":    "Low",
    },
    {
        "stage":       "noise-19",
        "displayName": "SOC Lab — Azure Storage Key Enumeration via ARM API",
        "severity":    "Medium",
    },
    {
        "stage":       "noise-20",
        "displayName": "SOC Lab — Sensitive SharePoint Site Accessed: RefundKB",
        "severity":    "Medium",
    },
    {
        "stage":       "noise-21",
        "displayName": "SOC Lab — Repeated Teams Contact with External Vendor",
        "severity":    "Medium",
    },
    {
        "stage":       "noise-22",
        "displayName": "SOC Lab — MFA Verification: Outlook Web Access",
        "severity":    "Informational",
    },
    {
        "stage":       "noise-23",
        "displayName": "SOC Lab — Inbound Email from External Financial Domain",
        "severity":    "Medium",
    },
    {
        "stage":       "noise-24",
        "displayName": "SOC Lab — API Telemetry Flush: Elevated Event Count",
        "severity":    "Low",
    },
    {
        "stage":       "noise-25",
        "displayName": "SOC Lab — Multiple HR Documents Downloaded",
        "severity":    "Medium",
    },
]


def rule_id_for(stage: str) -> str:
    """Deterministic UUID derived from the stage name — same stage = same rule ID.
    Running this script twice is idempotent: it just overwrites the same rules."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"soclab-noise-{stage}"))


def build_rule_body(entry: dict) -> dict:
    stage = entry["stage"]
    query = f"""SocLabEvents_CL
| where TimeGenerated > ago(4h)
| where Stage_s == "{stage}"
| extend
    Account  = Account_s,
    Device   = column_ifexists("Device_s", ""),
    SourceIP = column_ifexists("SourceIP_s", "")
| project TimeGenerated, Account, Device, SourceIP, Action = Action_s, Details = Details_s"""

    return {
        "kind": "Scheduled",
        "properties": {
            "displayName":     entry["displayName"],
            "description":     (
                f"Background noise rule for lab seeding ({stage}). "
                "Fires when matching events exist in SocLabEvents_CL within the last 4 hours. "
                "Created by setup_noise_rules.py. Safe to delete — recreate with that script."
            ),
            "severity":        entry["severity"],
            "enabled":         True,
            "query":           query,
            "queryFrequency":  "PT1H",
            "queryPeriod":     "PT4H",
            "triggerOperator": "GreaterThan",
            "triggerThreshold": 0,
            "suppressionEnabled":  False,
            "suppressionDuration": "PT1H",
            "tactics":         [],
            "techniques":      [],
            "entityMappings": [
                {
                    "entityType": "Account",
                    "fieldMappings": [
                        {"identifier": "FullName", "columnName": "Account"}
                    ]
                }
            ],
            "incidentConfiguration": {
                "createIncident": True,
                "groupingConfiguration": {
                    "enabled":               True,
                    "reopenClosedIncident":  False,
                    "lookbackDuration":      "PT5H",
                    "matchingMethod":        "AllEntities",
                    "groupByEntities":       [],
                    "groupByAlertDetails":   [],
                    "groupByCustomDetails":  []
                }
            }
        }
    }


def az(args, check=True):
    result = subprocess.run(["az"] + args, capture_output=True, text=True, shell=True)
    if check and result.returncode != 0:
        print(f"  ERROR: {result.stderr.strip()}")
        sys.exit(1)
    return result.stdout.strip()


def discover_subscription_id():
    sub_id = az(["account", "show", "--query", "id", "-o", "tsv"])
    if not sub_id:
        print("ERROR: Could not determine subscription ID. Is az CLI signed in?")
        sys.exit(1)
    return sub_id


def discover_workspace_name():
    """Discover the Log Analytics workspace name from the resource group at runtime."""
    name = az(["monitor", "log-analytics", "workspace", "list",
               "-g", RESOURCE_GROUP, "--query", "[0].name", "-o", "tsv"])
    if not name:
        print(f"ERROR: No Log Analytics workspace found in {RESOURCE_GROUP}.")
        sys.exit(1)
    return name


def create_rule(entry, sentinel_rules_base, dry_run):
    rule_id   = rule_id_for(entry["stage"])
    put_url   = f"{sentinel_rules_base}/{rule_id}?api-version={API_VERSION}"
    body      = build_rule_body(entry)

    if dry_run:
        print(f"  [dry-run] [{entry['severity']:13s}] {entry['displayName']}")
        print(f"            Stage: {entry['stage']}  Rule ID: {rule_id}")
        return True

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(body, f)
        tmp = f.name

    try:
        az([
            "rest", "--method", "put",
            "--url", put_url,
            "--body", f"@{tmp}",
            "--headers", "Content-Type=application/json"
        ])
        return True
    except SystemExit:
        return False
    finally:
        os.unlink(tmp)


def delete_rule(entry, sentinel_rules_base, dry_run):
    rule_id    = rule_id_for(entry["stage"])
    delete_url = f"{sentinel_rules_base}/{rule_id}?api-version={API_VERSION}"

    if dry_run:
        print(f"  [dry-run] DELETE {entry['displayName']}  ({rule_id[:8]}...)")
        return True

    result = subprocess.run(
        ["az", "rest", "--method", "delete", "--url", delete_url],
        capture_output=True, text=True, shell=True
    )
    if result.returncode != 0 and "NotFound" not in result.stderr:
        print(f"  WARN: {result.stderr.strip()}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Create or delete the 25 SOC Lab noise analytics rules."
    )
    parser.add_argument("--delete",  action="store_true", help="Delete the noise rules instead of creating them")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without making changes")
    args = parser.parse_args()

    mode    = "DELETE" if args.delete else "CREATE"
    dry_str = " [DRY RUN]" if args.dry_run else ""

    subscription_id = discover_subscription_id()
    workspace_name = discover_workspace_name()
    sentinel_rules_base = (
        f"https://management.azure.com/subscriptions/{subscription_id}"
        f"/resourceGroups/{RESOURCE_GROUP}"
        f"/providers/Microsoft.OperationalInsights/workspaces/{workspace_name}"
        f"/providers/Microsoft.SecurityInsights/alertRules"
    )

    print("=" * 65)
    print(f"SOC Lab — Noise Analytics Rules Setup{dry_str}")
    print(f"Workspace: {workspace_name}")
    print(f"Action   : {mode}  ({len(NOISE_RULES)} rules)")
    print("=" * 65)

    ok = fail = 0
    for i, entry in enumerate(NOISE_RULES):
        print(f"\n[{i+1:02d}/{len(NOISE_RULES)}] {entry['stage']}  |  {entry['displayName']}")

        if args.delete:
            success = delete_rule(entry, sentinel_rules_base, args.dry_run)
        else:
            success = create_rule(entry, sentinel_rules_base, args.dry_run)

        if success:
            ok += 1
        else:
            fail += 1
            print("         FAILED — continuing")

        if not args.dry_run and i < len(NOISE_RULES) - 1:
            time.sleep(0.5)

    print("\n" + "=" * 65)
    print("Done.")
    if not args.dry_run:
        print(f"  {'Created' if not args.delete else 'Deleted'} : {ok}")
        if fail:
            print(f"  Failed  : {fail}")

        if not args.delete:
            print(
                "\nNext steps:\n"
                "  1. Seed events:   .\\seed_events.ps1 -Domain <tenant-domain>\n"
                "  2. Force firing:  python update_rule_frequency.py PT5M --all\n"
                "  3. Wait ~5 min, then check Defender incidents queue.\n"
                "  4. Reset cadence: python update_rule_frequency.py PT1H --all\n"
                "\nExpected result: ~25 Informational/Low noise incidents + the\n"
                "cross-layer attack incident visible in the Defender portal."
            )


if __name__ == "__main__":
    main()
