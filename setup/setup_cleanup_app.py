"""
setup_cleanup_app.py
ONE-TIME SETUP: Creates an Azure AD app registration with Incident.ReadWrite.All
permission on the Microsoft Defender XDR API so cleanup_xdr_incidents.py can
programmatically resolve Defender-native incidents (jailbreak alerts, etc.)
that cannot be touched via the Sentinel ARM API or az rest user tokens.

WHY AN APP REGISTRATION IS NEEDED:
  The Defender XDR incidents API (api.security.microsoft.com) requires
  Incident.ReadWrite.All as an APPLICATION permission — it is not available
  as a delegated/user permission. User tokens from az CLI cannot acquire it.
  An app registration + client secret + client credentials flow is the only
  supported path.

WHAT THIS SCRIPT DOES:
  1. Creates an Azure AD app registration "SOC Lab — XDR Cleanup"
  2. Looks up the Incident.ReadWrite.All permission ID on WindowsDefenderATP
  3. Adds the permission to the app
  4. Grants admin consent (requires Global Administrator or App Admin role)
  5. Creates a client secret (1 year)
  6. Writes credentials to .soclab_xdr_creds.json (gitignored, stays local)

Run this ONCE per tenant. Then use cleanup_xdr_incidents.py for routine cleanup.

Usage:
  python setup_cleanup_app.py

Requires:
  - az CLI signed in with Global Administrator or Application Administrator
    (Owner on the subscription is NOT sufficient for AAD app creation + consent)
"""

import subprocess
import json
import sys
import os

# ── Lab config ────────────────────────────────────────────────────────────────
TENANT_ID       = None   # resolved at runtime from az account show
APP_DISPLAY_NAME = "SOC Lab — XDR Cleanup"
CREDS_FILE       = os.path.join(os.path.dirname(__file__), ".soclab_xdr_creds.json")

# Known resource app IDs that may host Incident.ReadWrite.All.
# The correct one varies by tenant configuration / Defender SKU.
# The script tries each in order and uses the first match.
DEFENDER_RESOURCE_APP_IDS = [
    "fc780465-2017-40d4-a0c5-307022471b92",  # WindowsDefenderATP (Defender for Endpoint)
    "8ee8fdad-f234-4243-8f3b-15c294843740",  # Microsoft Threat Protection (M365 Defender)
]
PERMISSION_NAME = "Incident.ReadWrite.All"
# ─────────────────────────────────────────────────────────────────────────────


def az(args, check=True):
    result = subprocess.run(["az"] + args, capture_output=True, text=True, shell=True)
    if check and result.returncode != 0:
        print(f"  ERROR: {result.stderr.strip()}")
        sys.exit(1)
    return result.stdout.strip()


def az_json(args):
    return json.loads(az(args))


def main():
    print("=" * 65)
    print("SOC Lab — XDR Cleanup App Registration Setup")
    print("=" * 65)

    # Resolve tenant ID at runtime
    global TENANT_ID
    TENANT_ID = az(["account", "show", "--query", "tenantId", "-o", "tsv"])
    print(f"\nTenant ID: {TENANT_ID}")

    # ── Step 1: Check for existing app ───────────────────────────────────────
    print(f"\n[1/6] Checking for existing app '{APP_DISPLAY_NAME}' ...")
    existing = az([
        "ad", "app", "list",
        "--display-name", APP_DISPLAY_NAME,
        "--query", "[0].{appId:appId, id:id}",
        "--output", "json"
    ])
    existing = json.loads(existing) if existing and existing != "null" else None

    if existing and existing.get("appId"):
        app_id  = existing["appId"]
        obj_id  = existing["id"]
        print(f"  Found existing app: {app_id} (will reuse)")
    else:
        # ── Step 2: Create app ────────────────────────────────────────────────
        print(f"\n[2/6] Creating app registration '{APP_DISPLAY_NAME}' ...")
        app = az_json([
            "ad", "app", "create",
            "--display-name", APP_DISPLAY_NAME,
            "--query", "{appId:appId, id:id}",
            "--output", "json"
        ])
        app_id = app["appId"]
        obj_id = app["id"]
        print(f"  Created: {app_id}")

    # ── Step 3: Create / verify service principal ─────────────────────────────
    print(f"\n[3/6] Ensuring service principal exists ...")
    sp_check = az([
        "ad", "sp", "list",
        "--filter", f"appId eq '{app_id}'",
        "--query", "[0].id",
        "--output", "tsv"
    ])
    if not sp_check:
        az(["ad", "sp", "create", "--id", app_id])
        print(f"  Service principal created.")
    else:
        print(f"  Already exists.")

    # ── Step 4: Add Incident.ReadWrite.All permission ─────────────────────────
    print(f"\n[4/6] Finding {PERMISSION_NAME} permission ...")

    resource_app_id = None
    perm_id         = None

    for candidate in DEFENDER_RESOURCE_APP_IDS:
        print(f"  Trying resource app {candidate} ...")
        result = subprocess.run(
            ["az", "ad", "sp", "show",
             "--id", candidate,
             "--query", f"appRoles[?value=='{PERMISSION_NAME}'].id | [0]",
             "--output", "tsv"],
            capture_output=True, text=True, shell=True
        )
        pid = result.stdout.strip()
        if pid:
            resource_app_id = candidate
            perm_id         = pid
            print(f"  Found on {candidate}: {perm_id}")
            break
        else:
            print(f"    Not found (SP may not exist in this tenant, or no match).")

    if not perm_id:
        # Last resort: search ALL service principals for the permission
        print(f"\n  Searching all service principals for '{PERMISSION_NAME}' ...")
        result = subprocess.run(
            ["az", "ad", "sp", "list", "--all",
             "--query",
             f"[?appRoles[?value=='{PERMISSION_NAME}']].{{appId:appId, name:displayName}}",
             "--output", "json"],
            capture_output=True, text=True, shell=True
        )
        matches = json.loads(result.stdout or "[]")
        if matches:
            print("  Found the permission on these apps:")
            for m in matches:
                print(f"    {m['appId']}  —  {m['name']}")
            print(
                "\n  Add the correct appId to DEFENDER_RESOURCE_APP_IDS in this script and re-run."
            )
        else:
            print(
                "\n  ERROR: Could not find Incident.ReadWrite.All on any service principal.\n"
                "  This usually means Defender XDR is not fully provisioned in this tenant,\n"
                "  or the app requires a license (Defender for Office 365 P2 / M365 E5).\n"
                "  As a fallback, grant the permission manually via the Azure portal:\n"
                f"  https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/"
                f"ApplicationMenuBlade/~/CallAnAPI/appId/{app_id}"
            )
        sys.exit(1)

    az([
        "ad", "app", "permission", "add",
        "--id", obj_id,
        "--api", resource_app_id,
        "--api-permissions", f"{perm_id}=Role"
    ])
    print("  Permission added.")

    # ── Step 5: Grant admin consent ───────────────────────────────────────────
    print(f"\n[5/6] Granting admin consent (requires Global Admin or App Admin) ...")
    result = subprocess.run(
        ["az", "ad", "app", "permission", "admin-consent", "--id", obj_id],
        capture_output=True, text=True, shell=True
    )
    if result.returncode != 0:
        print(f"  WARNING: Admin consent failed: {result.stderr.strip()}")
        print("  You may need to grant consent manually:")
        print(f"  https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/CallAnAPI/appId/{app_id}")
        print("  (Grant admin consent from the API permissions blade)")
    else:
        print("  Admin consent granted.")

    # ── Step 6: Create client secret ─────────────────────────────────────────
    print(f"\n[6/6] Creating client secret ...")
    secret = az_json([
        "ad", "app", "credential", "reset",
        "--id", obj_id,
        "--append",
        "--display-name", "soclab-cleanup",
        "--years", "1",
        "--output", "json"
    ])
    client_secret = secret.get("password") or secret.get("secretText")
    if not client_secret:
        print(f"  ERROR: Could not extract client secret from: {secret}")
        sys.exit(1)
    print("  Client secret created (1 year).")

    # ── Write credentials file ────────────────────────────────────────────────
    creds = {
        "tenantId":     TENANT_ID,
        "clientId":     app_id,
        "clientSecret": client_secret,
        "_note":        "Created by setup_cleanup_app.py. Do not commit to source control."
    }
    with open(CREDS_FILE, "w", encoding="utf-8") as f:
        json.dump(creds, f, indent=2)
    print(f"\nCredentials written to: {CREDS_FILE}")

    print(
        "\n" + "=" * 65 + "\n"
        "Setup complete.\n\n"
        "Next: run cleanup_xdr_incidents.py to resolve Defender XDR incidents.\n\n"
        "IMPORTANT: .soclab_xdr_creds.json contains a client secret.\n"
        "  - Do not commit it to git.\n"
        "  - Add it to .gitignore if you haven't already.\n"
    )


if __name__ == "__main__":
    main()
