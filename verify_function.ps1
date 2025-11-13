# Script to verify Azure Function App is working
param(
    [string]$ResourceGroupName = "Secomea",
    [string]$FunctionAppName = ""
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Azure Function App Verification" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Azure login
try {
    $context = Get-AzContext -ErrorAction Stop
    Write-Host "✓ Logged in as: $($context.Account.Id)" -ForegroundColor Green
} catch {
    Write-Host "✗ Not logged in. Run: Connect-AzAccount" -ForegroundColor Red
    exit 1
}

# Get Function App name if not provided
if ([string]::IsNullOrWhiteSpace($FunctionAppName)) {
    Write-Host "Finding Function Apps in resource group '$ResourceGroupName'..." -ForegroundColor Yellow
    $functionApps = Get-AzFunctionApp -ResourceGroupName $ResourceGroupName
    if ($functionApps.Count -eq 0) {
        Write-Host "✗ No Function Apps found in resource group '$ResourceGroupName'" -ForegroundColor Red
        exit 1
    } elseif ($functionApps.Count -eq 1) {
        $FunctionAppName = $functionApps[0].Name
        Write-Host "✓ Found Function App: $FunctionAppName" -ForegroundColor Green
    } else {
        Write-Host "Multiple Function Apps found:" -ForegroundColor Yellow
        $functionApps | ForEach-Object { Write-Host "  - $($_.Name)" -ForegroundColor White }
        Write-Host "`nPlease specify Function App name:" -ForegroundColor Yellow
        Write-Host "  .\verify_function.ps1 -FunctionAppName 'your-function-app-name'" -ForegroundColor Cyan
        exit 1
    }
}

# Get Function App
$functionApp = Get-AzFunctionApp -ResourceGroupName $ResourceGroupName -Name $FunctionAppName -ErrorAction SilentlyContinue
if (-not $functionApp) {
    Write-Host "✗ Function App '$FunctionAppName' not found" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== Function App Status ===" -ForegroundColor Cyan
Write-Host "Name: $($functionApp.Name)" -ForegroundColor White
Write-Host "State: $($functionApp.State)" -ForegroundColor $(if ($functionApp.State -eq "Running") { "Green" } else { "Yellow" })
Write-Host "URL: https://$($functionApp.DefaultHostName)" -ForegroundColor Cyan

# Check Functions
Write-Host "`n=== Functions ===" -ForegroundColor Cyan
try {
    $functions = Get-AzFunctionAppFunction -ResourceGroupName $ResourceGroupName -Name $FunctionAppName -ErrorAction SilentlyContinue
    if ($functions) {
        Write-Host "✓ Functions found:" -ForegroundColor Green
        $functions | ForEach-Object {
            Write-Host "  - $($_.Name)" -ForegroundColor White
        }
    } else {
        Write-Host "⚠ No functions found. Check Deployment Center for deployment status." -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠ Could not retrieve functions: $_" -ForegroundColor Yellow
}

# Check Application Settings
Write-Host "`n=== Application Settings ===" -ForegroundColor Cyan
try {
    $settings = Get-AzFunctionAppSetting -ResourceGroupName $ResourceGroupName -Name $FunctionAppName
    $requiredSettings = @(
        "MongoDBConnectionString",
        "COSMOS_DATABASE",
        "COSMOS_COLLECTION",
        "ALARM_FIELD",
        "PHONE_NUMBER_TO_CALL",
        "COMMUNICATION_SERVICE_CONNECTION_STRING",
        "COMMUNICATION_SERVICE_PHONE_NUMBER"
    )
    
    $missingSettings = @()
    foreach ($setting in $requiredSettings) {
        if ($settings.ContainsKey($setting) -and -not [string]::IsNullOrWhiteSpace($settings[$setting])) {
            Write-Host "✓ $setting : configured" -ForegroundColor Green
        } else {
            Write-Host "✗ $setting : missing or empty" -ForegroundColor Red
            $missingSettings += $setting
        }
    }
    
    if ($missingSettings.Count -gt 0) {
        Write-Host "`n⚠ Missing required settings. Please add them in Azure Portal:" -ForegroundColor Yellow
        Write-Host "  Portal -> Function App -> Configuration -> Application settings" -ForegroundColor Cyan
    }
} catch {
    Write-Host "⚠ Could not retrieve settings: $_" -ForegroundColor Yellow
}

# Check recent invocations
Write-Host "`n=== Recent Activity ===" -ForegroundColor Cyan
Write-Host "To check function execution logs:" -ForegroundColor Yellow
Write-Host "1. Go to Azure Portal: https://portal.azure.com" -ForegroundColor White
Write-Host "2. Navigate to: $FunctionAppName -> Functions -> monitor_timer_trigger" -ForegroundColor White
Write-Host "3. Click 'Monitor' tab to see execution history" -ForegroundColor White
Write-Host "4. Click 'Logs' tab to see real-time logs" -ForegroundColor White

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Verification Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`nNext Steps:" -ForegroundColor Yellow
Write-Host "1. Check Function execution in Azure Portal" -ForegroundColor White
Write-Host "2. Verify timer trigger is running (should run every minute)" -ForegroundColor White
Write-Host "3. Check Logs for any errors" -ForegroundColor White
Write-Host "4. Test by checking CosmosDB for alarm conditions" -ForegroundColor White

