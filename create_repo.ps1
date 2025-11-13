# Script to create GitHub repository AlarmBaaS
param(
    [string]$Token = $null
)

# Try to get token from credentials.json
if (-not $Token) {
    $credsPath = Join-Path $PSScriptRoot "credentials.json"
    if (Test-Path $credsPath) {
        try {
            $creds = Get-Content $credsPath | ConvertFrom-Json
            if ($creds.github_token) {
                $Token = $creds.github_token
            } elseif ($creds.token) {
                $Token = $creds.token
            } else {
                # Fallback: try reading as plain text
                $Token = (Get-Content $credsPath).Trim()
            }
            Write-Host "Token loaded from credentials.json" -ForegroundColor Green
        } catch {
            # Fallback: try reading as plain text
            $Token = (Get-Content $credsPath).Trim()
            Write-Host "Token loaded from credentials.json (plain text)" -ForegroundColor Green
        }
    }
}

# Try environment variable
if (-not $Token) {
    $Token = $env:GITHUB_TOKEN
}

if (-not $Token) {
    Write-Host "GitHub Personal Access Token not found." -ForegroundColor Yellow
    Write-Host "Please create a token with 'repo' scope at: https://github.com/settings/tokens" -ForegroundColor Cyan
    exit 1
}

$headers = @{
    "Authorization" = "token $Token"
    "Accept" = "application/vnd.github.v3+json"
}

$body = @{
    name = "AlarmBaaS"
    description = "Azure Function App to monitor CosmosDB for alarm conditions and make phone calls"
    private = $false
    auto_init = $false
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "https://api.github.com/user/repos" -Method Post -Headers $headers -Body $body -ContentType "application/json"
    Write-Host "Repository created successfully!" -ForegroundColor Green
    Write-Host "Repository URL: $($response.html_url)" -ForegroundColor Cyan
    Write-Host "Clone URL: $($response.clone_url)" -ForegroundColor Cyan
    
    # Now push the code
    Write-Host "`nPushing code to repository..." -ForegroundColor Yellow
    git push -u origin main
    
    Write-Host "`nDone! Repository is ready at: $($response.html_url)" -ForegroundColor Green
} catch {
    Write-Host "Error creating repository: $_" -ForegroundColor Red
    Write-Host "Response: $($_.Exception.Response)" -ForegroundColor Red
    exit 1
}

