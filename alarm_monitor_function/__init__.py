"""
Azure Function App to monitor CosmosDB for Test2OPCUA:CommonAlarm and make phone calls
"""

import logging
import os
import json
from datetime import datetime, timedelta
import azure.functions as func
from pymongo import MongoClient
from azure.communication.callautomation import CallAutomationClient, PhoneNumberIdentifier

# Configuration from environment variables
MONGODB_CONNECTION_STRING = os.environ.get("MongoDBConnectionString")
COSMOS_DATABASE = os.environ.get("COSMOS_DATABASE", "IoTDatabase")
COSMOS_COLLECTION = os.environ.get("COSMOS_COLLECTION", "YourCollectionName")
ALARM_FIELD = os.environ.get("ALARM_FIELD", "Test2OPCUA:CommonAlarm")
PHONE_NUMBER_TO_CALL = os.environ.get("PHONE_NUMBER_TO_CALL")
COMMUNICATION_SERVICE_CONNECTION_STRING = os.environ.get("COMMUNICATION_SERVICE_CONNECTION_STRING")
COMMUNICATION_SERVICE_PHONE_NUMBER = os.environ.get("COMMUNICATION_SERVICE_PHONE_NUMBER")
CALLBACK_URL = os.environ.get("CALLBACK_URL", "")

# Track last alarm state (in production, use Azure Table Storage or CosmosDB)
last_alarm_state = {}


def parse_timestamp(timestamp_value):
    """
    Parse timestamp from document - handles Windows FILETIME, Unix timestamps, etc.
    Returns datetime object
    """
    try:
        if isinstance(timestamp_value, (int, float)):
            # Windows FILETIME: 100-nanosecond intervals since January 1, 1601
            if 1.3e17 <= timestamp_value <= 1.5e17:
                windows_epoch = datetime(1601, 1, 1)
                return windows_epoch + timedelta(microseconds=timestamp_value / 10)
            elif timestamp_value > 1e15:  # Nanoseconds
                return datetime.fromtimestamp(timestamp_value / 1e9)
            elif timestamp_value > 1e12:  # Microseconds
                return datetime.fromtimestamp(timestamp_value / 1e6)
            elif timestamp_value > 1e9:  # Milliseconds
                return datetime.fromtimestamp(timestamp_value / 1e3)
            else:  # Seconds
                return datetime.fromtimestamp(timestamp_value)
    except (ValueError, OSError) as e:
        logging.error(f"Error parsing timestamp {timestamp_value}: {e}")
    return None


def check_alarm_in_cosmosdb():
    """Check CosmosDB for alarm condition"""
    try:
        if not MONGODB_CONNECTION_STRING:
            logging.error("MongoDBConnectionString not configured")
            return None
        
        # Connect to CosmosDB
        client = MongoClient(MONGODB_CONNECTION_STRING)
        db = client[COSMOS_DATABASE]
        collection = db[COSMOS_COLLECTION]
        
        # Get the most recent document
        latest_doc = collection.find_one(
            sort=[("_id", -1)]  # Sort by _id descending to get latest
        )
        
        if not latest_doc:
            logging.info("No documents found in collection")
            return None
        
        # Check for alarm field
        alarm_value = latest_doc.get(ALARM_FIELD)
        
        # Parse timestamp if available
        timestamp = None
        if 'timestamp' in latest_doc:
            timestamp = parse_timestamp(latest_doc['timestamp'])
        
        logging.info(f"Latest document: ID={latest_doc.get('_id')}, Alarm={alarm_value}, Timestamp={timestamp}")
        
        return alarm_value, latest_doc
        
    except Exception as e:
        logging.error(f"Error checking CosmosDB: {e}")
        return None


def make_phone_call(message="Alarm triggered: Test2OPCUA:CommonAlarm is 1"):
    """Make phone call using Azure Communication Services"""
    try:
        if not COMMUNICATION_SERVICE_CONNECTION_STRING:
            logging.error("Communication Service connection string not configured")
            return False
        
        if not PHONE_NUMBER_TO_CALL:
            logging.error("Phone number to call not configured")
            return False
        
        if not COMMUNICATION_SERVICE_PHONE_NUMBER:
            logging.error("Communication Service phone number not configured")
            return False
        
        # Initialize Call Automation Client
        call_automation_client = CallAutomationClient.from_connection_string(
            COMMUNICATION_SERVICE_CONNECTION_STRING
        )
        
        logging.info(f"Making phone call to {PHONE_NUMBER_TO_CALL}...")
        
        # Create call
        try:
            # Convert phone numbers to PhoneNumberIdentifier objects
            target_phone = PhoneNumberIdentifier(PHONE_NUMBER_TO_CALL)
            source_phone = PhoneNumberIdentifier(COMMUNICATION_SERVICE_PHONE_NUMBER)
            
            callback_url = CALLBACK_URL or f"https://{os.environ.get('WEBSITE_HOSTNAME', 'localhost')}/api/callbacks"
            
            call_connection = call_automation_client.create_call(
                target_participant=target_phone,
                callback_url=callback_url,
                source_caller_id_number=source_phone
            )
            
            logging.info(f"Call initiated: {call_connection.call_connection_id}")
            return True
        except Exception as e:
            logging.error(f"Failed to create call: {e}")
            logging.error(f"Error type: {type(e).__name__}")
            import traceback
            logging.error(traceback.format_exc())
            return False
        
    except Exception as e:
        logging.error(f"Error making phone call: {e}")
        return False


def monitor_timer_trigger(timer: func.TimerRequest) -> None:
    """
    Timer trigger function that runs every minute to check for alarms
    Configure in function.json with schedule: "0 * * * * *" (every minute)
    """
    logging.info(f"Timer trigger executed at {datetime.now()}")
    
    # Check for alarm
    result = check_alarm_in_cosmosdb()
    
    if result is None:
        logging.info("No data found or error checking CosmosDB")
        return
    
    alarm_value, doc = result
    doc_id = str(doc.get('_id', 'unknown'))
    
    # Check if alarm is triggered
    if alarm_value == 1:
        # Only make call if alarm state changed (avoid duplicate calls)
        if last_alarm_state.get(doc_id) != 1:
            logging.warning(f"⚠️  ALARM TRIGGERED! {ALARM_FIELD} = 1")
            logging.info(f"Document ID: {doc_id}")
            
            # Make phone call
            alarm_message = f"ALARM: {ALARM_FIELD} is active. Check system immediately."
            make_phone_call(alarm_message)
            
            last_alarm_state[doc_id] = 1
        else:
            logging.info("Alarm still active (already notified)")
    else:
        if last_alarm_state.get(doc_id) == 1:
            logging.info(f"✅ Alarm cleared: {ALARM_FIELD} = {alarm_value}")
            last_alarm_state[doc_id] = alarm_value
        else:
            logging.info(f"Status OK: {ALARM_FIELD} = {alarm_value}")


def cosmosdb_trigger(documents: func.DocumentList) -> None:
    """
    CosmosDB trigger function that runs when new documents are added
    This is more efficient than polling
    """
    logging.info(f"CosmosDB trigger executed. Documents: {len(documents)}")
    
    for doc in documents:
        try:
            doc_dict = json.loads(doc.to_json()) if hasattr(doc, 'to_json') else doc
            
            # Check for alarm field
            alarm_value = doc_dict.get(ALARM_FIELD)
            doc_id = str(doc_dict.get('_id', 'unknown'))
            
            if alarm_value == 1:
                # Check if we already notified for this alarm
                if last_alarm_state.get(doc_id) != 1:
                    logging.warning(f"⚠️  ALARM TRIGGERED in new document! {ALARM_FIELD} = 1")
                    logging.info(f"Document ID: {doc_id}")
                    
                    # Make phone call
                    alarm_message = f"ALARM: {ALARM_FIELD} is active. Check system immediately."
                    make_phone_call(alarm_message)
                    
                    last_alarm_state[doc_id] = 1
                    
        except Exception as e:
            logging.error(f"Error processing document: {e}")


