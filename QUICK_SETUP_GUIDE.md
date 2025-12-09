# Quick Setup Guide - Azure Function App from GitHub

Since you're creating the Function App manually in Azure Portal, follow these steps:

## Step 1: Create Function App in Azure Portal

1. Go to [Azure Portal](https://portal.azure.com)
2. Click **Create a resource** → Search for **Function App**
3. Fill in the details:
   - **Subscription**: Your subscription
   - **Resource Group**: `Secomea`
   - **Function App name**: Choose a unique name (e.g., `alarm-baas-function`)
   - **Publish**: Code
   - **Runtime stack**: Python
   - **Version**: 3.11
   - **Region**: Choose your region (e.g., North Europe or Germany West Central)
   - **Operating System**: Linux (required for Python)
   - **Plan type**: Consumption (Serverless)
4. Click **Review + create** → **Create**

## Step 2: Connect to GitHub

1. Once the Function App is created, go to your Function App in Azure Portal
2. Navigate to **Deployment Center** (in the left menu)
3. Select **GitHub** as the source
4. Click **Authorize** and sign in to GitHub
5. Configure:
   - **Organization**: `Bullcarrier`
   - **Repository**: `AlarmBaaS`
   - **Branch**: `main`
   - **Runtime stack**: Python
   - **Version**: 3.11
6. Click **Save**
7. Wait for the deployment to complete (you'll see deployment logs)

## Step 3: Configure Environment Variables

1. In your Function App, go to **Configuration** → **Application settings**
2. Click **+ New application setting** for each of the following:

| Setting Name | Value from local_data.json |
|-------------|---------------------------|
| `MongoDBConnectionString` | `mongodb_connection_string` |
| `COSMOS_DATABASE` | `cosmos_database` (secomeadb) |
| `COSMOS_COLLECTION` | `cosmos_collection` |
| `ALARM_FIELD` | `alarm_field` (Test2OPCUA:CallOperator) |
| `PHONE_NUMBER_TO_CALL` | `phone_number_to_call` |
| `COMMUNICATION_SERVICE_CONNECTION_STRING` | `communication_service_connection_string` |
| `COMMUNICATION_SERVICE_PHONE_NUMBER` | `communication_service_phone_number` |
| `CALLBACK_URL` | Leave empty or set to `https://your-function-app-name.azurewebsites.net/api/callbacks` |
| `FUNCTIONS_WORKER_RUNTIME` | `python` |
| `FUNCTIONS_EXTENSION_VERSION` | `~4` |

3. Click **Save** (this will restart the Function App)

## Step 4: Verify Deployment

1. Go to **Functions** in your Function App
2. You should see `monitor_timer_trigger` function
3. Check the **Code + Test** tab to verify the code is deployed
4. Go to **Monitor** to see execution logs

## Step 5: Test the Function

1. The function runs every minute (configured in `function.json`)
2. Check **Monitor** tab to see if it's executing
3. Check **Logs** for any errors
4. Verify it's connecting to CosmosDB and checking for alarms

## Troubleshooting

- **Function not appearing**: Check Deployment Center logs for deployment errors
- **Import errors**: Verify `requirements.txt` is being installed (check deployment logs)
- **Connection errors**: Verify all environment variables are set correctly
- **Function not running**: Check the timer trigger schedule in `function.json`

## Your Configuration Values

Based on your `local_data.json`:

- **MongoDBConnectionString**: `mongodb://secomeadb:***@secomeadb.documents.azure.com:10255/?ssl=true&replicaSet=globaldb`
- **COSMOS_DATABASE**: `secomeadb`
- **COSMOS_COLLECTION**: `YourCollectionName` (update this to your actual collection name)
- **ALARM_FIELD**: `Test2OPCUA:CallOperator`
- **PHONE_NUMBER_TO_CALL**: `+4550304427`
- **COMMUNICATION_SERVICE_CONNECTION_STRING**: `endpoint=https://alarmcontainer.europe.communication.azure.com/;accesskey=***`
- **COMMUNICATION_SERVICE_PHONE_NUMBER**: `+4588744478`

**Important**: Update `COSMOS_COLLECTION` to your actual collection name in Azure Portal!

