"""
List all collections in CosmosDB database
"""

import os
import json
from pymongo import MongoClient
from urllib.parse import urlparse, unquote

# Load configuration
config_path = os.path.join(os.path.dirname(__file__), "local_data.json")
with open(config_path, 'r') as f:
    config = json.load(f)

MONGODB_CONNECTION_STRING = config.get("mongodb_connection_string")
COSMOS_DATABASE = config.get("cosmos_database", "secomeadb")

print("=" * 80)
print("Listing Collections in CosmosDB")
print("=" * 80)
print(f"Database: {COSMOS_DATABASE}")
print()

try:
    # Parse connection string
    parsed = urlparse(MONGODB_CONNECTION_STRING)
    username = unquote(parsed.username) if parsed.username else ""
    password = unquote(parsed.password) if parsed.password else ""
    host = parsed.hostname
    port = parsed.port or 10255
    
    # Connect to CosmosDB
    client = MongoClient(
        host=host,
        port=port,
        username=username,
        password=password,
        authSource=COSMOS_DATABASE,
        tls=True,
        tlsAllowInvalidCertificates=True,
        retryWrites=False,
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000,
        socketTimeoutMS=10000
    )
    
    # Get database
    db = client[COSMOS_DATABASE]
    
    # List all collections - CosmosDB compatible method
    # Try to get collections by querying system collections or known collections
    # For CosmosDB, we'll try common collection names or query system collections
    
    # Try to get collections from system.namespaces (if available)
    collections = []
    try:
        # Try listing from system collections
        system_collections = db.list_collection_names()
        collections = system_collections
    except:
        # If that fails, try common collection names
        common_names = ['sensordata', 'sensor_data', 'alarms', 'alarm', 'data', 'telemetry', 
                       'measurements', 'events', 'logs', 'iotdata', 'iot_data']
        for name in common_names:
            try:
                # Try to access the collection
                test_collection = db[name]
                # Try to count documents (this will fail if collection doesn't exist)
                test_collection.count_documents({}, limit=1)
                collections.append(name)
            except:
                pass
    
    # If still no collections, try to find by querying a known pattern
    if not collections:
        print("Trying to discover collections...")
        # Try querying system collections directly
        try:
            namespaces = db['system.namespaces'].find()
            for ns in namespaces:
                name = ns.get('name', '').split('.')[-1]  # Get collection name
                if name and not name.startswith('system'):
                    collections.append(name)
        except:
            pass
    
    if collections:
        print(f"Found {len(collections)} collection(s):\n")
        for i, collection_name in enumerate(collections, 1):
            try:
                # Get document count
                count = db[collection_name].count_documents({})
                print(f"{i}. {collection_name} ({count} documents)")
                
                # Get a sample document to show structure
                sample = db[collection_name].find_one()
                if sample:
                    fields = list(sample.keys())[:5]  # Show first 5 fields
                    print(f"   Fields: {', '.join(fields)}...")
                    if 'Test2OPCUA:CommonAlarm' in sample:
                        print(f"   [OK] Contains 'Test2OPCUA:CommonAlarm' field")
            except Exception as e:
                print(f"{i}. {collection_name} (error accessing: {str(e)[:50]})")
            print()
    else:
        print("Could not automatically discover collections.")
        print("\nPlease check Azure Portal -> CosmosDB -> Data Explorer")
        print("to find the collection name, or enter it manually.")
    
    client.close()
    
    print("=" * 80)
    print("\nTo update local_data.json, change:")
    print('  "cosmos_collection": "YourCollectionName"')
    print("to:")
    if collections:
        print(f'  "cosmos_collection": "{collections[0]}"')
    print("\nOr edit local_data.json manually with the correct collection name.")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

