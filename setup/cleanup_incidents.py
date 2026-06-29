"""
cleanup_incidents.py
Deletes all SOC Lab incidents from Microsoft Sentinel so the environment
is clean for re-seeding.

Targets two categories of incident:
  1. Any incident whose title contains "SOC Lab" (the main attack + jailbreak incidents)
  2. Any incident tagged with the label "SocLabNoise" (created by seed_noise_incidents.py)

NOTE: This script intentionally does NOT purge the SocLabEvents_CL table.
Purging a custom table via the Log Analytics purge API locks the table against
new ingestion until the async purge completes (which can take hours). For
per-student lab tenants each tenant starts empty, so purge is never needed.
For re-seeding an existing tenant, deleting incidents is sufficient — old
events in the table are just background noise and do not affect the lab.

Run this BEFORE running seed_events.py.

Usage:
  python cleanup_incidents.py              # deletes matching incidents
  python cleanup_incidents.py --dry-run   # lists what would be deleted, no changes

Requires: az CLI signed in with Owner access to the subscription.
"""

import subprocess
import json
import sys
import argparse
import time

# ── Lab config ────────────────────────────────────────────────────────────────
RESOURCE_GROUP   = "rg-soclab"
INCIDENT_FILTER  = "SOC Lab"      # delete any incident whose title contains this
NOISE_LABEL      = "SocLabNoise"  # delete any incident with this label (noise incidents)
SENTINEL_API     = "2023-02-01"
# ─────────────────────────────────────────────────────────────────────────────


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


def list_incidents(sentinel_base):
    """Return Sentinel incidents (single page, up to 200 — sufficient for lab use).
    Pagination is intentionally skipped: nextLink URLs contain &$skipToken which
    Windows cmd.exe misinterprets as a command separator when shell=True."""
    url = f"{sentinel_base}/incidents?api-version={SENTINEL_API}"
    raw  = az(["rest", "--method", "get", "--url", url])
    data = json.loads(raw)
    return data.get("value", [])


def is_target(incident):
    """Return True if this incident should be deleted."""
    title  = incident["properties"].get("title", "")
    labels = [l.get("labelName", "") for l in incident["properties"].get("labels", [])]
    return INCIDENT_FILTER in title or NOISE_LABEL in labels


def delete_incident(incident_id, sentinel_base, dry_run, retries=3):
    url = f"{sentinel_base}/incidents/{incident_id}?api-version={SENTINEL_API}"
    if dry_run:
        print(f"    [dry-run] would DELETE {incident_id}")
        return
    for attempt in range(1, retries + 1):
        result = subprocess.run(
            ["az", "rest", "--method", "delete", "--url", url],
            capture_output=True, text=True, shell=True
        )
        if result.returncode == 0:
            print(f"    Deleted {incident_id}")
            return
        if attempt < retries:
            print(f"    Attempt {attempt} failed — retrying in 3s ...")
            time.sleep(3)
        else:
            print(f"    ERROR after {retries} attempts: {result.stderr.strip()[:120]}")


def main():
    parser = argparse.ArgumentParser(description="Clean up SOC Lab seeded incidents.")
    parser.add_argument("--dry-run", action="store_true", help="List targets without deleting")
    args = parser.parse_args()

    dry  = args.dry_run
    mode = "[DRY RUN] " if dry else ""

    subscription_id = discover_subscription_id()
    workspace_name = discover_workspace_name()
    sentinel_base = (
        f"https://management.azure.com/subscriptions/{subscription_id}"
        f"/resourceGroups/{RESOURCE_GROUP}"
        f"/providers/Microsoft.OperationalInsights/workspaces/{workspace_name}"
        f"/providers/Microsoft.SecurityInsights"
    )

    print("=" * 60)
    print(f"SOC Lab — {mode}Incident Cleanup")
    print(f"Workspace: {workspace_name}")
    print("=" * 60)

    # Loop until no targets remain. Each pass fetches one page (newest-first);
    # after deleting those, the next pass picks up older incidents that were
    # previously hidden on page 2+. Avoids $skipToken pagination issues on Windows.
    total_deleted = 0
    pass_num = 0
    while True:
        pass_num += 1
        print(f"\n[Pass {pass_num}] Fetching Sentinel incidents...")
        incidents = list_incidents(sentinel_base)
        targets   = [i for i in incidents if is_target(i)]

        if not targets:
            if pass_num == 1:
                print(f"  No incidents found matching filter '{INCIDENT_FILTER}' or label '{NOISE_LABEL}'.")
            else:
                print(f"  No more matching incidents — cleanup complete.")
            break

        soc_lab = [i for i in targets if INCIDENT_FILTER in i["properties"].get("title", "")]
        noise   = [i for i in targets if NOISE_LABEL in [l.get("labelName","") for l in i["properties"].get("labels", [])]]

        print(f"  Found {len(targets)} incident(s) to delete "
              f"({len(soc_lab)} SOC Lab, {len(noise)} noise):")
        for inc in targets:
            title    = inc["properties"]["title"]
            inc_id   = inc["name"]
            severity = inc["properties"].get("severity", "?")
            status   = inc["properties"].get("status", "?")
            print(f"    • [{severity:13s} / {status}] {title}  (id: {inc_id[:8]}...)")

        if dry:
            # In dry-run, just show the first page and stop
            break

        print("\n  Deleting...")
        for i, inc in enumerate(targets):
            delete_incident(inc["name"], sentinel_base, dry)
            if i < len(targets) - 1:
                time.sleep(2.0)   # avoid Azure management API rate limiting
        total_deleted += len(targets)
        print(f"  Pass {pass_num} complete — {total_deleted} deleted so far.")

        # Brief pause before re-listing so Azure has time to reflect deletions
        time.sleep(3.0)

    print("\nDone.")
    if not dry:
        print(f"  Total deleted: {total_deleted}")
        if total_deleted > 0:
            print(
                "\nNext steps:\n"
                "  1. Run seed_events.py (or seed_events.ps1) to inject fresh attack events.\n"
                "  2. Run seed_ai_attacks.py to trigger the Defender for Cloud jailbreak alert.\n"
                "  3. Run update_rule_frequency.py PT5M --all to force all rules to fire.\n"
                "  4. Wait ~10-30 min, verify incidents in the Defender portal.\n"
                "  5. Run update_rule_frequency.py PT1H --all to reset rule cadence.\n"
                "\nNOTE: Noise incidents are now created by analytics rules (setup_noise_rules.py),\n"
                "  not by seed_noise_incidents.py. No separate noise seeding step needed."
            )


if __name__ == "__main__":
    main()
