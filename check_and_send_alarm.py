"""
Check database structure and send alarm to the correct database
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
print("Check Database and Send Alarm")
print("=" * 80)

# Parse connection string
parsed = urlparse(MONGODB_CONNECTION_STRING)
username = unquote(parsed.username) if parsed.username else ""
password = unquote(parsed.password) if parsed.password else ""
host = parsed.hostname
port = parsed.port or 10255

try:
    # Connect to CosmosDB
    print("Connecting to CosmosDB...")
    client = MongoClient(
        host=host,
        port=port,
        username=username,
        password=password,
        authSource="secomeadb",  # Try secomeadb first (from connection string)
        tls=True,
        tlsAllowInvalidCertificates=True,
        retryWrites=False,
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000,
        socketTimeoutMS=10000
    )
    
    # Try to list databases
    print("\nChecking available databases...")
    try:
        databases = client.list_database_names()
        print(f"Available databases: {databases}")
    except:
        print("Could not list databases (CosmosDB limitation)")
    
    # Try secomeadb first
    print(f"\nTrying database: secomeadb")
    try:
        db_secomea = client["secomeadb"]
        collections_secomea = db_secomea.list_collection_names()
        print(f"  Collections in secomeadb: {collections_secomea}")
        
        if COSMOS_COLLECTION in collections_secomea:
            print(f"  ✓ Found collection '{COSMOS_COLLECTION}' in secomeadb")
            collection = db_secomea[COSMOS_COLLECTION]
            
            # Check document count
            count = collection.count_documents({})
            print(f"  Document count: {count}")
            
            # Get latest document
            latest = collection.find_one(sort=[("_id", -1)])
            if latest:
                print(f"  Latest document ID: {latest.get('_id')}")
                print(f"  Latest document alarm: {latest.get(ALARM_FIELD, 'N/A')}")
            
            # Insert alarm document
            print(f"\nInserting alarm document into secomeadb/{COSMOS_COLLECTION}...")
            now = datetime.now()
            alarm_doc = {
                "timestamp": int(now.timestamp() * 1e9),
                ALARM_FIELD: 1,
                "source": "manual_trigger",
                "created_at": now.isoformat(),
                "description": "Manual alarm trigger to test Azure Function App"
            }
            
            result = collection.insert_one(alarm_doc)
            print(f"[SUCCESS] Alarm inserted into secomeadb!")
            print(f"  Document ID: {result.inserted_id}")
            print(f"  Database: secomeadb")
            print(f"  Collection: {COSMOS_COLLECTION}")
            
            client.close()
            exit(0)
    except Exception as e:
        print(f"  Error with secomeadb: {e}")
    
    # Try IoTDatabase
    print(f"\nTrying database: {COSMOS_DATABASE}")
    try:
        db_iot = client[COSMOS_DATABASE]
        collections_iot = db_iot.list_collection_names()
        print(f"  Collections in {COSMOS_DATABASE}: {collections_iot}")
        
        if COSMOS_COLLECTION in collections_iot:
            print(f"  ✓ Found collection '{COSMOS_COLLECTION}' in {COSMOS_DATABASE}")
            collection = db_iot[COSMOS_COLLECTION]
            
            # Check document count
            count = collection.count_documents({})
            print(f"  Document count: {count}")
            
            # Insert alarm document
            print(f"\nInserting alarm document into {COSMOS_DATABASE}/{COSMOS_COLLECTION}...")
            now = datetime.now()
            alarm_doc = {
                "timestamp": int(now.timestamp() * 1e9),
                ALARM_FIELD: 1,
                "source": "manual_trigger",
                "created_at": now.isoformat(),
                "description": "Manual alarm trigger to test Azure Function App"
            }
            
            result = collection.insert_one(alarm_doc)
            print(f"[SUCCESS] Alarm inserted into {COSMOS_DATABASE}!")
            print(f"  Document ID: {result.inserted_id}")
            print(f"  Database: {COSMOS_DATABASE}")
            print(f"  Collection: {COSMOS_COLLECTION}")
            
            client.close()
            exit(0)
    except Exception as e:
        print(f"  Error with {COSMOS_DATABASE}: {e}")
    
    print("\n[ERROR] Could not find the collection in either database")
    print("Please check Azure Portal -> CosmosDB -> Data Explorer")
    print("to find the correct database and collection name")
    
    client.close()
    
except Exception as e:
    print(f"[ERROR] Failed: {e}")
    import traceback
    traceback.print_exc()

