# PowerShell script to fix Hugging Face token issues
# This script helps diagnose and fix token issues in Docker environment

function Write-ColorOutput($ForegroundColor) {
    # Save the current color
    $previousForegroundColor = $host.UI.RawUI.ForegroundColor
    
    # Set the new color
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    
    # Write the output
    if ($args) {
        Write-Output $args
    }
    else {
        # Write whatever is piped to this function
        $input | Write-Output
    }
    
    # Restore the original color
    $host.UI.RawUI.ForegroundColor = $previousForegroundColor
}

function Write-Success($message) {
    Write-ColorOutput Green "✓ $message"
}

function Write-Warning($message) {
    Write-ColorOutput Yellow "⚠ $message"
}

function Write-Error($message) {
    Write-ColorOutput Red "✗ $message"
}

function Write-Info($message) {
    Write-ColorOutput Cyan "ℹ $message"
}

function Write-Header($message) {
    Write-Output ""
    Write-ColorOutput Blue "================================================================================"
    Write-ColorOutput Blue " $message"
    Write-ColorOutput Blue "================================================================================"
    Write-Output ""
}

function Mask-Token($token) {
    if (-not $token -or $token.Length -lt 8) {
        return "***"
    }
    return "$($token.Substring(0, 4))...$($token.Substring($token.Length - 4))"
}

function Check-EnvFile {
    Write-Header "Checking .env file"
    
    $envPath = ".env"
    if (-not (Test-Path $envPath)) {
        Write-Error ".env file not found!"
        return $null
    }
    
    $envContent = Get-Content $envPath -Raw
    
    # Extract token using regex
    $tokenMatch = [regex]::Match($envContent, 'HUGGINGFACE_TOKEN=([^\r\n]+)')
    if (-not $tokenMatch.Success) {
        Write-Error "HUGGINGFACE_TOKEN not found in .env file!"
        return $null
    }
    
    $token = $tokenMatch.Groups[1].Value.Trim()
    $maskedToken = Mask-Token $token
    Write-Success "Found HUGGINGFACE_TOKEN in .env file: $maskedToken"
    
    # Check for Redis URL
    if ($envContent -match "CELERY_BROKER_URL=redis://localhost") {
        Write-Warning "Found CELERY_BROKER_URL using 'localhost' instead of 'redis'!"
        Write-Info "Consider changing to: CELERY_BROKER_URL=redis://redis:6379/0"
    }
    
    return $token
}

function Check-DockerEnvironment {
    Write-Header "Checking Docker environment"
    
    try {
        # Check if Docker is running
        docker ps | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Docker is not running!"
            return $null
        }
        Write-Success "Docker is running"
        
        # Check if celery_worker container is running
        $containerRunning = docker-compose ps | Select-String -Pattern "celery_worker.*Up" -Quiet
        if (-not $containerRunning) {
            Write-Error "celery_worker container is not running!"
            return $null
        }
        Write-Success "celery_worker container is running"
        
        # Check environment variables in the celery_worker container
        Write-Info "Checking environment variables in celery_worker container..."
        $envVars = docker-compose exec -T celery_worker env
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to get environment variables from container!"
            return $null
        }
        
        $hfToken = $null
        foreach ($var in $envVars) {
            if ($var -match "^HUGGINGFACE_TOKEN=(.+)$") {
                $hfToken = $matches[1]
                $maskedToken = Mask-Token $hfToken
                Write-Success "Found HUGGINGFACE_TOKEN in container: $maskedToken"
                break
            }
        }
        
        if (-not $hfToken) {
            Write-Error "HUGGINGFACE_TOKEN not found in container environment!"
            return $null
        }
        
        return $hfToken
    }
    catch {
        Write-Error "Error checking Docker environment: $_"
        return $null
    }
}

function Test-HuggingFaceToken($token) {
    Write-Header "Testing token permissions"
    
    if (-not $token) {
        Write-Error "No token provided!"
        return $false
    }
    
    # Test endpoint
    $url = "https://api-inference.huggingface.co/models/facebook/musicgen-stereo-small"
    $headers = @{
        "Authorization" = "Bearer $token"
    }
    $body = @{
        "inputs" = "Test connection"
        "options" = @{
            "wait_for_model" = $false
        }
    } | ConvertTo-Json
    
    try {
        Write-Info "Sending test request to Hugging Face API..."
        $response = Invoke-RestMethod -Uri $url -Method Post -Headers $headers -Body $body -ContentType "application/json" -TimeoutSec 10 -ErrorVariable restError -ErrorAction SilentlyContinue
        
        Write-Success "Token has proper permissions!"
        return $true
    }
    catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        $errorDetails = $restError.Message
        
        Write-Info "Response status code: $statusCode"
        Write-Info "Response body: $errorDetails"
        
        if ($statusCode -eq 401) {
            Write-Error "Token is invalid or expired!"
            Write-Info "Please create a new token at: https://huggingface.co/settings/tokens"
        }
        elseif ($statusCode -eq 403) {
            Write-Error "Token does not have sufficient permissions!"
            Write-Info "Please create a new token with WRITE permissions at:"
            Write-Info "https://huggingface.co/settings/tokens"
        }
        else {
            Write-Warning "Unexpected response: $errorDetails"
        }
        
        return $false
    }
}

function Update-EnvFile($newToken) {
    Write-Header "Updating .env file"
    
    $envPath = ".env"
    if (-not (Test-Path $envPath)) {
        Write-Error ".env file not found!"
        return $false
    }
    
    # Create backup
    $backupPath = "$envPath.backup"
    Copy-Item -Path $envPath -Destination $backupPath -Force
    Write-Info "Created backup of original .env file at $backupPath"
    
    # Read content
    $envContent = Get-Content $envPath -Raw
    
    # Update token using regex
    $updatedContent = [regex]::Replace($envContent, 'HUGGINGFACE_TOKEN=([^\r\n]+)', "HUGGINGFACE_TOKEN=$newToken")
    
    # Write updated content
    Set-Content -Path $envPath -Value $updatedContent
    
    Write-Success "Updated HUGGINGFACE_TOKEN in .env file"
    return $true
}

function Restart-DockerContainers {
    Write-Header "Restarting Docker containers"
    
    try {
        Write-Info "Stopping containers..."
        docker-compose down
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to stop containers!"
            return $false
        }
        
        Write-Info "Starting containers..."
        docker-compose up -d
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to start containers!"
            return $false
        }
        
        Write-Success "Containers restarted successfully"
        return $true
    }
    catch {
        Write-Error "Failed to restart containers: $_"
        return $false
    }
}

# Main script
Write-Header "Hugging Face Token Fixer"

# Step 1: Check .env file
$tokenFromEnv = Check-EnvFile

# Step 2: Check Docker environment
$tokenFromDocker = Check-DockerEnvironment

# Step 3: Compare tokens
if ($tokenFromEnv -and $tokenFromDocker -and ($tokenFromEnv -ne $tokenFromDocker)) {
    Write-Warning "Token in .env file doesn't match token in Docker container!"
    Write-Info "This suggests the containers need to be restarted to pick up the new token"
}

# Step 4: Test token from Docker (this is what matters for the API calls)
$tokenValid = $false
if ($tokenFromDocker) {
    $tokenValid = Test-HuggingFaceToken $tokenFromDocker
}

# Step 5: Ask for new token if needed
if (-not $tokenValid) {
    Write-Header "Token Update Required"
    Write-Info "Your current token is invalid or has insufficient permissions."
    Write-Info "Please create a new token with WRITE permissions at:"
    Write-Info "https://huggingface.co/settings/tokens"
    
    $newToken = Read-Host -Prompt "Enter your new Hugging Face token"
    if ($newToken.Trim()) {
        # Test the new token
        if (Test-HuggingFaceToken $newToken.Trim()) {
            # Update .env file
            if (Update-EnvFile $newToken.Trim()) {
                # Restart containers
                $restart = Read-Host -Prompt "Do you want to restart Docker containers now? (y/n)"
                if ($restart.ToLower() -eq 'y') {
                    Restart-DockerContainers
                }
            }
        }
    }
}

Write-Header "Troubleshooting Summary"
if (-not $tokenValid) {
    Write-Warning "Your Hugging Face token appears to have permission issues."
    Write-Info "Please follow these steps:"
    Write-Info "1. Go to https://huggingface.co/settings/tokens"
    Write-Info "2. Create a new token with WRITE permissions"
    Write-Info "3. Update your .env file with the new token"
    Write-Info "4. Restart your Docker containers with: docker-compose down && docker-compose up -d"
    Write-Info "5. Make sure you've accepted the model terms at:"
    Write-Info "   https://huggingface.co/facebook/musicgen-stereo-small"
}
else {
    Write-Success "Your Hugging Face token appears to be valid!"
    Write-Info "If you're still experiencing issues, please check:"
    Write-Info "1. Docker container logs: docker-compose logs celery_worker"
    Write-Info "2. Network connectivity to Hugging Face API"
    Write-Info "3. Model access at https://huggingface.co/facebook/musicgen-stereo-small"
}
