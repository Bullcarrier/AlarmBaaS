"""
Monitor CosmosDB and display last 24 hours of data, updating every 30 seconds
Includes phone call functionality when alarms are detected
"""

import os
import json
from datetime import datetime, timedelta
from pymongo import MongoClient
import time
import sys

# Azure Communication Services for phone calls
try:
    from azure.communication.callautomation import CallAutomationClient, PhoneNumberIdentifier
    CALL_AUTOMATION_AVAILABLE = True
except ImportError:
    CALL_AUTOMATION_AVAILABLE = False
    print("⚠️  azure-communication-callautomation not installed. Phone calls will be disabled.")
    print("   Install with: pip install azure-communication-callautomation")

# Load configuration from local_data.json
config_path = os.path.join(os.path.dirname(__file__), "local_data.json")
with open(config_path, 'r') as f:
    config = json.load(f)

MONGODB_CONNECTION_STRING = config.get("mongodb_connection_string")
COSMOS_DATABASE = config.get("cosmos_database", "secomeadb")
COSMOS_COLLECTION = config.get("cosmos_collection", "YourCollectionName")

ALARM_FIELD = config.get("alarm_field", "Test2OPCUA:CommonAlarm")
PHONE_NUMBER_TO_CALL = config.get("phone_number_to_call", "")
COMMUNICATION_SERVICE_CONNECTION_STRING = config.get("communication_service_connection_string", "")
COMMUNICATION_SERVICE_PHONE_NUMBER = config.get("communication_service_phone_number", "")

# Track last alarm state to avoid duplicate calls (persistent across restarts)
ALARM_STATE_FILE = os.path.join(os.path.dirname(__file__), ".alarm_state.json")

def load_alarm_state():
    """Load alarm state from file"""
    try:
        if os.path.exists(ALARM_STATE_FILE):
            with open(ALARM_STATE_FILE, 'r') as f:
                data = json.load(f)
                return data.get('last_alarm_state', {}), data.get('last_call_time', {})
    except:
        pass
    return {}, {}

def save_alarm_state(last_alarm_state, last_call_time):
    """Save alarm state to file"""
    try:
        data = {
            'last_alarm_state': last_alarm_state,
            'last_call_time': {k: v.isoformat() if isinstance(v, datetime) else v 
                              for k, v in last_call_time.items()}
        }
        with open(ALARM_STATE_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Warning: Could not save alarm state: {e}")

# Load persistent alarm state
last_alarm_state, last_call_time = load_alarm_state()

# Convert string timestamps back to datetime objects
for key, value in last_call_time.items():
    if isinstance(value, str):
        try:
            last_call_time[key] = datetime.fromisoformat(value)
        except:
            last_call_time[key] = datetime.min

# Check if collection name needs to be updated
if COSMOS_COLLECTION == "YourCollectionName":
    print("⚠️  WARNING: COSMOS_COLLECTION is set to 'YourCollectionName'")
    print("   Trying to discover collection name...")
    
    # Try to discover the collection by testing common names
    common_names = ['sensordata', 'sensor_data', 'alarms', 'alarm', 'data', 'telemetry', 
                   'measurements', 'events', 'logs', 'iotdata', 'iot_data', 'secomea']
    
    discovered = None
    try:
        # Quick connection test
        parsed = urlparse(MONGODB_CONNECTION_STRING)
        username = unquote(parsed.username) if parsed.username else ""
        password = unquote(parsed.password) if parsed.password else ""
        host = parsed.hostname
        port = parsed.port or 10255
        
        test_client = MongoClient(
            host=host, port=port, username=username, password=password,
            authSource=COSMOS_DATABASE, tls=True, tlsAllowInvalidCertificates=True,
            retryWrites=False, serverSelectionTimeoutMS=5000
        )
        test_db = test_client[COSMOS_DATABASE]
        
        for name in common_names:
            try:
                test_col = test_db[name]
                # Try to find a document with the alarm field
                sample = test_col.find_one({ALARM_FIELD: {"$exists": True}})
                if sample:
                    discovered = name
                    print(f"   ✓ Found collection: {name}")
                    break
            except:
                pass
        
        test_client.close()
    except:
        pass
    
    if discovered:
        COSMOS_COLLECTION = discovered
        print(f"   Using discovered collection: {COSMOS_COLLECTION}")
    else:
        print("   Could not auto-discover collection name")
        print("   Please enter collection name now (or press Enter to try 'YourCollectionName'): ", end="", flush=True)
        try:
            user_input = input().strip()
            if user_input:
                COSMOS_COLLECTION = user_input
                print(f"   Using collection: {COSMOS_COLLECTION}")
        except:
            pass

def clear_screen():
    """Clear terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def make_phone_call(message="Alarm triggered: Test2OPCUA:CommonAlarm is 1"):
    """Make phone call using Azure Communication Services"""
    if not CALL_AUTOMATION_AVAILABLE:
        print(f"⚠️  Phone call disabled - azure-communication-callautomation not installed")
        return False
    
    try:
        if not COMMUNICATION_SERVICE_CONNECTION_STRING:
            print("⚠️  Communication Service connection string not configured")
            return False
        
        if not PHONE_NUMBER_TO_CALL:
            print("⚠️  Phone number to call not configured")
            return False
        
        if not COMMUNICATION_SERVICE_PHONE_NUMBER:
            print("⚠️  Communication Service phone number not configured")
            return False
        
        # Initialize Call Automation Client
        call_automation_client = CallAutomationClient.from_connection_string(
            COMMUNICATION_SERVICE_CONNECTION_STRING
        )
        
        print(f"Making phone call to {PHONE_NUMBER_TO_CALL}...")
        
        # Create call
        try:
            callback_url = config.get("callback_url", "")
            if not callback_url:
                callback_url = "https://localhost/api/callbacks"  # Dummy URL for local testing
            
            # Convert phone number to PhoneNumberIdentifier
            target_phone = PhoneNumberIdentifier(PHONE_NUMBER_TO_CALL)
            source_phone = PhoneNumberIdentifier(COMMUNICATION_SERVICE_PHONE_NUMBER)
            
            # Create the call using the proper format
            call_connection = call_automation_client.create_call(
                target_participant=target_phone,
                callback_url=callback_url,
                source_caller_id_number=source_phone
            )
            
            print(f"[SUCCESS] Call initiated: {call_connection.call_connection_id}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to create call: {e}")
            print(f"   Error details: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f"❌ Error making phone call: {e}")
        return False

def format_timestamp(timestamp):
    """Format timestamp for display - handles Windows FILETIME, Unix timestamps, etc."""
    if isinstance(timestamp, datetime):
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")
    elif isinstance(timestamp, (int, float)):
        # Handle different timestamp formats
        # Windows FILETIME: 100-nanosecond intervals since January 1, 1601
        if 1.3e17 <= timestamp <= 1.5e17:  # FILETIME range for 2020-2030
            windows_epoch = datetime(1601, 1, 1)
            dt = windows_epoch + timedelta(microseconds=timestamp / 10)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        elif timestamp > 1e15:  # Nanoseconds
            dt = datetime.fromtimestamp(timestamp / 1e9)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        elif timestamp > 1e12:  # Microseconds
            dt = datetime.fromtimestamp(timestamp / 1e6)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        elif timestamp > 1e9:  # Milliseconds
            dt = datetime.fromtimestamp(timestamp / 1e3)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        else:  # Seconds
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
    elif isinstance(timestamp, str):
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return str(timestamp)
    return str(timestamp)

def get_documents_last_24h():
    """Get documents from last 24 hours"""
    try:
        # CosmosDB MongoDB API connection with compatibility settings
        # Parse connection string properly
        from urllib.parse import urlparse, unquote
        
        parsed = urlparse(MONGODB_CONNECTION_STRING)
        username = unquote(parsed.username) if parsed.username else ""
        password = unquote(parsed.password) if parsed.password else ""
        host = parsed.hostname
        port = parsed.port or 10255
        
        # Connect directly with CosmosDB-compatible options
        # PyMongo 3.12.3 should work with older wire versions
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
        
        # Test connection with a simple operation
        try:
            # Try to list databases first (lighter operation)
            client.list_database_names()
        except Exception as e:
            # If that fails, try direct access
            print(f"⚠️  Connection warning: {e}")
            pass
        
        db = client[COSMOS_DATABASE]
        collection = db[COSMOS_COLLECTION]
        
        # Calculate 24 hours ago (adjust local time -1 hour for DB comparison)
        now = datetime.utcnow() - timedelta(hours=1)
        last_24h = now - timedelta(hours=24)
        
        # Get a sample document to understand the structure
        sample = collection.find_one(sort=[("_id", -1)])
        if not sample:
            print("⚠️  No documents found in collection")
            return None, None
        
        # Try different timestamp fields and formats
        timestamp_fields = ['timestamp', '_ts', 'time', 'date', '_id']
        timestamp_field = None
        query = {}
        
        # Check timestamp field format
        for field in timestamp_fields:
            if field in sample:
                timestamp_value = sample[field]
                
                if field == 'timestamp':
                    # Handle different timestamp formats
                    if isinstance(timestamp_value, (int, float)):
                        # Could be FILETIME, nanoseconds, microseconds, milliseconds, or seconds
                        # Try to determine the format
                        if 1.3e17 <= timestamp_value <= 1.5e17:  # Windows FILETIME
                            # Convert 24 hours ago to FILETIME
                            windows_epoch = datetime(1601, 1, 1)
                            last_24h_filetime = int((last_24h - windows_epoch).total_seconds() * 1e7)
                            query = {"timestamp": {"$gte": last_24h_filetime}}
                            timestamp_field = field
                            break
                        elif timestamp_value > 1e15:  # Nanoseconds (e.g., 134075122252005310)
                            # Convert 24 hours ago to nanoseconds
                            last_24h_ns = int((last_24h.timestamp()) * 1e9)
                            query = {"timestamp": {"$gte": last_24h_ns}}
                            timestamp_field = field
                            break
                        elif timestamp_value > 1e12:  # Microseconds
                            last_24h_us = int((last_24h.timestamp()) * 1e6)
                            query = {"timestamp": {"$gte": last_24h_us}}
                            timestamp_field = field
                            break
                        elif timestamp_value > 1e9:  # Milliseconds
                            last_24h_ms = int((last_24h.timestamp()) * 1e3)
                            query = {"timestamp": {"$gte": last_24h_ms}}
                            timestamp_field = field
                            break
                        else:  # Seconds
                            query = {"timestamp": {"$gte": int(last_24h.timestamp())}}
                            timestamp_field = field
                            break
                elif field == '_ts':
                    # _ts is Unix timestamp
                    query = {"_ts": {"$gte": int(last_24h.timestamp())}}
                    timestamp_field = field
                    break
                elif field == '_id':
                    # _id might be ObjectId with timestamp
                    from bson import ObjectId
                    try:
                        obj_id = ObjectId(sample['_id'])
                        query = {"_id": {"$gte": ObjectId.from_datetime(last_24h)}}
                        timestamp_field = field
                        break
                    except:
                        pass
        
        # If timestamp field found, use query; otherwise get last 100 documents
        if timestamp_field:
            # Try query first, but if it returns too few results, get more documents
            documents = list(collection.find(query).sort("_id", -1).limit(100))
            if len(documents) < 5:  # If query returns very few, get more documents
                # Get last 100 documents regardless of timestamp
                all_docs = list(collection.find().sort("_id", -1).limit(100))
                if len(all_docs) > len(documents):
                    print(f"⚠️  Query returned {len(documents)} document(s), showing last {len(all_docs)} documents instead")
                    documents = all_docs
        else:
            print("⚠️  No recognized timestamp field found, showing last 100 documents")
            documents = list(collection.find().sort("_id", -1).limit(100))
        
        # Filter out test alarms from display (but keep them for alarm checking)
        # We'll show them but mark them clearly
        
        client.close()
        return documents, timestamp_field
        
    except Exception as e:
        print(f"❌ Error connecting to CosmosDB: {e}")
        return None, None

def display_documents(documents, timestamp_field):
    """Display documents in a formatted way"""
    clear_screen()
    
    print("=" * 80)
    print(f"COSMOSDB MONITOR - Last 24 Hours")
    print(f"Database: {COSMOS_DATABASE} | Collection: {COSMOS_COLLECTION}")
    print(f"Alarm Field: {ALARM_FIELD}")
    print(f"Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    if not documents:
        print("⚠️  No documents found in the last 24 hours")
        return
    
    print(f"📊 Found {len(documents)} document(s)\n")
    
    # Check for test alarm trigger first (before checking real documents)
    check_test_alarm_trigger()
    
    # Check the most recent document (first in list) for alarm
    most_recent_doc = documents[0] if documents else None
    most_recent_alarm_value = None
    most_recent_doc_id = None
    
    if most_recent_doc:
        most_recent_alarm_value = most_recent_doc.get(ALARM_FIELD, "N/A")
        most_recent_doc_id = str(most_recent_doc.get('_id', 'unknown'))
        
        # Check if the most recent document has an alarm and make phone call
        if most_recent_alarm_value == 1:
            # Check document age - don't call for old alarms (older than 10 minutes)
            doc_timestamp = None
            if 'timestamp' in most_recent_doc:
                ts_value = most_recent_doc['timestamp']
                if isinstance(ts_value, (int, float)):
                    if 1.3e17 <= ts_value <= 1.5e17:  # Windows FILETIME
                        windows_epoch = datetime(1601, 1, 1)
                        doc_timestamp = windows_epoch + timedelta(microseconds=ts_value / 10)
                    elif ts_value > 1e15:  # Nanoseconds
                        doc_timestamp = datetime.fromtimestamp(ts_value / 1e9)
                    elif ts_value > 1e12:  # Microseconds
                        doc_timestamp = datetime.fromtimestamp(ts_value / 1e6)
                    elif ts_value > 1e9:  # Milliseconds
                        doc_timestamp = datetime.fromtimestamp(ts_value / 1e3)
                    else:  # Seconds
                        doc_timestamp = datetime.fromtimestamp(ts_value)
            
            # If document is older than 10 minutes, consider it "old" and don't call
            # Adjust local time -1 hour for DB comparison
            is_old_alarm = False
            if doc_timestamp:
                current_time_adjusted = datetime.now() - timedelta(hours=1)
                age_seconds = (current_time_adjusted - doc_timestamp).total_seconds()
                if age_seconds > 600:  # 10 minutes
                    is_old_alarm = True
                    print(f"\nℹ️  Alarm detected but document is old ({int(age_seconds/60)} min old) - skipping call")
            
            # Only make call if alarm state changed AND it's not an old alarm
            if not is_old_alarm and last_alarm_state.get(most_recent_doc_id) != 1:
                # Check if we called recently (avoid spam - max 1 call per 5 minutes)
                # Adjust local time -1 hour for DB comparison
                last_call = last_call_time.get(most_recent_doc_id, datetime.min)
                current_time_adjusted = datetime.now() - timedelta(hours=1)
                time_since_last_call = (current_time_adjusted - last_call).total_seconds()
                
                if time_since_last_call > 300:  # 5 minutes cooldown
                    print(f"\n{'=' * 80}")
                    print(f"⚠️  ALARM TRIGGERED in most recent document!")
                    print(f"   Making phone call...")
                    print(f"{'=' * 80}\n")
                    alarm_message = f"ALARM: {ALARM_FIELD} is active. Check system immediately."
                    call_success = make_phone_call(alarm_message)
                    if call_success:
                        # Store time with -1 hour adjustment
                        last_call_time[most_recent_doc_id] = datetime.now() - timedelta(hours=1)
                        print(f"[SUCCESS] Phone call initiated successfully!")
                    else:
                        print(f"[ERROR] Phone call failed. Check configuration.")
                    last_alarm_state[most_recent_doc_id] = 1
                    save_alarm_state(last_alarm_state, last_call_time)
                else:
                    minutes_left = int((300 - time_since_last_call) / 60)
                    print(f"\n⚠️  Alarm detected but call cooldown active ({minutes_left} min remaining)")
            elif is_old_alarm:
                # Old alarm - mark as seen but don't call
                last_alarm_state[most_recent_doc_id] = 1
                save_alarm_state(last_alarm_state, last_call_time)
            else:
                print(f"\nℹ️  Alarm still active (call already made for this alarm)")
        else:
            if last_alarm_state.get(most_recent_doc_id) == 1:
                print(f"\n✅ Alarm cleared in most recent document: {ALARM_FIELD} = {most_recent_alarm_value}")
            last_alarm_state[most_recent_doc_id] = most_recent_alarm_value
            save_alarm_state(last_alarm_state, last_call_time)
    
    print()
    
    # Display documents
    for i, doc in enumerate(documents, 1):
        print(f"\n{'─' * 80}")
        print(f"Document #{i}")
        print(f"{'─' * 80}")
        
        # Display timestamp
        if timestamp_field and timestamp_field in doc:
            if timestamp_field == '_ts':
                ts = datetime.fromtimestamp(doc['_ts'])
                print(f"Timestamp: {ts.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            elif timestamp_field == '_id':
                from bson import ObjectId
                try:
                    obj_id = ObjectId(doc['_id'])
                    print(f"Timestamp: {obj_id.generation_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                except:
                    print(f"ID: {doc['_id']}")
            elif timestamp_field == 'timestamp':
                # Handle FILETIME/nanosecond/microsecond/millisecond timestamps
                ts_value = doc[timestamp_field]
                if isinstance(ts_value, (int, float)):
                    if 1.3e17 <= ts_value <= 1.5e17:  # Windows FILETIME
                        windows_epoch = datetime(1601, 1, 1)
                        ts = windows_epoch + timedelta(microseconds=ts_value / 10)
                    elif ts_value > 1e15:  # Nanoseconds
                        ts = datetime.fromtimestamp(ts_value / 1e9)
                    elif ts_value > 1e12:  # Microseconds
                        ts = datetime.fromtimestamp(ts_value / 1e6)
                    elif ts_value > 1e9:  # Milliseconds
                        ts = datetime.fromtimestamp(ts_value / 1e3)
                    else:  # Seconds
                        ts = datetime.fromtimestamp(ts_value)
                    print(f"Timestamp: {ts.strftime('%Y-%m-%d %H:%M:%S UTC')} (raw: {ts_value})")
                else:
                    print(f"Timestamp: {format_timestamp(ts_value)}")
            else:
                print(f"Timestamp: {format_timestamp(doc[timestamp_field])}")
        else:
            print(f"ID: {doc.get('_id', 'N/A')}")
        
        # Display alarm field
        alarm_value = doc.get(ALARM_FIELD, "N/A")
        doc_id = str(doc.get('_id', 'unknown'))
        alarm_status = "🔴 ALARM ACTIVE" if alarm_value == 1 else "🟢 OK" if alarm_value == 0 else "⚪ UNKNOWN"
        
        # Mark if this is the most recent document
        is_most_recent = (i == 1)
        is_test_alarm = doc.get('test_alarm', False) or doc.get('created_by') == 'monitor_test'
        
        status_label = ""
        if is_most_recent:
            status_label = " [MOST RECENT]"
        if is_test_alarm:
            status_label += " [TEST ALARM - Can be ignored]"
        
        print(f"Alarm Status ({ALARM_FIELD}): {alarm_value} {alarm_status}{status_label}")
        
        # Display other important fields (first 10 fields)
        print("\nOther Fields:")
        field_count = 0
        for key, value in doc.items():
            if key not in ['_id', '_ts', ALARM_FIELD, timestamp_field] and field_count < 10:
                # Truncate long values
                value_str = str(value)
                if len(value_str) > 50:
                    value_str = value_str[:47] + "..."
                print(f"  {key}: {value_str}")
                field_count += 1
        if field_count >= 10:
            print(f"  ... and {len(doc) - field_count - 3} more fields")
    
    print(f"\n{'─' * 80}")
    print(f"\nRefreshing every 30 seconds... (Press Ctrl+C to stop)")
    print(f"Note: Old alarms (>10 min) won't trigger calls")
    print()

def create_test_alarm():
    """Create a test alarm state locally (without saving to database)"""
    print("Creating test alarm state (simulated, not saved to database)...")
    
    # Create a simulated test document ID
    test_doc_id = f"test_alarm_{int(datetime.now().timestamp())}"
    
    # Clear any previous test alarm state
    # Remove old test alarm entries from state
    keys_to_remove = [k for k in last_alarm_state.keys() if k.startswith("test_alarm_")]
    for key in keys_to_remove:
        last_alarm_state.pop(key, None)
        last_call_time.pop(key, None)
    
    # Set test alarm state to trigger call on next cycle
    # We'll simulate it by creating a temporary state that will be checked
    print(f"✅ Test alarm state created (ID: {test_doc_id})")
    print(f"   This will trigger a phone call on the next monitor cycle")
    print(f"   Note: No document is saved to the database")
    
    # Store test alarm info to trigger call
    # We'll use a special marker that the monitor will recognize
    # Store time with -1 hour adjustment for DB comparison
    test_alarm_marker = {
        'doc_id': test_doc_id,
        'created_at': datetime.now() - timedelta(hours=1),
        'trigger_call': True
    }
    
    # Save test alarm marker to state file
    try:
        state_data = {
            'last_alarm_state': last_alarm_state,
            'last_call_time': {k: v.isoformat() if isinstance(v, datetime) else v 
                              for k, v in last_call_time.items()},
            'test_alarm': test_alarm_marker
        }
        with open(ALARM_STATE_FILE, 'w') as f:
            json.dump(state_data, f)
    except:
        pass
    
    return True

def delete_test_alarms_from_db():
    """Delete test alarm documents from the database"""
    try:
        from urllib.parse import urlparse, unquote
        
        parsed = urlparse(MONGODB_CONNECTION_STRING)
        username = unquote(parsed.username) if parsed.username else ""
        password = unquote(parsed.password) if parsed.password else ""
        host = parsed.hostname
        port = parsed.port or 10255
        
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
        collection = db[COSMOS_COLLECTION]
        
        # Find and delete test alarms
        result = collection.delete_many({
            "$or": [
                {"test_alarm": True},
                {"created_by": "monitor_test"}
            ]
        })
        
        client.close()
        
        print(f"✅ Deleted {result.deleted_count} test alarm document(s) from database")
        return result.deleted_count
        
    except Exception as e:
        print(f"❌ Error deleting test alarms: {e}")
        return 0

def check_test_alarm_trigger():
    """Check if we need to trigger a call for a test alarm"""
    try:
        if os.path.exists(ALARM_STATE_FILE):
            with open(ALARM_STATE_FILE, 'r') as f:
                data = json.load(f)
                test_alarm = data.get('test_alarm')
                if test_alarm and test_alarm.get('trigger_call'):
                    # Check if it's recent (within last minute)
                    # Adjust local time -1 hour for DB comparison
                    created_at = datetime.fromisoformat(test_alarm['created_at'])
                    current_time_adjusted = datetime.now() - timedelta(hours=1)
                    if (current_time_adjusted - created_at).total_seconds() < 60:
                        # Trigger the call
                        doc_id = test_alarm['doc_id']
                        if last_call_time.get(doc_id, datetime.min) != datetime.now():
                            print(f"\n{'=' * 80}")
                            print(f"⚠️  TEST ALARM TRIGGERED!")
                            print(f"   Making phone call...")
                            print(f"{'=' * 80}\n")
                            alarm_message = f"TEST ALARM: {ALARM_FIELD} is active. This is a test call."
                            call_success = make_phone_call(alarm_message)
                            if call_success:
                                # Store time with -1 hour adjustment
                                last_call_time[doc_id] = datetime.now() - timedelta(hours=1)
                                print(f"[SUCCESS] Test phone call initiated successfully!")
                            else:
                                print(f"[ERROR] Test phone call failed. Check configuration.")
                            
                            # Clear test alarm trigger
                            test_alarm['trigger_call'] = False
                            data['test_alarm'] = test_alarm
                            with open(ALARM_STATE_FILE, 'w') as f:
                                json.dump(data, f)
                            return True
    except:
        pass
    return False

def main():
    """Main monitoring loop"""
    print("🚀 Starting CosmosDB Monitor...")
    print(f"Connecting to: {COSMOS_DATABASE}/{COSMOS_COLLECTION}")
    print()
    print("=" * 80)
    print("CONTROLS:")
    print("  Press '1' + Enter to create a test alarm (triggers phone call, not saved to DB)")
    print("  Press '2' + Enter to delete test alarms from database")
    print("  Press Ctrl+C to stop monitoring")
    print("=" * 80)
    print()
    
    # Use threading to handle input while monitoring
    import threading
    import queue
    
    input_queue = queue.Queue()
    stop_monitoring = threading.Event()
    
    def input_handler():
        """Handle user input in a separate thread"""
        while not stop_monitoring.is_set():
            try:
                user_input = input().strip()
                if user_input:
                    input_queue.put(user_input)
            except:
                break
    
    # Start input handler thread
    input_thread = threading.Thread(target=input_handler, daemon=True)
    input_thread.start()
    
    try:
        while True:
            # Check for user input
            try:
                user_input = input_queue.get_nowait()
                if user_input == '1':
                    print("\n📞 Creating test alarm...")
                    create_test_alarm()
                    print("   Monitor will check for alarm on next cycle (30 seconds)\n")
                elif user_input == '2':
                    print("\n🗑️  Deleting test alarms from database...")
                    deleted = delete_test_alarms_from_db()
                    print(f"   Deleted {deleted} test alarm document(s)\n")
            except queue.Empty:
                pass
            
            documents, timestamp_field = get_documents_last_24h()
            if documents is not None:
                display_documents(documents, timestamp_field)
            else:
                print("❌ Failed to retrieve documents")
            
            # Wait 30 seconds, but check for input periodically
            for _ in range(30):
                time.sleep(1)
                # Check for user input during wait
                try:
                    user_input = input_queue.get_nowait()
                    if user_input == '1':
                        print("\n📞 Creating test alarm...")
                        create_test_alarm()
                        print("   Monitor will check for alarm on next cycle\n")
                    elif user_input == '2':
                        print("\n🗑️  Deleting test alarms from database...")
                        deleted = delete_test_alarms_from_db()
                        print(f"   Deleted {deleted} test alarm document(s)\n")
                except queue.Empty:
                    pass
            
    except KeyboardInterrupt:
        stop_monitoring.set()
        print("\n\n👋 Monitoring stopped by user")
        sys.exit(0)
    except Exception as e:
        stop_monitoring.set()
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

