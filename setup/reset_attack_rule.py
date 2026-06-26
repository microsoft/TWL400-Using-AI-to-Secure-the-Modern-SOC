"""
reset_attack_rule.py
Clears the PT24H suppression on the "SOC Lab — cross-layer attack" analytics
rule and sets frequency to PT5M so it fires immediately on the next re-seed
without being blocked by the 24-hour suppression window.

WHY THIS IS NEEDED:
  The cross-layer attack rule has suppressionEnabled=True, PT24H. After
  cleanup_incidents.py deletes the incident, the underlying Sentinel alert
  still exists and the suppression clock is still running. The rule will
  not create a new incident until 24 hours after the last alert, regardless
  of how many times events are re-seeded.

  This script resets that state. After the new incident appears, re-run
  add_entity_mappings.py to re-enable suppression.

FULL TEARDOWN + RE-SEED SEQUENCE:
  1. python cleanup_incidents.py           # delete Sentinel incidents
  2. python cleanup_xdr_incidents.py       # resolve Defender XDR incidents (jailbreak)
  3. python reset_attack_rule.py           # reset suppression (THIS SCRIPT)
  4. .\\seed_events.ps1 -Domain <domain>   # seed 30 events
  5. python update_rule_frequency.py PT5M --all   # already set by this script
  6. python seed_ai_attacks.py             # trigger jailbreak
  7. wait 10-30 min; verify incidents in Defender portal
  8. python update_rule_frequency.py PT1H --all   # reset cadence
  9. python add_entity_mappings.py         # re-enable PT24H suppression

Usage:
  python reset_attack_rule.py

Requires: az CLI signed in with Owner access to the subscription.
"""

import subprocess
import json
import sys
import tempfile
import os

# ── Lab config ────────────────────────────────────────────────────────────────
RESOURCE_GROUP = "rg-soclab"
RULE_KEYWORD    = "cross-layer"
API_VERSION     = "2023-02-01"
# ─────────────────────────────────────────────────────────────────────────────


def az(args, check=True):
    result = subprocess.run(["az"] + args, capture_output=True, text=True, shell=True)
    if check and result.returncode != 0:
        print(f"ERROR: {result.stderr.strip()}")
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


def main():
    print("=" * 60)
    print("SOC Lab — Reset Attack Rule Suppression")
    print("=" * 60)

    subscription_id = discover_subscription_id()
    workspace_name = discover_workspace_name()
    print(f"Subscription : {subscription_id}")
    print(f"Workspace    : {workspace_name}")

    base_url = (
        f"https://management.azure.com/subscriptions/{subscription_id}"
        f"/resourceGroups/{RESOURCE_GROUP}"
        f"/providers/Microsoft.OperationalInsights/workspaces/{workspace_name}"
        f"/providers/Microsoft.SecurityInsights/alertRules"
        f"?api-version={API_VERSION}"
    )

    print("\nFetching alert rules...")
    rules = json.loads(az(["rest", "--method", "get", "--url", base_url]))["value"]

    rule = next((r for r in rules if RULE_KEYWORD in r["properties"].get("displayName", "")), None)
    if not rule:
        print(f"ERROR: No rule found containing '{RULE_KEYWORD}'.")
        sys.exit(1)

    props = rule["properties"]
    print(f"  Rule       : {props['displayName']}")
    print(f"  Suppression: {props.get('suppressionEnabled')} / {props.get('suppressionDuration')}")
    print(f"  Frequency  : {props.get('queryFrequency')}")

    # Remove read-only fields
    for field in ["lastModifiedUtc", "createdTimeUtc", "lastModifiedBy", "createdBy"]:
        props.pop(field, None)

    # Disable suppression + force fast firing
    props["suppressionEnabled"]  = False
    props["suppressionDuration"] = "PT1H"   # ignored while disabled, but required by API
    props["queryFrequency"]      = "PT5M"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(rule, f)
        tmp = f.name

    try:
        put_url = f"https://management.azure.com{rule['id']}?api-version={API_VERSION}"
        print("\nApplying: suppressionEnabled=False, queryFrequency=PT5M ...")
        response = az([
            "rest", "--method", "put",
            "--url", put_url,
            "--body", f"@{tmp}",
            "--headers", "Content-Type=application/json"
        ])
        updated = json.loads(response)["properties"]
        print(f"  Suppression now: {updated.get('suppressionEnabled')}")
        print(f"  Frequency now  : {updated.get('queryFrequency')}")
    finally:
        os.unlink(tmp)

    print(
        "\nDone. The cross-layer attack rule will fire within 5 minutes.\n"
        "\nNext steps:\n"
        "  1. Run: .\\seed_events.ps1 -Domain <tenant-domain>\n"
        "  2. Wait ~5 min for the attack incident to appear in Defender.\n"
        "  3. Run: python update_rule_frequency.py PT1H --all   (reset cadence)\n"
        "  4. Run: python add_entity_mappings.py                (re-enable suppression)\n"
    )


if __name__ == "__main__":
    main()
