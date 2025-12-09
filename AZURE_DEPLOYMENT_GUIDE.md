# Azure Function App Deployment Guide

This guide will help you deploy the Alarm Monitor Function to Azure.

## Prerequisites

1. Azure subscription
2. Azure PowerShell modules installed
3. GitHub repository: https://github.com/Bullcarrier/AlarmBaaS

## Step 1: Configure local_data.json

Update `local_data.json` with your actual values:

```json
{
  "github_token": "your_github_token",
  "phone_number_to_call": "+1234567890",
  "communication_service_connection_string": "endpoint=https://...",
  "communication_service_phone_number": "+1234567890",
  "mongodb_connection_string": "mongodb://...",
  "cosmos_database": "secomeadb",
  "cosmos_collection": "YourCollectionName",
  "alarm_field": "Test2OPCUA:CallOperator",
  "callback_url": "https://your-function-app.azurewebsites.net/api/callbacks"
}
```

## Step 2: Login to Azure

```powershell
Connect-AzAccount
```

If browser authentication doesn't work, use device code:
```powershell
Connect-AzAccount -DeviceCode
```

## Step 3: Run Deployment Script

```powershell
.\deploy_to_azure.ps1
```

Or with custom parameters:
```powershell
.\deploy_to_azure.ps1 -ResourceGroupName "my-rg" -FunctionAppName "my-function-app" -Location "West Europe"
```

## Step 4: Configure GitHub Deployment

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to your Function App
3. Go to **Deployment Center**
4. Select **GitHub** as source
5. Authorize and select:
   - Organization: `Bullcarrier`
   - Repository: `AlarmBaaS`
   - Branch: `main`
6. Click **Save**

## Step 5: Verify Deployment

1. Go to **Functions** in your Function App
2. You should see `monitor_timer_trigger` function
3. Check **Logs** to verify it's running
4. Test by checking CosmosDB for alarm conditions

## Manual Deployment via Azure Portal

If you prefer to use the Azure Portal:

### Create Function App

1. Go to [Azure Portal](https://portal.azure.com)
2. Click **Create a resource**
3. Search for **Function App**
4. Fill in:
   - **Subscription**: Your subscription
   - **Resource Group**: Create new or use existing
   - **Function App name**: `alarm-baas-function` (must be globally unique)
   - **Publish**: Code
   - **Runtime stack**: Python
   - **Version**: 3.11
   - **Region**: Your preferred region
5. Click **Review + create** then **Create**

### Configure GitHub Deployment

1. In your Function App, go to **Deployment Center**
2. Select **GitHub**
3. Authorize GitHub
4. Select:
   - Organization: `Bullcarrier`
   - Repository: `AlarmBaaS`
   - Branch: `main`
5. Click **Save**

### Set Environment Variables

1. Go to **Configuration** > **Application settings**
2. Add the following settings:

| Setting Name | Value |
|-------------|-------|
| `MongoDBConnectionString` | Your CosmosDB connection string |
| `COSMOS_DATABASE` | `secomeadb` |
| `COSMOS_COLLECTION` | Your collection name |
| `ALARM_FIELD` | `Test2OPCUA:CallOperator` |
| `PHONE_NUMBER_TO_CALL` | Phone number to call (e.g., +1234567890) |
| `COMMUNICATION_SERVICE_CONNECTION_STRING` | Azure Communication Services connection string |
| `COMMUNICATION_SERVICE_PHONE_NUMBER` | Your Communication Services phone number |
| `CALLBACK_URL` | `https://your-function-app.azurewebsites.net/api/callbacks` |
| `FUNCTIONS_WORKER_RUNTIME` | `python` |
| `FUNCTIONS_EXTENSION_VERSION` | `~4` |

3. Click **Save**

## Troubleshooting

### Function not appearing
- Check that the function code is in the `alarm_monitor_function` folder
- Verify `function.json` is correctly configured
- Check deployment logs in **Deployment Center**

### Environment variables not working
- Ensure all variables are set in **Configuration** > **Application settings**
- Restart the Function App after adding variables
- Check function logs for errors

### GitHub deployment fails
- Verify GitHub token has correct permissions
- Check that the repository is accessible
- Review deployment logs in **Deployment Center**

## Next Steps

1. Monitor function execution in **Functions** > **monitor_timer_trigger** > **Monitor**
2. Set up Application Insights for better logging
3. Configure alerts for function failures
4. Test the alarm trigger by updating CosmosDB

