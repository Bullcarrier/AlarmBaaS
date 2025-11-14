"""
Azure Function App to monitor CosmosDB for Test2OPCUA:CommonAlarm and make phone calls
"""

import logging
import os
import json
import time
from datetime import datetime, timedelta
import azure.functions as func
from pymongo import MongoClient
from azure.communication.callautomation import CallAutomationClient, PhoneNumberIdentifier

# Try to import media source classes for playing audio
try:
    from azure.communication.callautomation import FileSource
    AUDIO_PLAYBACK_AVAILABLE = True
except ImportError:
    AUDIO_PLAYBACK_AVAILABLE = False
    # Audio playback classes not available

# Configuration from environment variables
MONGODB_CONNECTION_STRING = os.environ.get("MongoDBConnectionString")
COSMOS_DATABASE = os.environ.get("COSMOS_DATABASE", "IoTDatabase")
COSMOS_COLLECTION = os.environ.get("COSMOS_COLLECTION", "YourCollectionName")
ALARM_FIELD = os.environ.get("ALARM_FIELD", "Test2OPCUA:CommonAlarm")
PHONE_NUMBER_TO_CALL = os.environ.get("PHONE_NUMBER_TO_CALL")
COMMUNICATION_SERVICE_CONNECTION_STRING = os.environ.get("COMMUNICATION_SERVICE_CONNECTION_STRING")
COMMUNICATION_SERVICE_PHONE_NUMBER = os.environ.get("COMMUNICATION_SERVICE_PHONE_NUMBER")
CALLBACK_URL = os.environ.get("CALLBACK_URL", "")
AUDIO_FILE_URL = os.environ.get("AUDIO_FILE_URL", "")  # URL to pre-recorded WAV file

# Track last alarm state (in production, use Azure Table Storage or CosmosDB)
last_alarm_state = {}


def parse_timestamp(timestamp_value):
    """
    Parse timestamp from document - handles Windows FILETIME, Unix timestamps, etc.
    Returns datetime object
    Note: Returned timestamps are in UTC; use -1 hour adjustment for comparisons
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
        
        logging.info(f"Connecting to database: {COSMOS_DATABASE}, collection: {COSMOS_COLLECTION}")
        
        # Connect to CosmosDB
        client = MongoClient(MONGODB_CONNECTION_STRING)
        db = client[COSMOS_DATABASE]
        collection = db[COSMOS_COLLECTION]
        
        # Get the most recent document
        latest_doc = collection.find_one(
            sort=[("_id", -1)]  # Sort by _id descending to get latest
        )
        
        if not latest_doc:
            logging.info(f"No documents found in collection '{COSMOS_COLLECTION}' in database '{COSMOS_DATABASE}'")
            # Try to list available databases and collections for debugging
            try:
                db_list = client.list_database_names()
                logging.info(f"Available databases: {db_list}")
                if COSMOS_DATABASE in db_list:
                    coll_list = db.list_collection_names()
                    logging.info(f"Available collections in {COSMOS_DATABASE}: {coll_list}")
            except Exception as debug_e:
                logging.warning(f"Could not list databases/collections for debugging: {debug_e}")
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


def make_phone_call(message="Hi Operator, this is the Bawat Container. There is a Safety Alarm. Please attend."):
    """Make phone call using Azure Communication Services and play message when answered"""
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
            
            # Create the call
            call_connection = call_automation_client.create_call(
                target_participant=target_phone,
                callback_url=callback_url,
                source_caller_id_number=source_phone
            )
            
            call_connection_id = call_connection.call_connection_id
            server_call_id = getattr(call_connection, 'server_call_id', None)
            logging.info(f"Call initiated: {call_connection_id}, ServerCallId: {server_call_id}")
            
            # Debug logging
            logging.info(f"Audio file URL configured: {bool(AUDIO_FILE_URL)}")
            logging.info(f"Audio playback available: {AUDIO_PLAYBACK_AVAILABLE}")
            if AUDIO_FILE_URL:
                logging.info(f"Audio file URL value: {AUDIO_FILE_URL[:50]}...")  # Log first 50 chars
            
            # Play audio file if URL is provided
            if AUDIO_FILE_URL and AUDIO_PLAYBACK_AVAILABLE:
                try:
                    # Get the call connection
                    call_connection_obj = call_automation_client.get_call_connection(call_connection_id)
                    
                    # Create file source for audio playback
                    file_source = FileSource(url=AUDIO_FILE_URL)
                    
                    # Wait for call to be established (answered) with retry logic
                    max_retries = 10  # Try for up to 30 seconds (10 retries * 3 seconds)
                    retry_count = 0
                    playback_success = False
                    
                    while retry_count < max_retries and not playback_success:
                        try:
                            # Wait before trying
                            if retry_count > 0:
                                time.sleep(3)  # Wait 3 seconds between retries
                            else:
                                time.sleep(5)  # Wait 5 seconds on first attempt
                            
                            # Try to play audio
                            if hasattr(call_connection_obj, 'play_media_to_all'):
                                call_connection_obj.play_media_to_all(file_source)
                                logging.info(f"Audio playback started (play_media_to_all) from: {AUDIO_FILE_URL}")
                                playback_success = True
                            elif hasattr(call_connection_obj, 'play_media'):
                                call_connection_obj.play_media(play_sources=[file_source])
                                logging.info(f"Audio playback started (play_media) from: {AUDIO_FILE_URL}")
                                playback_success = True
                            else:
                                raise Exception("Neither play_media_to_all nor play_media methods found")
                                
                        except Exception as play_error:
                            error_str = str(play_error)
                            # Check if it's the "not in Established state" error
                            if "not in Established state" in error_str or "8501" in error_str:
                                retry_count += 1
                                logging.info(f"Call not answered yet, retrying ({retry_count}/{max_retries})...")
                                if retry_count >= max_retries:
                                    logging.warning(f"Call not answered after {max_retries} attempts. Audio playback failed.")
                                    logging.info("Consider using callback-based approach to detect when call is answered")
                            else:
                                # Different error, don't retry
                                raise
                    
                    if not playback_success:
                        logging.warning("Could not play audio - call may not have been answered")
                            
                except Exception as play_error:
                    logging.warning(f"Could not play audio file: {play_error}")
                    logging.error(f"Play error details: {type(play_error).__name__}: {str(play_error)}")
                    import traceback
                    logging.error(traceback.format_exc())
                    logging.info("Call was created but audio playback failed")
            elif AUDIO_FILE_URL:
                logging.warning("Audio file URL configured but FileSource class not available")
            else:
                logging.info("No audio file URL configured - call created without audio playback")
            
            return True
        except Exception as e:
            logging.error(f"Failed to create call: {e}")
            logging.error(f"Error type: {type(e).__name__}")
            import traceback
            logging.error(traceback.format_exc())
            return False
        
    except Exception as e:
        logging.error(f"Error making phone call: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return False


def main(timer: func.TimerRequest) -> None:
    """
    Timer trigger function that runs every minute to check for alarms
    Configure in function.json with schedule: "0 * * * * *" (every minute)
    Note: Time comparisons use -1 hour adjustment for DB timezone alignment
    """
    try:
        # Adjust time -1 hour for DB comparison
        current_time_adjusted = datetime.now() - timedelta(hours=1)
        logging.info(f"Timer trigger executed at {datetime.now()} (DB comparison time: {current_time_adjusted})")
        
        # Check for alarm
        result = check_alarm_in_cosmosdb()
        
        if result is None:
            logging.info("No data found or error checking CosmosDB")
            return
        
        alarm_value, doc = result
        doc_id = str(doc.get('_id', 'unknown'))
        
        # Parse and format timestamp for logging
        timestamp_str = "N/A"
        if 'timestamp' in doc:
            timestamp = parse_timestamp(doc['timestamp'])
            if timestamp:
                timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        
        # Log timestamp and alarm status (visible in log stream)
        logging.info(f"Timestamp last occurrence: {timestamp_str}. Alarm signal: {alarm_value}")
        
        # Check if alarm is triggered
        if alarm_value == 1:
            # Only make call if alarm state changed (avoid duplicate calls)
            if last_alarm_state.get(doc_id) != 1:
                logging.warning(f"⚠️  ALARM TRIGGERED! {ALARM_FIELD} = 1")
                logging.info(f"Document ID: {doc_id}")
                
                # Make phone call with custom message
                alarm_message = "Hi Operator, this is the Bawat Container. There is a Safety Alarm. Please attend."
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
    except Exception as e:
        logging.error(f"Error in monitor_timer_trigger: {e}")
        import traceback
        logging.error(traceback.format_exc())


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


