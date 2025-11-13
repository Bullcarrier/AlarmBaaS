"""
Find the collection name by trying to access it directly
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
ALARM_FIELD = config.get("alarm_field", "Test2OPCUA:CommonAlarm")

print("=" * 80)
print("Finding Collection with Alarm Field")
print("=" * 80)
print(f"Database: {COSMOS_DATABASE}")
print(f"Looking for field: {ALARM_FIELD}")
print()

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

db = client[COSMOS_DATABASE]

# Extended list of common collection names to try
collection_names_to_try = [
    'sensordata', 'sensor_data', 'sensors', 'sensor',
    'alarms', 'alarm', 'alarmdata', 'alarm_data',
    'data', 'telemetry', 'telemetrydata', 'telemetry_data',
    'measurements', 'measurement', 'measurementdata',
    'events', 'event', 'eventdata', 'event_data',
    'logs', 'log', 'logdata', 'log_data',
    'iotdata', 'iot_data', 'iot', 'iottelemetry',
    'secomea', 'secomeadata', 'secomea_data',
    'devicedata', 'device_data', 'device',
    'timeseries', 'timeseriesdata', 'tsdata',
    'opcua', 'opcdata', 'opc_ua',
    'monitoring', 'monitordata', 'monitor_data'
]

print("Trying collection names...")
print()

found_collections = []

for collection_name in collection_names_to_try:
    try:
        collection = db[collection_name]
        # Try to find a document with the alarm field
        sample = collection.find_one({ALARM_FIELD: {"$exists": True}})
        if sample:
            count = collection.count_documents({})
            found_collections.append({
                'name': collection_name,
                'count': count,
                'sample': sample
            })
            print(f"✓ FOUND: {collection_name} ({count} documents)")
            print(f"  Sample document has: {list(sample.keys())[:5]}")
            if 'timestamp' in sample:
                print(f"  Timestamp field: {sample['timestamp']}")
            print()
    except Exception as e:
        # Collection doesn't exist or error accessing
        pass

client.close()

if found_collections:
    print("=" * 80)
    print(f"\nFound {len(found_collections)} collection(s) with '{ALARM_FIELD}' field:\n")
    for i, col in enumerate(found_collections, 1):
        print(f"{i}. {col['name']} ({col['count']} documents)")
    
    # Use the first one found
    best_match = found_collections[0]
    print(f"\n✓ Best match: {best_match['name']}")
    print(f"\nTo update local_data.json, change:")
    print(f'  "cosmos_collection": "YourCollectionName"')
    print(f'to:')
    print(f'  "cosmos_collection": "{best_match["name"]}"')
    
    # Offer to update automatically
    print(f"\nWould you like me to update local_data.json automatically? (y/n): ", end="", flush=True)
    try:
        response = input().strip().lower()
        if response == 'y' or response == 'yes':
            # Update local_data.json
            config['cosmos_collection'] = best_match['name']
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"\n✓ Updated local_data.json with collection: {best_match['name']}")
        else:
            print("\nYou can update it manually in local_data.json")
    except:
        print("\nYou can update it manually in local_data.json")
else:
    print("=" * 80)
    print("\n[ERROR] Could not find any collection with the alarm field.")
    print("\nPlease:")
    print("1. Check Azure Portal -> CosmosDB -> Data Explorer")
    print("2. Find the collection name in the left sidebar")
    print("3. Update local_data.json manually with the collection name")
    print("\nOr if you know the collection name, you can enter it when running monitor_cosmosdb.py")

