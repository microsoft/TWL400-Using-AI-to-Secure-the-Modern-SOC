"""
update_rule_frequency.py
Updates or enables/disables Sentinel analytics rules for SOC Lab.

Usage:
  python update_rule_frequency.py PT5M        # update attack rule frequency only
  python update_rule_frequency.py PT5M --all  # update ALL SOC Lab rules (attack + 25 noise)
  python update_rule_frequency.py PT1H --all  # reset all to normal cadence
  python update_rule_frequency.py --disable --all  # disable all SOC Lab rules
  python update_rule_frequency.py --enable --all   # re-enable all SOC Lab rules

Recommended workflow:
  1. After incidents are created: --disable --all  (stops duplicate incident generation)
  2. Before re-seeding:          --enable --all
  3. Force fire:                 PT5M --all
  4. Wait for incidents, then:   PT1H --all
  5. Disable again:              --disable --all

Requires: az CLI signed in with Owner access to the subscription.
"""

import subprocess
import json
import sys
import tempfile
import os

# ── Lab config ────────────────────────────────────────────────────────────────
RESOURCE_GROUP = "rg-soclab"
RULE_KEYWORD    = "cross-layer"   # used when --all is not set
SOC_LAB_PREFIX  = "SOC Lab"       # used when --all is set
API_VERSION     = "2023-02-01"
# ─────────────────────────────────────────────────────────────────────────────

def az(args):
    result = subprocess.run(["az"] + args, capture_output=True, text=True, shell=True)
    if result.returncode != 0:
        print(f"ERROR: {result.stderr.strip()}")
        sys.exit(1)
    return result.stdout


def discover_subscription_id():
    sub_id = az(["account", "show", "--query", "id", "-o", "tsv"]).strip()
    if not sub_id:
        print("ERROR: Could not determine subscription ID. Is az CLI signed in?")
        sys.exit(1)
    return sub_id


def discover_workspace_name():
    """Discover the Log Analytics workspace name from the resource group at runtime."""
    name = az(["monitor", "log-analytics", "workspace", "list",
               "-g", RESOURCE_GROUP, "--query", "[0].name", "-o", "tsv"]).strip()
    if not name:
        print(f"ERROR: No Log Analytics workspace found in {RESOURCE_GROUP}.")
        sys.exit(1)
    return name


def put_rule(rule):
    """PUT the rule back to the API, stripping read-only fields first."""
    rule_id = rule["id"]
    for field in ["lastModifiedUtc", "createdTimeUtc", "lastModifiedBy", "createdBy"]:
        rule["properties"].pop(field, None)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(rule, f)
        temp_path = f.name
    try:
        put_url = f"https://management.azure.com{rule_id}?api-version={API_VERSION}"
        response = az([
            "rest", "--method", "put",
            "--url", put_url,
            "--body", f"@{temp_path}",
            "--headers", "Content-Type=application/json"
        ])
        return json.loads(response)
    finally:
        os.unlink(temp_path)


def update_rule(rule, new_frequency):
    display_name  = rule["properties"]["displayName"]
    old_frequency = rule["properties"]["queryFrequency"]

    if old_frequency == new_frequency:
        print(f"  {display_name[:60]}")
        print(f"    Already {new_frequency} — skipped.")
        return

    rule["properties"]["queryFrequency"] = new_frequency
    updated = put_rule(rule)
    new_freq = updated["properties"]["queryFrequency"]
    print(f"  {display_name[:60]}")
    print(f"    {old_frequency} → {new_freq}")


def set_rule_enabled(rule, enabled):
    display_name = rule["properties"]["displayName"]
    state_str    = "enabled" if enabled else "disabled"

    # Always PUT the target state. ARM read-after-write is eventually consistent,
    # so deciding whether to act based on the fetched 'enabled' value can skip a
    # change that's actually needed (e.g. re-enabling a rule that was just disabled,
    # where the GET still returns the stale pre-disable value).
    rule["properties"]["enabled"] = enabled
    put_rule(rule)
    print(f"  {display_name[:60]}")
    print(f"    → {state_str}")

def main():
    update_all  = "--all"     in sys.argv
    do_disable  = "--disable" in sys.argv
    do_enable   = "--enable"  in sys.argv
    freq_args   = [a for a in sys.argv[1:] if not a.startswith("-")]

    if not do_disable and not do_enable and not freq_args:
        print("Usage: python update_rule_frequency.py <frequency> [--all]")
        print("       python update_rule_frequency.py --disable [--all]")
        print("       python update_rule_frequency.py --enable  [--all]")
        print("  e.g. PT5M --all     (force all SOC Lab rules to fire)")
        print("  e.g. PT1H --all     (reset all to normal cadence)")
        print("  e.g. --disable --all  (stop rules from firing)")
        print("  e.g. --enable  --all  (re-enable rules before re-seeding)")
        sys.exit(1)

    subscription_id = discover_subscription_id()
    workspace_name  = discover_workspace_name()
    print(f"Subscription : {subscription_id}")
    print(f"Workspace    : {workspace_name}")

    base_url = (
        f"https://management.azure.com/subscriptions/{subscription_id}"
        f"/resourceGroups/{RESOURCE_GROUP}"
        f"/providers/Microsoft.OperationalInsights/workspaces/{workspace_name}"
        f"/providers/Microsoft.SecurityInsights/alertRules"
        f"?api-version={API_VERSION}"
    )

    print("Fetching alert rules...")
    rules_json = az(["rest", "--method", "get", "--url", base_url])
    all_rules  = json.loads(rules_json)["value"]

    if update_all:
        targets = [
            r for r in all_rules
            if r.get("kind") == "Scheduled"
            and r["properties"].get("displayName", "").startswith(SOC_LAB_PREFIX)
        ]
    else:
        rule = next(
            (r for r in all_rules if RULE_KEYWORD in r["properties"].get("displayName", "")),
            None
        )
        if not rule:
            print(f"ERROR: No rule found containing '{RULE_KEYWORD}'.")
            sys.exit(1)
        targets = [rule]

    if do_disable:
        print(f"\nDisabling {len(targets)} SOC Lab rule(s)...\n")
        for rule in targets:
            set_rule_enabled(rule, False)
        print("\nDone. Rules will not fire until re-enabled.")
    elif do_enable:
        print(f"\nEnabling {len(targets)} SOC Lab rule(s)...\n")
        for rule in targets:
            set_rule_enabled(rule, True)
        print("\nDone. Rules are active.")
    else:
        new_frequency = freq_args[0].upper()
        print(f"\nUpdating {len(targets)} SOC Lab rule(s) → {new_frequency}\n")
        for rule in targets:
            update_rule(rule, new_frequency)
        print(f"\nDone. Rules will fire within the next {new_frequency} cycle.")

if __name__ == "__main__":
    main()
