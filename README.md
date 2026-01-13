# Looker Seed Embed Group

This project contains a script to seed tenant content for a Looker Embed Group. It automates the creation of embed user sessions, group folder structure, and content migration.

## Prerequisites

- Python 3.13+
- `uv` package manager
- Looker API credentials (Client ID and Secret)
- Looker Instance URL

## Setup

1.  **Dependencies**: Install dependencies using `uv`.

    ```bash
    uv sync
    ```

2.  **Environment Variables**: Set the following environment variables (or use `looker.ini`).
    ```bash
    export LOOKERSDK_BASE_URL="https://your-instance.looker.com"
    export LOOKERSDK_CLIENT_ID="your_client_id"
    export LOOKERSDK_CLIENT_SECRET="your_client_secret"
    ```

## Usage

Run the script using `uv run main.py`.

### Arguments

- `--external_user_id` (Required): ID for the dummy embed user.
- `--external_group_id` (Required): ID for the embed group.
- `--subfolders`: List of subfolders to create (e.g., "Finance" "Marketing"). Default: "Subfolder A" "Subfolder B".
- `--source_dashboard_ids`: List of existing dashboard IDs to copy to the group's folder.
- `--lookml_dashboard_ids`: List of LookML Dashboard IDs to import to the **Embed Group Root**. **Pass '*' to import ALL LookML dashboards to the root.**
- `--source_dashboard_mapping`: Pairs of `dashboard_id:subfolder_name` (e.g., "123:Finance").
- `--lookml_dashboard_mapping`: Pairs of `lookml_id:subfolder_name` (e.g., "model::dash:Marketing").

### Examples

**Basic Usage:**

```bash
uv run main.py --external_group_id "seed_group_01"
```

**Mapped Dashboards and Custom Subfolders:**

```bash
uv run main.py \
  --external_group_id "seed_group_01" \
  --subfolders "General" \
  --source_dashboard_mapping "123:Finance" "456:Finance" \
  --lookml_dashboard_mapping "model::dash1:Marketing"
```
*Creates "General", "Finance", and "Marketing" folders. Copies dash 123/456 to Finance, imports dash1 to Marketing.*

**Import ALL LookML Dashboards to Root:**

```bash
uv run main.py \
  --external_group_id "seed_group_01" \
  --lookml_dashboard_ids "*"
```
