# Alarm Monitor Function

Azure Function App to monitor CosmosDB for alarm conditions and make phone calls using Azure Communication Services.

## Features

- Monitors CosmosDB for alarm conditions (Test2OPCUA:CommonAlarm)
- Makes automated phone calls when alarms are triggered
- Timer-based polling (runs every minute)
- Prevents duplicate notifications for the same alarm

## Configuration

The function requires the following environment variables:

- `MongoDBConnectionString` - Connection string to CosmosDB
- `COSMOS_DATABASE` - Database name (default: "secomeadb")
- `COSMOS_COLLECTION` - Collection name
- `ALARM_FIELD` - Field name to monitor (default: "Test2OPCUA:CommonAlarm")
- `PHONE_NUMBER_TO_CALL` - Phone number to call when alarm is triggered
- `COMMUNICATION_SERVICE_CONNECTION_STRING` - Azure Communication Services connection string
- `COMMUNICATION_SERVICE_PHONE_NUMBER` - Phone number from Azure Communication Services
- `CALLBACK_URL` - Optional callback URL for call events

## Deployment

This function can be deployed to Azure Functions using:
- GitHub Actions
- Azure DevOps
- Azure Portal (direct deployment from GitHub)

## Function Structure

- `__init__.py` - Main function code
- `function.json` - Function binding configuration
- `host.json` - Host configuration
- `requirements.txt` - Python dependencies

