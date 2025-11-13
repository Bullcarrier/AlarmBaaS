# Script to create and deploy Azure Function App from GitHub
param(
    [string]$ResourceGroupName = "alarm-baas-rg",
    [string]$FunctionAppName = "alarm-baas-function",
    [string]$Location = "West Europe",
    [string]$StorageAccountName = "alarmbaasstorage",
    [string]$AppServicePlanName = "alarm-baas-plan",
    [string]$GitHubRepo = "https://github.com/Bullcarrier/AlarmBaaS.git",
    [string]$GitHubBranch = "main"
)

# Check if logged in to Azure
Write-Host "Checking Azure login status..." -ForegroundColor Yellow
try {
    $context = Get-AzContext -ErrorAction Stop
    Write-Host "Logged in as: $($context.Account.Id)" -ForegroundColor Green
} catch {
    Write-Host "Not logged in to Azure. Please run: Connect-AzAccount" -ForegroundColor Red
    exit 1
}

# Load configuration from local_data.json
$configPath = Join-Path $PSScriptRoot "local_data.json"
if (-not (Test-Path $configPath)) {
    Write-Host "local_data.json not found. Please create it first." -ForegroundColor Red
    exit 1
}

$config = Get-Content $configPath | ConvertFrom-Json
Write-Host "Configuration loaded from local_data.json" -ForegroundColor Green

# Create Resource Group
Write-Host "`nCreating Resource Group: $ResourceGroupName..." -ForegroundColor Yellow
$rg = Get-AzResourceGroup -Name $ResourceGroupName -ErrorAction SilentlyContinue
if (-not $rg) {
    $rg = New-AzResourceGroup -Name $ResourceGroupName -Location $Location
    Write-Host "Resource Group created." -ForegroundColor Green
} else {
    Write-Host "Resource Group already exists." -ForegroundColor Green
}

# Create Storage Account
Write-Host "`nCreating Storage Account: $StorageAccountName..." -ForegroundColor Yellow
$storage = Get-AzStorageAccount -ResourceGroupName $ResourceGroupName -Name $StorageAccountName -ErrorAction SilentlyContinue
if (-not $storage) {
    $storage = New-AzStorageAccount -ResourceGroupName $ResourceGroupName `
        -Name $StorageAccountName `
        -Location $Location `
        -SkuName Standard_LRS
    Write-Host "Storage Account created." -ForegroundColor Green
} else {
    Write-Host "Storage Account already exists." -ForegroundColor Green
}

# Create App Service Plan (Consumption Plan for serverless)
Write-Host "`nCreating App Service Plan: $AppServicePlanName..." -ForegroundColor Yellow
$plan = Get-AzAppServicePlan -ResourceGroupName $ResourceGroupName -Name $AppServicePlanName -ErrorAction SilentlyContinue
if (-not $plan) {
    $plan = New-AzAppServicePlan -ResourceGroupName $ResourceGroupName `
        -Name $AppServicePlanName `
        -Location $Location `
        -Tier "Dynamic" `
        -NumberofWorkers 0
    Write-Host "App Service Plan created." -ForegroundColor Green
} else {
    Write-Host "App Service Plan already exists." -ForegroundColor Green
}

# Create Function App
Write-Host "`nCreating Function App: $FunctionAppName..." -ForegroundColor Yellow
$functionApp = Get-AzFunctionApp -ResourceGroupName $ResourceGroupName -Name $FunctionAppName -ErrorAction SilentlyContinue
if (-not $functionApp) {
    $functionApp = New-AzFunctionApp -ResourceGroupName $ResourceGroupName `
        -Name $FunctionAppName `
        -StorageAccountName $StorageAccountName `
        -PlanName $AppServicePlanName `
        -Runtime "Python" `
        -RuntimeVersion "3.11" `
        -FunctionsVersion "4"
    Write-Host "Function App created." -ForegroundColor Green
} else {
    Write-Host "Function App already exists." -ForegroundColor Green
}

# Configure GitHub deployment
Write-Host "`nConfiguring GitHub deployment..." -ForegroundColor Yellow
try {
    # Get GitHub token from local_data.json
    $githubToken = $config.github_token
    
    if ($githubToken) {
        # Set deployment source to GitHub
        $properties = @{
            repoUrl = $GitHubRepo
            branch = $GitHubBranch
            isManualIntegration = $false
        }
        
        # Note: This requires additional setup. For now, we'll set environment variables
        # and you can configure GitHub deployment from Azure Portal
        Write-Host "GitHub deployment can be configured from Azure Portal:" -ForegroundColor Cyan
        Write-Host "  Portal -> Function App -> Deployment Center -> GitHub" -ForegroundColor Cyan
        Write-Host "  Repository: $GitHubRepo" -ForegroundColor Cyan
        Write-Host "  Branch: $GitHubBranch" -ForegroundColor Cyan
    }
} catch {
    Write-Host "Warning: Could not configure GitHub deployment automatically." -ForegroundColor Yellow
}

# Set Application Settings (Environment Variables)
Write-Host "`nSetting environment variables..." -ForegroundColor Yellow

$appSettings = @{
    "MongoDBConnectionString" = $config.mongodb_connection_string
    "COSMOS_DATABASE" = $config.cosmos_database
    "COSMOS_COLLECTION" = $config.cosmos_collection
    "ALARM_FIELD" = $config.alarm_field
    "PHONE_NUMBER_TO_CALL" = $config.phone_number_to_call
    "COMMUNICATION_SERVICE_CONNECTION_STRING" = $config.communication_service_connection_string
    "COMMUNICATION_SERVICE_PHONE_NUMBER" = $config.communication_service_phone_number
    "CALLBACK_URL" = $config.callback_url
    "FUNCTIONS_WORKER_RUNTIME" = "python"
    "FUNCTIONS_EXTENSION_VERSION" = "~4"
    "WEBSITE_RUN_FROM_PACKAGE" = "1"
}

# Update app settings
Update-AzFunctionAppSetting -ResourceGroupName $ResourceGroupName `
    -Name $FunctionAppName `
    -AppSetting $appSettings

Write-Host "Environment variables configured." -ForegroundColor Green

# Display summary
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Deployment Summary" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "Resource Group: $ResourceGroupName" -ForegroundColor Cyan
Write-Host "Function App: $FunctionAppName" -ForegroundColor Cyan
Write-Host "Function App URL: https://$FunctionAppName.azurewebsites.net" -ForegroundColor Cyan
Write-Host "`nNext Steps:" -ForegroundColor Yellow
Write-Host "1. Configure GitHub deployment from Azure Portal" -ForegroundColor White
Write-Host "2. Update local_data.json with your actual values:" -ForegroundColor White
Write-Host "   - MongoDBConnectionString" -ForegroundColor White
Write-Host "   - COSMOS_COLLECTION" -ForegroundColor White
Write-Host "   - PHONE_NUMBER_TO_CALL" -ForegroundColor White
Write-Host "   - COMMUNICATION_SERVICE_CONNECTION_STRING" -ForegroundColor White
Write-Host "   - COMMUNICATION_SERVICE_PHONE_NUMBER" -ForegroundColor White
Write-Host "3. Re-run this script to update environment variables" -ForegroundColor White
Write-Host "`nOr update settings manually in Azure Portal:" -ForegroundColor Yellow
Write-Host "  Portal -> Function App -> Configuration -> Application settings" -ForegroundColor Cyan

