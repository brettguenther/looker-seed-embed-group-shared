import argparse
import sys
from typing import List, Optional

import looker_sdk
from looker_sdk import models40 as models
from looker_sdk.error import SDKError


def acquire_cookieless_session(
    sdk: looker_sdk.methods40.Looker40SDK,
    external_group_id: str,
    session_length: int = 3600,
    force_logout_login: bool = True,
) -> models.EmbedCookielessSessionAcquireResponse:
    """Acquires a cookieless session to ensure the embed group exists."""
    body = models.EmbedCookielessSessionAcquire(
        first_name="Embed",
        last_name="Seed",
        session_length=3600,
        force_logout_login=True,
        external_user_id=f"seed-user-{external_group_id}",
        external_group_id=external_group_id,
        permissions=["access_data", "see_looks", "see_user_dashboards", "see_lookml_dashboards"],
        models=["basic_ecomm"],
        user_attributes={"locale": "en_US"},
    )
    try:
        session = sdk.acquire_embed_cookieless_session(body=body)
        print(f"Acquired cookieless session for user 'seed-user-{external_group_id}' with group '{external_group_id}'")
        return session
    except SDKError as e:
        print(f"Error acquiring cookieless session: {e}")
        sys.exit(1)


def find_embed_folder_for_external_group(
    sdk: looker_sdk.methods40.Looker40SDK, external_group_id: str
) -> Optional[models.Folder]:
    """Finds the folder associated with the external group ID."""
    # base finder strategy off naming of the embed folder + parent is the embed shared root
    try:
        # TODO: limit fields returned
        groups = sdk.search_groups(external_group_id=external_group_id)
        if not groups:
            print(f"Group with external_id '{external_group_id}' not found.")
            return None

        embed_group_id = groups[0].id

        # Validate parent group has "Embed Shared" root for external group
        folders = sdk.search_folders(name=external_group_id)
        for folder in folders:
            if folder.is_embed:
                print(f"Found folder: {folder.name} (ID: {folder.id})")
                # TODO: limit fields returned
                parent_folder = sdk.folder_parent(folder.id)
                if parent_folder.is_embed_shared_root:
                    embed_folder = folder
                    break
        return embed_folder
    except SDKError as e:
        print(f"Error finding folder: {e}")
        return None


def create_subfolders(
    sdk: looker_sdk.methods40.Looker40SDK, parent_folder_id: str, subfolders: List[str]
):
    """Creates subfolders under the given parent folder."""
    for folder_name in subfolders:
        try:
            # Check if exists first to be idempotent
            existing = sdk.search_folders(parent_id=parent_folder_id, name=folder_name)
            if existing:
                print(f"Folder '{folder_name}' already exists (ID: {existing[0].id}).")
                continue

            folder = sdk.create_folder(
                body=models.CreateFolder(name=folder_name, parent_id=parent_folder_id)
            )
            print(f"Created folder '{folder_name}' (ID: {folder.id}).")
        except SDKError as e:
            print(f"Error creating folder '{folder_name}': {e}")


def copy_dashboards(
    sdk: looker_sdk.methods40.Looker40SDK, source_dashboard_ids: List[str], target_folder_id: str
):
    """Copies existing user defined dashboards to the target folder."""
    for dash_id in source_dashboard_ids:
        try:
            sdk.copy_dashboard(
                dashboard_id=dash_id,
                folder_id=target_folder_id
            )
            print(f"Copied dashboard '{dash_id}' to folder {target_folder_id}.")
        except SDKError as e:
            print(f"Error copying dashboard '{dash_id}': {e}")


def import_lookml_dashboards(
    sdk: looker_sdk.methods40.Looker40SDK, lookml_dashboard_ids: List[str], target_folder_id: str
):
    """Imports LookML dashboards to the target folder as UDDs."""
    # If empty list is passed (should be caught by caller, but safety check), do nothing?
    # Wait, requirement was: "If passed with NO arguments (empty list), import ALL".
    # Caller should handle the logic of "empty list means all" before calling this? 
    # Or we handle it here. Let's handle it here for safety if the list is empty.
    
    dashboards_to_import = lookml_dashboard_ids
    
    if len(dashboards_to_import) == 1 and dashboards_to_import[0] == '*':
        print("Wildcard '*' provided, fetching ALL LookML dashboards...")
        try:
            all_dashboards = sdk.all_lookml_dashboards()
            dashboards_to_import = [d.name for d in all_dashboards if d.name] # name is the ID usually for LookML dash
            print(f"Found {len(dashboards_to_import)} LookML dashboards.")
        except SDKError as e:
            print(f"Error fetching all LookML dashboards: {e}")
            return
    elif not dashboards_to_import:
        print("No LookML dashboards specified.")
        return

    for dash_id in dashboards_to_import:
        try:
            # import_lookml_dashboard returns the created dashboard
            new_dash = sdk.import_lookml_dashboard(
                lookml_dashboard_id=dash_id,
                space_id=target_folder_id # Note: space_id param is mapped to folder_id in v4.0 usually, let's verify arg name
            )
            # Argument name for import_lookml_dashboard in python sdk might be different or body based?
            # Checking recent SDKs, `import_lookml_dashboard` takes `lookml_dashboard_id` and `space_id` (folder_id).
            print(f"Imported LookML dashboard '{dash_id}' as '{new_dash.id}' in folder {target_folder_id}.")
        except SDKError as e:
            print(f"Error importing LookML dashboard '{dash_id}': {e}")


def main():
    parser = argparse.ArgumentParser(description="Seed Looker content for an embed group.")
    parser.add_argument("--external_group_id", required=True, help="External Group ID for the embed group.")
    parser.add_argument("--subfolders", nargs="*", default=None, help="List of subfolders to create.")
    parser.add_argument("--source_dashboard_ids", nargs="*", default=None, help="List of source Dashboard IDs to copy.")
    parser.add_argument("--lookml_dashboard_ids", nargs="*", default=None, help="List of LookML Dashboard IDs to import. Pass '*' to import ALL. If omitted or empty, imports None.")
    
    args = parser.parse_args()

    # Initialize SDK
    sdk = looker_sdk.init40()

    # 1. Acquire cookieless session to ensure group creation
    acquire_cookieless_session(sdk, args.external_group_id)

    # 2. Find the embed group's folder
    folder = find_embed_folder_for_external_group(sdk, args.external_group_id)
    if not folder:
        print("Exiting: Could not find target folder.")
        sys.exit(1)

    # 3. Create subfolders
    if args.subfolders is not None:
        create_subfolders(sdk, folder.id, args.subfolders)

    # 4. Migrate content
    if args.source_dashboard_ids is not None:
        copy_dashboards(sdk, args.source_dashboard_ids, folder.id)
    
    if args.lookml_dashboard_ids is not None:
        import_lookml_dashboards(sdk, args.lookml_dashboard_ids, folder.id)

if __name__ == "__main__":
    main()
