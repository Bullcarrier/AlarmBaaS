"""
Azure Function App to monitor CosmosDB for Test2OPCUA:CallOperator and make phone calls
"""

import logging
import os
import json
import time
from datetime import datetime, timedelta
import azure.functions as func
from pymongo import MongoClient
from bson import ObjectId
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
COSMOS_COLLECTION = os.environ.get("COSMOS_COLLECTION", "iotmessages")
ALARM_FIELD = os.environ.get("ALARM_FIELD", "Test2OPCUA:CallOperator")
CALL_SERVICE_FIELD = os.environ.get("CALL_SERVICE_FIELD", "Test2OPCUA:CallService")
VOLUME_TREATED_FIELD = os.environ.get("VOLUME_TREATED_FIELD", "Test2OPCUA:VolumeTreated")
PHONE_NUMBER_TO_CALL = os.environ.get("PHONE_NUMBER_TO_CALL")
COMMUNICATION_SERVICE_CONNECTION_STRING = os.environ.get("COMMUNICATION_SERVICE_CONNECTION_STRING")
COMMUNICATION_SERVICE_PHONE_NUMBER = os.environ.get("COMMUNICATION_SERVICE_PHONE_NUMBER")
CALLBACK_URL = os.environ.get("CALLBACK_URL", "")
AUDIO_FILE_URL = os.environ.get("AUDIO_FILE_URL", "")  # URL to pre-recorded WAV file

# Track last alarm state and last call time (per function instance)
last_alarm_state = {}
last_call_time = {}


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


def get_document_time(doc):
    """
    Get a datetime for a document, using 'timestamp' when present,
    otherwise falling back to the ObjectId generation time.
    """
    if not doc:
        return None

    # First try explicit 'timestamp' field
    if "timestamp" in doc:
        ts = parse_timestamp(doc["timestamp"])
        if ts:
            return ts

    # Fallback: use ObjectId generation time
    try:
        _id = doc.get("_id")
        if isinstance(_id, ObjectId):
            return _id.generation_time
        if isinstance(_id, str):
            return ObjectId(_id).generation_time
    except Exception as e:
        logging.debug(f"Could not derive time from _id: {e}")

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
        
        # Get the two most recent documents (latest and previous)
        cursor = collection.find().sort("_id", -1).limit(2)
        docs = list(cursor)
        latest_doc = docs[0] if docs else None
        previous_doc = docs[1] if len(docs) > 1 else None
        
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
        
        # Get best-effort document time for logging
        latest_time = get_document_time(latest_doc)
        
        logging.info(f"Latest document: ID={latest_doc.get('_id')}, Alarm={alarm_value}, Timestamp={latest_time}")
        
        return alarm_value, latest_doc, previous_doc
        
    except Exception as e:
        logging.error(f"Error checking CosmosDB: {e}")
        return None


def get_phone_number_from_database():
    """Get phone number from Operator collection in IoTDatabase"""
    try:
        if not MONGODB_CONNECTION_STRING:
            logging.error("MongoDBConnectionString not configured")
            return None
        
        # Connect to CosmosDB
        client = MongoClient(MONGODB_CONNECTION_STRING)
        db = client[COSMOS_DATABASE]
        operator_collection = db["Operator"]
        
        # Get the document from Operator collection (there should only be one)
        latest_doc = operator_collection.find_one()
        
        if not latest_doc:
            logging.error("No documents found in Operator collection")
            return None
        
        # Extract country code and phone number
        country_code = latest_doc.get("Test2OPCUA:Country", "")
        phone_number = latest_doc.get("Test2OPCUA:PhoneNumber", "")
        
        if not country_code or not phone_number:
            logging.error(f"Missing phone number data: Country={country_code}, PhoneNumber={phone_number}")
            return None
        
        # Replace "00" with "+" in country code
        if country_code.startswith("00"):
            country_code = "+" + country_code[2:]
        elif not country_code.startswith("+"):
            country_code = "+" + country_code
        
        # Concatenate country code and phone number
        full_phone_number = country_code + phone_number
        
        logging.info(f"Retrieved phone number from Operator collection: {full_phone_number}")
        return full_phone_number
        
    except Exception as e:
        logging.error(f"Error getting phone number from database: {e}")
        return None


def make_phone_call(message="Hi Operator, this is the Bawat Container. There is a Safety Alarm. Please attend."):
    """Make phone call using Azure Communication Services and play message when answered"""
    try:
        if not COMMUNICATION_SERVICE_CONNECTION_STRING:
            logging.error("Communication Service connection string not configured")
            return False
        
        if not COMMUNICATION_SERVICE_PHONE_NUMBER:
            logging.error("Communication Service phone number not configured")
            return False
        
        # Get phone number from database
        phone_number_to_call = get_phone_number_from_database()
        
        if not phone_number_to_call:
            logging.error("Could not retrieve phone number from Operator collection")
            # Fallback to environment variable if available
            if PHONE_NUMBER_TO_CALL:
                phone_number_to_call = PHONE_NUMBER_TO_CALL
                logging.info(f"Using fallback phone number from environment variable: {phone_number_to_call}")
            else:
                logging.error("No phone number available from database or environment variable")
                return False
        
        # Initialize Call Automation Client
        call_automation_client = CallAutomationClient.from_connection_string(
            COMMUNICATION_SERVICE_CONNECTION_STRING
        )
        
        logging.info(f"Making phone call to {phone_number_to_call}...")
        
        # Create call
        try:
            # Convert phone numbers to PhoneNumberIdentifier objects
            target_phone = PhoneNumberIdentifier(phone_number_to_call)
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
        # Adjust time -1 hour for DB comparison (naive UTC)
        now_utc = datetime.utcnow()
        current_time_adjusted = now_utc - timedelta(hours=1)
        logging.info(f"Timer trigger executed at {now_utc} (DB comparison time: {current_time_adjusted})")
        
        # Check for alarm
        result = check_alarm_in_cosmosdb()
        
        if result is None:
            logging.info("No data found or error checking CosmosDB")
            return
        
        alarm_value, doc, previous_doc = result
        doc_id = str(doc.get('_id', 'unknown'))
        
        # Parse and format timestamp for logging (using timestamp field or _id fallback)
        timestamp_str = "N/A"
        timestamp = get_document_time(doc)
        if timestamp:
            # Normalize to naive for consistent arithmetic
            if getattr(timestamp, "tzinfo", None) is not None:
                timestamp = timestamp.replace(tzinfo=None)
            timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")

        # Compute age of latest message relative to now (per-run age) — use now_utc so age is positive
        age_seconds = None
        if timestamp:
            age_seconds = (now_utc - timestamp).total_seconds()
            logging.info(f"Age of latest message (seconds) = {int(age_seconds)}")

        # Calculate and log time since last message if previous document exists
        if previous_doc:
            prev_timestamp = get_document_time(previous_doc)
            if timestamp and prev_timestamp:
                if getattr(prev_timestamp, "tzinfo", None) is not None:
                    prev_timestamp = prev_timestamp.replace(tzinfo=None)
                time_since_last_message = (timestamp - prev_timestamp).total_seconds()
                if time_since_last_message >= 0:
                    logging.info(f"Time since last message (seconds) = {int(time_since_last_message)}")
        
        # Log timestamp and alarm status (visible in log stream)
        call_service_value = doc.get(CALL_SERVICE_FIELD, 0)
        logging.info(f"Timestamp last occurrence: {timestamp_str}. Alarm signal: {alarm_value}, CallService: {call_service_value}")

        # Log VolumeTreated field for visibility
        volume_treated_value = doc.get(VOLUME_TREATED_FIELD)
        logging.info(f"Volume treated ({VOLUME_TREATED_FIELD}) = {volume_treated_value}")

        # Determine if alarm should be considered active:
        # 1) Normal case: Alarm field is 1 and CallService is 1
        # 2) Signal-loss case: message age > 120s and CallService is 1 (treat as alarm)
        is_alarm_active = (alarm_value == 1 and call_service_value == 1)
        if age_seconds is not None and age_seconds > 120 and call_service_value == 1:
            logging.warning(
                f"⚠️  Alarm forced due to signal loss: age={int(age_seconds)}s, CallService={call_service_value}"
            )
            is_alarm_active = True
        
        # Check if alarm is triggered (normal or signal-loss)
        if is_alarm_active:
            global last_call_time

            # Enforce a 5-minute cooldown between successful calls while alarm is active
            cooldown_seconds = 300
            last_call = last_call_time.get("global_alarm")
            if last_call is not None:
                elapsed_since_call = (now_utc - last_call).total_seconds()
                if elapsed_since_call < cooldown_seconds:
                    remaining = int(cooldown_seconds - elapsed_since_call)
                    logging.info(
                        f"Alarm active but call cooldown in effect "
                        f"(next possible call in {remaining} seconds)"
                    )
                    # Mark that we've already notified for this alarm state
                    last_alarm_state[doc_id] = 1
                    return

            # Only make call if alarm state changed (avoid duplicate calls per document)
            if last_alarm_state.get(doc_id) != 1:
                logging.warning(f"⚠️  ALARM TRIGGERED! {ALARM_FIELD} = 1")
                logging.info(f"Document ID: {doc_id}")

                # Make phone call with custom message
                alarm_message = "Hi Operator, this is the Bawat Container. There is a Safety Alarm. Please attend."
                call_success = make_phone_call(alarm_message)

                if call_success:
                    # Treat successful initiation as answered and start cooldown
                    last_alarm_state[doc_id] = 1
                    last_call_time["global_alarm"] = now_utc
                else:
                    # Call failed or was rejected before establishing - retry next cycle
                    logging.error("Phone call failed or not established; will retry while alarm remains active")
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
            call_service_value = doc_dict.get(CALL_SERVICE_FIELD, 0)
            doc_id = str(doc_dict.get('_id', 'unknown'))
            
            if alarm_value == 1 and call_service_value == 1:
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


