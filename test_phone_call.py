"""
Simple test script to make a phone call
"""

import os
import json
from azure.communication.callautomation import CallAutomationClient, PhoneNumberIdentifier

# Load configuration
config_path = os.path.join(os.path.dirname(__file__), "local_data.json")
with open(config_path, 'r') as f:
    config = json.load(f)

COMMUNICATION_SERVICE_CONNECTION_STRING = config.get("communication_service_connection_string")
PHONE_NUMBER_TO_CALL = config.get("phone_number_to_call")
COMMUNICATION_SERVICE_PHONE_NUMBER = config.get("communication_service_phone_number")

print("=" * 80)
print("Testing Phone Call")
print("=" * 80)
print(f"Connection String: {COMMUNICATION_SERVICE_CONNECTION_STRING[:50]}...")
print(f"Phone Number to Call: {PHONE_NUMBER_TO_CALL}")
print(f"Source Phone Number: {COMMUNICATION_SERVICE_PHONE_NUMBER}")
print()

try:
    # Initialize Call Automation Client
    call_automation_client = CallAutomationClient.from_connection_string(
        COMMUNICATION_SERVICE_CONNECTION_STRING
    )
    
    print("Creating phone call...")
    
    # Convert phone numbers to PhoneNumberIdentifier
    target_phone = PhoneNumberIdentifier(PHONE_NUMBER_TO_CALL)
    source_phone = PhoneNumberIdentifier(COMMUNICATION_SERVICE_PHONE_NUMBER)
    
    # Create call
    callback_url = "https://localhost/api/callbacks"  # Dummy URL for testing
    
    print(f"   Target: {target_phone}")
    print(f"   Source: {source_phone}")
    print(f"   Callback URL: {callback_url}")
    print()
    
    call_connection = call_automation_client.create_call(
        target_participant=target_phone,
        callback_url=callback_url,
        source_caller_id_number=source_phone
    )
    
    print(f"[SUCCESS] Call initiated successfully!")
    print(f"   Call Connection ID: {call_connection.call_connection_id}")
    
except Exception as e:
    print(f"[ERROR] Error: {e}")
    print(f"   Error type: {type(e).__name__}")
    import traceback
    traceback.print_exc()

