# CosmosDB Monitor - Usage Guide

## Quick Start

Run the monitor script:
```bash
python monitor_cosmosdb.py
```

The script will:
- Connect to CosmosDB using credentials from `local_data.json`
- Display documents from the last 24 hours
- Update every 30 seconds
- Show alarm status for each document

## Features

- ✅ Auto-detects timestamp fields (`_ts`, `_id`, `timestamp`, etc.)
- ✅ Shows alarm status (🔴 ALARM ACTIVE / 🟢 OK)
- ✅ Displays key fields from each document
- ✅ Refreshes every 30 seconds
- ✅ Handles connection errors gracefully

## Before Running

1. **Update Collection Name** (if needed):
   - Edit `local_data.json`
   - Change `"cosmos_collection": "YourCollectionName"` to your actual collection name
   - Or the script will prompt you when you run it

2. **Verify Connection String**:
   - The script uses `mongodb_connection_string` from `local_data.json`
   - Should be in format: `mongodb://secomeadb:KEY@secomeadb.documents.azure.com:10255/...`

## Example Output

```
================================================================================
COSMOSDB MONITOR - Last 24 Hours
Database: secomeadb | Collection: YourCollectionName
Alarm Field: Test2OPCUA:CommonAlarm
Last Update: 2025-11-13 15:30:45
================================================================================

📊 Found 5 document(s)

────────────────────────────────────────────────────────────────────────────────
Document #1
────────────────────────────────────────────────────────────────────────────────
Timestamp: 2025-11-13 14:25:30 UTC
Alarm Status (Test2OPCUA:CommonAlarm): 0 🟢 OK

Other Fields:
  field1: value1
  field2: value2
  ...

────────────────────────────────────────────────────────────────────────────────
🔄 Refreshing every 30 seconds... (Press Ctrl+C to stop)
```

## Troubleshooting

### Error: "No documents found"
- Check that `COSMOS_COLLECTION` is set to the correct collection name
- Verify documents exist in the collection
- Check that documents have timestamps within the last 24 hours

### Error: "Connection failed"
- Verify `mongodb_connection_string` in `local_data.json` is correct
- Check network connectivity
- Verify CosmosDB account is accessible

### Collection name prompt
- If you see the prompt, enter your actual collection name
- Or update `local_data.json` before running

## Stop the Monitor

Press `Ctrl+C` to stop the monitoring script.

