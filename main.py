import argparse
import sys
from typing import List, Optional, Dict, Union

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
    try:
        # Validate parent group has "Embed Shared" root for external group
        folders = sdk.search_folders(name=external_group_id)
        embed_folder = None
        for folder in folders:
            if folder.is_embed:
                # print(f"Found folder: {folder.name} (ID: {folder.id})")
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
) -> Dict[str, str]:
    """Creates subfolders under the given parent folder and returns a map of name -> id."""
    folder_map = {}
    for folder_name in subfolders:
        try:
            # Check if exists first to be idempotent
            existing = sdk.search_folders(parent_id=parent_folder_id, name=folder_name)
            if existing:
                print(f"Folder '{folder_name}' already exists (ID: {existing[0].id}).")
                folder_map[folder_name] = existing[0].id
                continue

            folder = sdk.create_folder(
                body=models.CreateFolder(name=folder_name, parent_id=parent_folder_id)
            )
            print(f"Created folder '{folder_name}' (ID: {folder.id}).")
            folder_map[folder_name] = folder.id
        except SDKError as e:
            print(f"Error creating folder '{folder_name}': {e}")
    return folder_map


def copy_dashboards(
    sdk: looker_sdk.methods40.Looker40SDK, 
    source_dashboard_ids: List[str], 
    target_folder_id: str,
    dashboard_mapping: Optional[Dict[str, str]] = None
):
    """Copies existing user defined dashboards to the target folder(s)."""
    # 1. Copy unmapped dashboards to root
    for dash_id in source_dashboard_ids:
        try:
            sdk.copy_dashboard(
                dashboard_id=dash_id,
                folder_id=target_folder_id
            )
            print(f"Copied dashboard '{dash_id}' to root folder {target_folder_id}.")
        except SDKError as e:
            print(f"Error copying dashboard '{dash_id}': {e}")

    # 2. Copy mapped dashboards
    if dashboard_mapping:
        for dash_id, folder_id in dashboard_mapping.items():
            try:
                sdk.copy_dashboard(
                    dashboard_id=dash_id,
                    folder_id=folder_id
                )
                print(f"Copied dashboard '{dash_id}' to folder {folder_id}.")
            except SDKError as e:
                print(f"Error copying dashboard '{dash_id}' to mapped folder: {e}")


def import_lookml_dashboards(
    sdk: looker_sdk.methods40.Looker40SDK, 
    lookml_dashboard_ids: List[str], 
    target_folder_id: str,
    dashboard_mapping: Optional[Dict[str, str]] = None
):
    """Imports LookML dashboards to the target folder(s) as UDDs."""
    
    dashboards_to_import = lookml_dashboard_ids
    
    # Handle wildcard or empty list for MAIN list
    if len(dashboards_to_import) == 1 and dashboards_to_import[0] == '*':
        print("Wildcard '*' provided, fetching ALL LookML dashboards...")
        try:
            all_dashboards = sdk.all_lookml_dashboards()
            dashboards_to_import = [d.name for d in all_dashboards if d.name]
            print(f"Found {len(dashboards_to_import)} LookML dashboards.")
        except SDKError as e:
            print(f"Error fetching all LookML dashboards: {e}")
            return # Don't process wildcard if fetch fails

    # 1. Import unmapped dashboards to root
    if dashboards_to_import:
        for dash_id in dashboards_to_import:
            try:
                new_dash = sdk.import_lookml_dashboard(
                    lookml_dashboard_id=dash_id,
                    space_id=target_folder_id
                )
                print(f"Imported LookML dashboard '{dash_id}' as '{new_dash.id}' in root folder {target_folder_id}.")
            except SDKError as e:
                print(f"Error importing LookML dashboard '{dash_id}': {e}")

    # 2. Import mapped dashboards
    if dashboard_mapping:
        for dash_id, folder_id in dashboard_mapping.items():
            try:
                new_dash = sdk.import_lookml_dashboard(
                    lookml_dashboard_id=dash_id,
                    space_id=folder_id
                )
                print(f"Imported LookML dashboard '{dash_id}' as '{new_dash.id}' in mapped folder {folder_id}.")
            except SDKError as e:
                print(f"Error importing LookML dashboard '{dash_id}' to mapped folder: {e}")


def parse_mapping(mapping_args: Optional[List[str]]) -> Dict[str, str]:
    """Parses a list of 'id:name' strings into a dictionary {id: name}."""
    mapping = {}
    if not mapping_args:
        return mapping
    for item in mapping_args:
        if ':' in item:
            key, val = item.rsplit(':', 1)
            mapping[key.strip()] = val.strip()
        else:
            print(f"Warning: Invalid mapping format '{item}'. Expected 'id:folder_name'. Skipping.")
    return mapping


def main():
    parser = argparse.ArgumentParser(description="Seed Looker content for an embed group.")
    parser.add_argument("--external_group_id", required=True, help="External Group ID for the embed group.")
    parser.add_argument("--subfolders", nargs="*", default=None, help="List of subfolders to create.")
    parser.add_argument("--source_dashboard_ids", nargs="*", default=None, help="List of source Dashboard IDs to copy to root.")
    parser.add_argument("--lookml_dashboard_ids", nargs="*", default=None, help="List of LookML Dashboard IDs to import to root. Pass '*' to import ALL.")
    
    # New Mapping Arguments
    parser.add_argument("--source_dashboard_mapping", nargs="+", help="Map source dashboards to subfolders. Format: id:folder_name")
    parser.add_argument("--lookml_dashboard_mapping", nargs="+", help="Map LookML dashboards to subfolders. Format: id:folder_name")

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

    # 3. Resolve Folder Logic
    # Collect all unique folder names from args.subfolders AND mappings
    needed_subfolders = set()
    
    if args.subfolders:
        needed_subfolders.update(args.subfolders)
    
    source_mapping_raw = parse_mapping(args.source_dashboard_mapping)
    lookml_mapping_raw = parse_mapping(args.lookml_dashboard_mapping)
    
    needed_subfolders.update(source_mapping_raw.values())
    needed_subfolders.update(lookml_mapping_raw.values())

    # Create all needed subfolders
    folder_map_name_to_id = {}
    if needed_subfolders:
        print(f"Ensuring subfolders exist: {needed_subfolders}")
        folder_map_name_to_id = create_subfolders(sdk, folder.id, list(needed_subfolders))

    # Resolve mappings to use IDs instead of names
    source_mapping_ids = {}
    for dash_id, folder_name in source_mapping_raw.items():
        if folder_name in folder_map_name_to_id:
            source_mapping_ids[dash_id] = folder_map_name_to_id[folder_name]
        else:
             print(f"Warning: Folder '{folder_name}' for dashboard '{dash_id}' was not created. Skipping.")

    lookml_mapping_ids = {}
    for dash_id, folder_name in lookml_mapping_raw.items():
        if folder_name in folder_map_name_to_id:
            lookml_mapping_ids[dash_id] = folder_map_name_to_id[folder_name]
        else:
             print(f"Warning: Folder '{folder_name}' for LookML dashboard '{dash_id}' was not created. Skipping.")

    # 4. Migrate content
    # Pass both list (for root) and mapping (for subfolders)
    copy_dashboards(
        sdk, 
        args.source_dashboard_ids if args.source_dashboard_ids else [], 
        folder.id, 
        dashboard_mapping=source_mapping_ids
    )
    
    import_lookml_dashboards(
        sdk, 
        args.lookml_dashboard_ids if args.lookml_dashboard_ids else [], 
        folder.id,
        dashboard_mapping=lookml_mapping_ids
    )

if __name__ == "__main__":
    main()
