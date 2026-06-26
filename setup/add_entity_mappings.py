"""
add_entity_mappings.py
Creates or patches the SOC Lab cross-layer attack analytics rule in Sentinel.

Behaviour:
  - If the rule already exists  → patches it (entity mappings, query, tactics, suppression)
  - If the rule does not exist  → creates it from scratch with a deterministic rule ID
  Running this script multiple times is safe and idempotent.

Usage:
  python add_entity_mappings.py

Requires: az CLI signed in with Owner access to the subscription.
"""

import subprocess
import json
import sys
import tempfile
import os
import uuid

# ── Lab config ────────────────────────────────────────────────────────────────
RESOURCE_GROUP = "rg-soclab"
RULE_KEYWORD   = "cross-layer"
API_VERSION    = "2023-02-01"
# ─────────────────────────────────────────────────────────────────────────────

DISPLAY_NAME = "SOC Lab — cross-layer attack"

# Look back 4 hours to capture events whether the rule fires immediately after
# seeding or up to 2 hours later. Column names include _s suffix because the
# table is populated via the Log Analytics HTTP Data Collector API, which
# automatically appends type suffixes to all custom string columns.
UPDATED_QUERY = """let lookback = 4h;
let attack = SocLabEvents_CL
    | where TimeGenerated > ago(lookback)
    | where Stage_s !startswith "noise";
let chainAccounts = attack
    | summarize StageCount = dcount(Stage_s) by Account_s
    | where StageCount >= 3
    | project Account_s;
attack
| where Account_s in (chainAccounts)
| project
    TimeGenerated,
    Stage            = Stage_s,
    Account          = Account_s,
    SourceIP         = column_ifexists("SourceIP_s", ""),
    Device           = column_ifexists("Device_s", ""),
    Sender           = column_ifexists("Sender_s", ""),
    Recipient        = column_ifexists("Recipient_s", ""),
    NetworkMessageId = column_ifexists("NetworkMessageId_s", ""),
    AzureResourceId  = column_ifexists("AzureResourceId_s", ""),
    ServicePrincipal = column_ifexists("ServicePrincipal_s", "")"""

TACTICS = [
    "InitialAccess",
    "CredentialAccess",
    "Execution",
    "LateralMovement",
    "Persistence"
]

ENTITY_MAPPINGS = [
    {
        "entityType": "Account",
        "fieldMappings": [
            {"identifier": "FullName", "columnName": "Account"}
        ]
    },
    {
        "entityType": "Account",
        "fieldMappings": [
            {"identifier": "Name", "columnName": "ServicePrincipal"}
        ]
    },
    {
        "entityType": "Host",
        "fieldMappings": [
            {"identifier": "HostName", "columnName": "Device"}
        ]
    },
    {
        "entityType": "AzureResource",
        "fieldMappings": [
            {"identifier": "ResourceId", "columnName": "AzureResourceId"}
        ]
    },
    {
        "entityType": "MailMessage",
        "fieldMappings": [
            {"identifier": "Recipient", "columnName": "Recipient"},
            {"identifier": "Sender", "columnName": "Sender"},
            {"identifier": "NetworkMessageId", "columnName": "NetworkMessageId"}
        ]
    }
]

RULE_PROPERTIES = {
    "displayName":          DISPLAY_NAME,
    "description":          "Correlates the seeded cross-layer attack stages into one incident, emitting per-stage entities (user, attacker IP, phishing email, AI resource, service principal, endpoint).",
    "enabled":              True,
    "severity":             "Medium",
    "query":                UPDATED_QUERY,
    "queryFrequency":       "PT1H",
    "queryPeriod":          "PT4H",
    "triggerOperator":      "GreaterThan",
    "triggerThreshold":     0,
    "suppressionEnabled":   True,
    "suppressionDuration":  "PT24H",
    "incidentConfiguration": {"createIncident": True},
    "eventGroupingSettings": {"aggregationKind": "SingleAlert"},
    "entityMappings":       ENTITY_MAPPINGS,
    "tactics":              TACTICS,
    "techniques":           []
}


def az(args, check=True):
    result = subprocess.run(["az"] + args, capture_output=True, text=True, shell=True)
    if check and result.returncode != 0:
        print(f"ERROR: {result.stderr.strip()}")
        sys.exit(1)
    return result.stdout.strip()


def discover_subscription_id():
    """Discover the active subscription ID at runtime — avoids hardcoding."""
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


def put_rule(rule_body, rule_resource_id):
    put_url = f"https://management.azure.com{rule_resource_id}?api-version={API_VERSION}"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(rule_body, f)
        temp_path = f.name
    try:
        response = az([
            "rest", "--method", "put",
            "--url", put_url,
            "--body", f"@{temp_path}",
            "--headers", "Content-Type=application/json"
        ])
        return json.loads(response)
    finally:
        os.unlink(temp_path)


def print_result(updated):
    props = updated["properties"]
    mappings   = props.get("entityMappings", [])
    tactics    = props.get("tactics", [])
    severity   = props.get("severity", "?")
    suppressed = props.get("suppressionEnabled", False)
    print(f"  Display name : {props.get('displayName')}")
    print(f"  Severity     : {severity}")
    print(f"  Tactics      : {tactics}")
    print(f"  Entities     : {[m['entityType'] for m in mappings]}")
    print(f"  Suppression  : {'enabled (PT24H)' if suppressed else 'disabled'}")
    print("\nNext steps:")
    print("1. Run: python setup_noise_rules.py")
    print("2. Run: python setup_cleanup_app.py")


def main():
    print("=" * 60)
    print("SOC Lab — Add Entity Mappings to Analytics Rule")
    print("=" * 60)

    subscription_id = discover_subscription_id()
    workspace_name = discover_workspace_name()
    print(f"Subscription : {subscription_id}")
    print(f"Workspace    : {workspace_name}")

    workspace_resource_id = (
        f"/subscriptions/{subscription_id}/resourceGroups/{RESOURCE_GROUP}"
        f"/providers/Microsoft.OperationalInsights/workspaces/{workspace_name}"
    )
    rule_id = str(uuid.uuid5(uuid.NAMESPACE_URL, workspace_resource_id + "/soclab-crosslayer"))

    base_url = (
        f"https://management.azure.com{workspace_resource_id}"
        f"/providers/Microsoft.SecurityInsights/alertRules"
        f"?api-version={API_VERSION}"
    )

    print("Fetching alert rules...")
    rules_json = az(["rest", "--method", "get", "--url", base_url])
    rules = json.loads(rules_json)["value"]

    existing = next(
        (r for r in rules if RU