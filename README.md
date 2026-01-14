# Looker Seed Embed Group

This project contains a script to seed tenant content for a Looker Embed Group. It automates the creation of the embed group folder via the cookieless session acquire API and supports both a single level embed group child folder structure and content synchronziation.

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

- `--external_group_id` (Required): ID for the embed group.
- `--subfolders`: List of subfolders to create within the Embed group folder (e.g., "Finance" "Marketing").
- `--source_dashboard_ids`: List of existing dashboard IDs to copy to the Embed group folder.
- `--lookml_dashboard_ids`: List of LookML Dashboard IDs to import to the Embed group folder.. **Pass '*' to import ALL LookML dashboards to the Embed group folder.**
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

**Import ALL LookML Dashboards to the Embed Group Shared folder:**

```bash
uv run main.py \
  --external_group_id "seed_group_01" \
  --lookml_dashboard_ids "*"
```
