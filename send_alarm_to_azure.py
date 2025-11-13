"""
Send an alarm signal to CosmosDB that will trigger the Azure Function App
"""

import os
import json
from datetime import datetime
from pymongo import MongoClient
from urllib.parse import urlparse, unquote

# Load configuration
config_path = os.path.join(os.path.dirname(__file__), "local_data.json")
with open(config_path, 'r') as f:
    config = json.load(f)

MONGODB_CONNECTION_STRING = config.get("mongodb_connection_string")
COSMOS_DATABASE = config.get("cosmos_database", "IoTDatabase")
COSMOS_COLLECTION = config.get("cosmos_collection", "YourCollectionName")
ALARM_FIELD = config.get("alarm_field", "Test2OPCUA:CommonAlarm")

print("=" * 80)
print("Send Alarm Signal to CosmosDB")
print("=" * 80)
print(f"CosmosDB Account: secomeadb")
print(f"Database: {COSMOS_DATABASE}")
print(f"Collection: {COSMOS_COLLECTION}")
print(f"Alarm Field: {ALARM_FIELD}")
print()
print("NOTE: In Azure Portal, navigate to:")
print("  CosmosDB Account 'secomeadb' -> Data Explorer -> Database 'IoTDatabase' -> Collection 'YourCollectionName'")
print()

try:
    # Parse connection string
    parsed = urlparse(MONGODB_CONNECTION_STRING)
    username = unquote(parsed.username) if parsed.username else ""
    password = unquote(parsed.password) if parsed.password else ""
    host = parsed.hostname
    port = parsed.port or 10255
    
    # Connect to CosmosDB
    # Note: Connection string has "secomeadb" in URL but that's the account name
    # The actual database is "IoTDatabase" (or "secomeadb" - we'll try both)
    print("Connecting to CosmosDB...")
    
    # Try IoTDatabase first (from config)
    databases_to_try = [COSMOS_DATABASE, "secomeadb"]
    
    for db_name in databases_to_try:
        try:
            print(f"\nTrying database: {db_name}")
            client = MongoClient(
                host=host,
                port=port,
                username=username,
                password=password,
                authSource=db_name,
                tls=True,
                tlsAllowInvalidCertificates=True,
                retryWrites=False,
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=10000,
                socketTimeoutMS=10000
            )
            
            db = client[db_name]
            collection = db[COSMOS_COLLECTION]
            
            # Test by trying to find one document (lighter operation)
            try:
                sample = collection.find_one()
                print(f"  [OK] Successfully connected to {db_name}/{COSMOS_COLLECTION}")
                if sample:
                    print(f"  Found existing documents in collection")
            except:
                print(f"  [OK] Connected to {db_name}/{COSMOS_COLLECTION}")
            
            # Break out of loop - found working database
            break
        except Exception as e:
            print(f"  [FAILED] {e}")
            if db_name == databases_to_try[-1]:
                # Last database failed, raise error
                raise
            continue
    
    # Create alarm document with current timestamp (nanoseconds format)
    now = datetime.now()
    alarm_doc = {
        "timestamp": int(now.timestamp() * 1e9),  # Nanoseconds format
        ALARM_FIELD: 1,  # Alarm active
        "source": "manual_trigger",
        "created_at": now.isoformat(),
        "description": "Manual alarm trigger to test Azure Function App"
    }
    
    print(f"Inserting alarm document...")
    print(f"  Timestamp: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  {ALARM_FIELD}: 1 (ALARM ACTIVE)")
    print()
    
    # Insert document
    result = collection.insert_one(alarm_doc)
    
    print(f"\n[SUCCESS] Alarm document inserted!")
    print(f"  Document ID: {result.inserted_id}")
    print(f"  CosmosDB Account: secomeadb")
    print(f"  Database: {db_name}")
    print(f"  Collection: {COSMOS_COLLECTION}")
    print(f"  Timestamp: {alarm_doc['timestamp']}")
    print()
    print("=" * 80)
    print("Azure Function App will detect this alarm on its next check cycle")
    print("(Function runs every minute, so it should trigger within 1 minute)")
    print("=" * 80)
    print(f"\nTo verify in Azure Portal:")
    print(f"  1. Go to Azure Portal -> CosmosDB accounts")
    print(f"  2. Click on account: secomeadb")
    print(f"  3. Click 'Data Explorer' (left menu)")
    print(f"  4. Expand: {db_name} (database)")
    print(f"  5. Click on collection: {COSMOS_COLLECTION}")
    print(f"  6. Look for document with ID: {result.inserted_id}")
    print(f"     Or search for: Test2OPCUA:CommonAlarm = 1")
    print()
    print(f"Connection details:")
    print(f"  Endpoint: secomeadb.documents.azure.com (or secomeadb.mongo.cosmos.azure.com)")
    print(f"  Database: {db_name}")
    print(f"  Collection: {COSMOS_COLLECTION}")
    print(f"  Password: {'*' * 20} (in connection string)")
    
    client.close()
    
except Exception as e:
    print(f"[ERROR] Failed to send alarm: {e}")
    import traceback
    traceback.print_exc()

