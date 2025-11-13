# Simplified script to create Azure Function App using REST API
# This script will guide you through the process

param(
    [string]$SubscriptionId = "",
    [string]$ResourceGroupName = "alarm-baas-rg",
    [string]$FunctionAppName = "alarm-baas-function",
    [string]$Location = "westeurope"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Azure Function App Creation Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Azure login
Write-Host "Step 1: Checking Azure authentication..." -ForegroundColor Yellow
try {
    $context = Get-AzContext -ErrorAction Stop
    Write-Host "✓ Logged in as: $($context.Account.Id)" -ForegroundColor Green
    if (-not $SubscriptionId) {
        $SubscriptionId = $context.Subscription.Id
    }
} catch {
    Write-Host "✗ Not logged in to Azure" -ForegroundColor Red
    Write-Host "Please run: Connect-AzAccount -DeviceCode" -ForegroundColor Yellow
    exit 1
}

# Load configuration
Write-Host "`nStep 2: Loading configuration..." -ForegroundColor Yellow
$configPath = Join-Path $PSScriptRoot "local_data.json"
if (-not (Test-Path $configPath)) {
    Write-Host "✗ local_data.json not found" -ForegroundColor Red
    exit 1
}
$jsonContent = Get-Content $configPath -Raw
$config = $jsonContent | ConvertFrom-Json
Write-Host "✓ Configuration loaded" -ForegroundColor Green

# Validate required fields
Write-Host "`nStep 3: Validating configuration..." -ForegroundColor Yellow
$requiredFields = @(
    "mongodb_connection_string",
    "cosmos_collection",
    "phone_number_to_call",
    "communication_service_connection_string",
    "communication_service_phone_number"
)

$missingFields = @()
foreach ($field in $requiredFields) {
    $value = $config.$field
    if ([string]::IsNullOrWhiteSpace($value)) {
        $missingFields += $field
    } else {
        Write-Host "  ✓ $field : configured" -ForegroundColor Green
    }
}

if ($missingFields.Count -gt 0) {
    Write-Host "✗ Missing required fields in local_data.json:" -ForegroundColor Red
    foreach ($field in $missingFields) {
        Write-Host "  - $field" -ForegroundColor Red
    }
    Write-Host "`nPlease update local_data.json with the required values." -ForegroundColor Yellow
    exit 1
}
Write-Host "✓ All required fields present" -ForegroundColor Green

# Generate unique function app name if needed
if ($FunctionAppName -eq "alarm-baas-function") {
    $timestamp = Get-Date -Format "yyyyMMddHHmmss"
    $FunctionAppName = "alarm-baas-$timestamp"
    Write-Host "`nGenerated unique function app name: $FunctionAppName" -ForegroundColor Cyan
}

# Ensure function app name is valid (lowercase, alphanumeric and hyphens only, max 60 chars)
$FunctionAppName = $FunctionAppName.ToLower() -replace '[^a-z0-9-]', ''
if ($FunctionAppName.Length -gt 60) {
    $FunctionAppName = $FunctionAppName.Substring(0, 60)
}

# Create Resource Group
Write-Host "`nStep 4: Creating/Verifying Resource Group..." -ForegroundColor Yellow
$rg = Get-AzResourceGroup -Name $ResourceGroupName -ErrorAction SilentlyContinue
if (-not $rg) {
    try {
        $rg = New-AzResourceGroup -Name $ResourceGroupName -Location $Location
        Write-Host "✓ Resource Group created: $ResourceGroupName" -ForegroundColor Green
    } catch {
        Write-Host "✗ Error creating Resource Group: $_" -ForegroundColor Red
        Write-Host "  The resource group may already exist or you may need to select a subscription." -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "✓ Resource Group already exists: $ResourceGroupName" -ForegroundColor Green
    $Location = $rg.Location
}

# Create Storage Account
Write-Host "`nStep 5: Creating Storage Account..." -ForegroundColor Yellow
# Storage account names must be 3-24 chars, lowercase, alphanumeric only
$storageBase = ($FunctionAppName -replace '[^a-z0-9]', '')
if ($storageBase.Length -gt 20) {
    $storageBase = $storageBase.Substring(0, 20)
}
$storageName = $storageBase + "stor"
if ($storageName.Length -gt 24) {
    $storageName = $storageName.Substring(0, 24)
}
$storage = Get-AzStorageAccount -ResourceGroupName $ResourceGroupName -Name $storageName -ErrorAction SilentlyContinue
if (-not $storage) {
    $storage = New-AzStorageAccount -ResourceGroupName $ResourceGroupName `
        -Name $storageName `
        -Location $Location `
        -SkuName Standard_LRS
    Write-Host "✓ Storage Account created: $storageName" -ForegroundColor Green
} else {
    Write-Host "✓ Storage Account already exists: $storageName" -ForegroundColor Green
}

# Create App Service Plan
Write-Host "`nStep 6: Creating App Service Plan..." -ForegroundColor Yellow
$planName = "$FunctionAppName-plan"
$plan = Get-AzAppServicePlan -ResourceGroupName $ResourceGroupName -Name $planName -ErrorAction SilentlyContinue
if (-not $plan) {
    $plan = New-AzAppServicePlan -ResourceGroupName $ResourceGroupName `
        -Name $planName `
        -Location $Location `
        -Tier "Dynamic" `
        -NumberofWorkers 0
    Write-Host "✓ App Service Plan created: $planName" -ForegroundColor Green
} else {
    Write-Host "✓ App Service Plan already exists: $planName" -ForegroundColor Green
}

# Create Function App
Write-Host "`nStep 7: Creating Function App..." -ForegroundColor Yellow
$functionApp = Get-AzFunctionApp -ResourceGroupName $ResourceGroupName -Name $FunctionAppName -ErrorAction SilentlyContinue
if (-not $functionApp) {
    try {
        $functionApp = New-AzFunctionApp -ResourceGroupName $ResourceGroupName `
            -Name $FunctionAppName `
            -StorageAccountName $storageName `
            -PlanName $planName `
            -Runtime "Python" `
            -RuntimeVersion "3.11" `
            -FunctionsVersion "4" `
            -OSType "Linux"
        Write-Host "✓ Function App created: $FunctionAppName" -ForegroundColor Green
    } catch {
        Write-Host "✗ Error creating Function App: $_" -ForegroundColor Red
        Write-Host "  Trying with Windows OS type..." -ForegroundColor Yellow
        try {
            $functionApp = New-AzFunctionApp -ResourceGroupName $ResourceGroupName `
                -Name $FunctionAppName `
                -StorageAccountName $storageName `
                -PlanName $planName `
                -Runtime "Python" `
                -RuntimeVersion "3.11" `
                -FunctionsVersion "4" `
                -OSType "Windows"
            Write-Host "✓ Function App created with Windows OS: $FunctionAppName" -ForegroundColor Green
        } catch {
            Write-Host "✗ Failed to create Function App: $_" -ForegroundColor Red
            Write-Host "  Please check the error message above and try creating manually in Azure Portal." -ForegroundColor Yellow
            exit 1
        }
    }
} else {
    Write-Host "✓ Function App already exists: $FunctionAppName" -ForegroundColor Green
}

# Set Application Settings
Write-Host "`nStep 8: Configuring environment variables..." -ForegroundColor Yellow
if ($functionApp) {
    $appSettings = @{
        "MongoDBConnectionString" = $config.mongodb_connection_string
        "COSMOS_DATABASE" = $config.cosmos_database
        "COSMOS_COLLECTION" = $config.cosmos_collection
        "ALARM_FIELD" = $config.alarm_field
        "PHONE_NUMBER_TO_CALL" = $config.phone_number_to_call
        "COMMUNICATION_SERVICE_CONNECTION_STRING" = $config.communication_service_connection_string
        "COMMUNICATION_SERVICE_PHONE_NUMBER" = $config.communication_service_phone_number
        "CALLBACK_URL" = if ($config.callback_url) { $config.callback_url } else { "https://$FunctionAppName.azurewebsites.net/api/callbacks" }
        "FUNCTIONS_WORKER_RUNTIME" = "python"
        "FUNCTIONS_EXTENSION_VERSION" = "~4"
        "WEBSITE_RUN_FROM_PACKAGE" = "1"
    }

    try {
        Update-AzFunctionAppSetting -ResourceGroupName $ResourceGroupName `
            -Name $FunctionAppName `
            -AppSetting $appSettings
        Write-Host "✓ Environment variables configured" -ForegroundColor Green
    } catch {
        Write-Host "✗ Error setting environment variables: $_" -ForegroundColor Red
        Write-Host "  You can set them manually in Azure Portal:" -ForegroundColor Yellow
        Write-Host "  Portal -> Function App -> Configuration -> Application settings" -ForegroundColor Cyan
    }
} else {
    Write-Host "✗ Function App not found. Cannot set environment variables." -ForegroundColor Red
}

# Summary
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "Function App Name: $FunctionAppName" -ForegroundColor Cyan
Write-Host "Function App URL: https://$FunctionAppName.azurewebsites.net" -ForegroundColor Cyan
Write-Host "Resource Group: $ResourceGroupName" -ForegroundColor Cyan
Write-Host "`nNext Steps:" -ForegroundColor Yellow
Write-Host "1. Go to Azure Portal: https://portal.azure.com" -ForegroundColor White
Write-Host "2. Navigate to your Function App: $FunctionAppName" -ForegroundColor White
Write-Host "3. Go to Deployment Center" -ForegroundColor White
Write-Host "4. Select GitHub as source" -ForegroundColor White
Write-Host "5. Connect to: https://github.com/Bullcarrier/AlarmBaaS" -ForegroundColor White
Write-Host "6. Select branch: main" -ForegroundColor White
Write-Host "7. Save and wait for deployment" -ForegroundColor White
Write-Host "`nYour function will be deployed automatically from GitHub!" -ForegroundColor Green

