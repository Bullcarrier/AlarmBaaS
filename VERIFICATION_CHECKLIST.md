# Function App Verification Checklist

## ✅ Status: Function App is Running!

**Function App Name:** `BaasCall`  
**Resource Group:** `Secomea`  
**URL:** `https://baascall-dgbpdxesgsg2hscy.northeurope-01.azurewebsites.net`

## ✅ Application Settings - All Configured!

All required settings are present:
- ✅ MongoDBConnectionString
- ✅ COSMOS_DATABASE
- ✅ COSMOS_COLLECTION
- ✅ ALARM_FIELD
- ✅ PHONE_NUMBER_TO_CALL
- ✅ COMMUNICATION_SERVICE_CONNECTION_STRING
- ✅ COMMUNICATION_SERVICE_PHONE_NUMBER

## Next: Verify Function is Deployed and Running

### Step 1: Check if Function is Deployed

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to: **Secomea** → **BaasCall** → **Functions**
3. You should see: **monitor_timer_trigger**

**If you don't see the function:**
- Go to **Deployment Center** and check deployment status
- Verify GitHub connection is working
- Check deployment logs for errors

### Step 2: Check Function Execution

1. Click on **monitor_timer_trigger** function
2. Go to **Monitor** tab
3. You should see execution history (function runs every minute)
4. Check for:
   - ✅ Successful executions (green)
   - ⚠️ Failed executions (red) - click to see error details

### Step 3: Check Logs for Errors

1. In the function, go to **Logs** tab
2. Look for:
   - ✅ "Timer trigger executed at..." - means function is running
   - ✅ "Status OK: Test2OPCUA:CommonAlarm = 0" - means it's checking CosmosDB
   - ⚠️ Any error messages (red text)

### Step 4: Common Issues to Check

#### Issue: Function not appearing
**Solution:**
- Check **Deployment Center** → Verify GitHub deployment completed
- Check deployment logs for errors
- Verify code is in `alarm_monitor_function` folder in GitHub

#### Issue: "MongoDBConnectionString not configured"
**Solution:**
- Go to **Configuration** → **Application settings**
- Verify `MongoDBConnectionString` is set correctly
- Click **Save** to restart Function App

#### Issue: "No documents found in collection"
**Solution:**
- Verify `COSMOS_COLLECTION` is set to the correct collection name
- Check that the collection exists in CosmosDB
- Verify `COSMOS_DATABASE` is correct (should be `secomeadb`)

#### Issue: "Communication Service connection string not configured"
**Solution:**
- Verify `COMMUNICATION_SERVICE_CONNECTION_STRING` is set
- Verify `COMMUNICATION_SERVICE_PHONE_NUMBER` is set
- Click **Save** to restart Function App

#### Issue: Function not executing
**Solution:**
- Check **Configuration** → **Application settings**
- Verify `FUNCTIONS_WORKER_RUNTIME` = `python`
- Verify `FUNCTIONS_EXTENSION_VERSION` = `~4`
- Restart the Function App

### Step 5: Test the Alarm

To test if the alarm detection works:

1. Go to your CosmosDB
2. Find a document in your collection
3. Update the `Test2OPCUA:CommonAlarm` field to `1`
4. Wait for the next function execution (within 1 minute)
5. Check the function logs - you should see:
   - "⚠️ ALARM TRIGGERED! Test2OPCUA:CommonAlarm = 1"
   - Phone call attempt logs

## Quick Links

- **Function App:** https://portal.azure.com/#@/resource/subscriptions/*/resourceGroups/Secomea/providers/Microsoft.Web/sites/BaasCall
- **Functions:** https://portal.azure.com/#@/resource/subscriptions/*/resourceGroups/Secomea/providers/Microsoft.Web/sites/BaasCall/functions
- **Configuration:** https://portal.azure.com/#@/resource/subscriptions/*/resourceGroups/Secomea/providers/Microsoft.Web/sites/BaasCall/config
- **Deployment Center:** https://portal.azure.com/#@/resource/subscriptions/*/resourceGroups/Secomea/providers/Microsoft.Web/sites/BaasCall/deploymentCenter

## Summary

✅ Function App is **Running**  
✅ All settings are **Configured**  
⏳ **Next:** Check if function is deployed and executing

If you see the function and it's executing successfully, your code is working! 🎉

