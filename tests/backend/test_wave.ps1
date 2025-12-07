# Hanwha WAVE VMS Integration Test Script
# Tests all WAVE-related API endpoints

param(
    [string]$BackendUrl = "http://localhost:8000",
    [string]$WaveServer = "192.168.1.100",
    [int]$WavePort = 7001,
    [string]$WaveUsername = "admin",
    [string]$WavePassword = "",
    [bool]$UseHttps = $true
)

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "  Hanwha WAVE VMS Integration Tests" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Backend URL:    $BackendUrl"
Write-Host "  WAVE Server:    $WaveServer"
Write-Host "  WAVE Port:      $WavePort"
Write-Host "  WAVE Username:  $WaveUsername"
Write-Host "  Use HTTPS:      $UseHttps"
Write-Host ""

$testResults = @()

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Method,
        [string]$Url,
        [hashtable]$Body = $null,
        [bool]$ExpectSuccess = $true
    )

    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor Gray
    Write-Host "TEST: $Name" -ForegroundColor Cyan
    Write-Host ("=" * 70) -ForegroundColor Gray
    Write-Host ""
    Write-Host "Request:" -ForegroundColor Yellow
    Write-Host "  Method: $Method"
    Write-Host "  URL:    $Url"

    if ($Body) {
        Write-Host "  Body:   $(ConvertTo-Json $Body -Compress)"
    }

    Write-Host ""

    $result = @{
        Name = $Name
        Success = $false
        StatusCode = 0
        Duration = 0
        Error = ""
        Response = $null
    }

    try {
        $startTime = Get-Date

        $params = @{
            Uri = $Url
            Method = $Method
            Headers = @{
                "Content-Type" = "application/json"
            }
            TimeoutSec = 30
        }

        if ($Body) {
            $params.Body = (ConvertTo-Json $Body -Depth 10)
        }

        $response = Invoke-RestMethod @params

        $endTime = Get-Date
        $duration = ($endTime - $startTime).TotalSeconds

        $result.Success = $true
        $result.StatusCode = 200
        $result.Duration = $duration
        $result.Response = $response

        Write-Host "Response:" -ForegroundColor Green
        Write-Host (ConvertTo-Json $response -Depth 5)
        Write-Host ""
        Write-Host "✅ SUCCESS (took $($duration.ToString('F2'))s)" -ForegroundColor Green

    } catch {
        $endTime = Get-Date
        $duration = ($endTime - $startTime).TotalSeconds

        $result.Success = $false
        $result.Duration = $duration
        $result.Error = $_.Exception.Message

        if ($_.Exception.Response) {
            $result.StatusCode = [int]$_.Exception.Response.StatusCode
        }

        Write-Host "Error:" -ForegroundColor Red
        Write-Host "  $($_.Exception.Message)"
        Write-Host ""

        if ($ExpectSuccess) {
            Write-Host "❌ FAILED" -ForegroundColor Red
        } else {
            Write-Host "✅ EXPECTED FAILURE" -ForegroundColor Yellow
        }
    }

    $script:testResults += $result
    return $result
}

Write-Host ""
Write-Host "Starting tests..." -ForegroundColor Yellow
Write-Host ""

# ==============================================================================
# Test 1: WAVE Camera Discovery
# ==============================================================================

$url = "$BackendUrl/api/wave/discover?server_ip=$WaveServer&port=$WavePort&username=$WaveUsername&password=$WavePassword&use_https=$($UseHttps.ToString().ToLower())"

$test1 = Test-Endpoint -Name "WAVE Camera Discovery" `
                        -Method "GET" `
                        -Url $url `
                        -ExpectSuccess $true

$cameras = @()
if ($test1.Success -and $test1.Response.cameras) {
    $cameras = $test1.Response.cameras
    Write-Host ""
    Write-Host "📸 Found $($cameras.Count) cameras:" -ForegroundColor Cyan

    foreach ($cam in $cameras) {
        Write-Host "  - $($cam.name) ($($cam.vendor) $($cam.model)) at $($cam.ip)" -ForegroundColor Gray
        Write-Host "    ID: $($cam.id) | Status: $($cam.status) | Recording: $($cam.recording)" -ForegroundColor DarkGray
    }
}

# ==============================================================================
# Test 2: Get Camera Capabilities (if cameras found)
# ==============================================================================

if ($cameras.Count -gt 0) {
    $cameraId = $cameras[0].id

    $url = "$BackendUrl/api/wave/cameras/$cameraId/capabilities?server_ip=$WaveServer&port=$WavePort&username=$WaveUsername&password=$WavePassword"

    $test2 = Test-Endpoint -Name "Get WAVE Camera Capabilities" `
                            -Method "GET" `
                            -Url $url `
                            -ExpectSuccess $true

    if ($test2.Success) {
        $caps = $test2.Response.capabilities
        Write-Host ""
        Write-Host "📋 Camera Capabilities:" -ForegroundColor Cyan
        Write-Host "  Device: $($caps.device.manufacturer) $($caps.device.model)" -ForegroundColor Gray
        Write-Host "  Max Resolution: $($caps.max_resolution)" -ForegroundColor Gray
        Write-Host "  Max FPS: $($caps.max_fps)" -ForegroundColor Gray
    }
}

# ==============================================================================
# Test 3: Get Current Settings (if cameras found)
# ==============================================================================

if ($cameras.Count -gt 0) {
    $cameraId = $cameras[0].id

    $url = "$BackendUrl/api/wave/cameras/$cameraId/current-settings?server_ip=$WaveServer&port=$WavePort&username=$WaveUsername&password=$WavePassword"

    $test3 = Test-Endpoint -Name "Get WAVE Camera Current Settings" `
                            -Method "GET" `
                            -Url $url `
                            -ExpectSuccess $true

    if ($test3.Success) {
        $settings = $test3.Response.currentSettings
        Write-Host ""
        Write-Host "⚙️ Current Settings:" -ForegroundColor Cyan
        Write-Host "  Resolution: $($settings.stream.resolution)" -ForegroundColor Gray
        Write-Host "  Codec: $($settings.stream.codec)" -ForegroundColor Gray
        Write-Host "  FPS: $($settings.stream.fps)" -ForegroundColor Gray
        Write-Host "  Bitrate: $($settings.stream.bitrateMbps) Mbps" -ForegroundColor Gray
    }
}

# ==============================================================================
# Test 4: Apply Settings via WAVE (if cameras found)
# ==============================================================================

if ($cameras.Count -gt 0) {
    $cameraId = $cameras[0].id
    $waveCamera = $cameras[0]

    # Create apply request
    $applyRequest = @{
        camera = @{
            id = "test-wave-camera-01"
            ip = $waveCamera.ip
            vendor = $waveCamera.vendor
            model = $waveCamera.model
            vmsSystem = "hanwha-wave"
            vmsCameraId = $cameraId
        }
        settings = @{
            stream = @{
                resolution = "1920x1080"
                codec = "H.265"
                fps = 20
                bitrateMbps = 4.0
                keyframeInterval = 60
                cbr = $true
            }
            exposure = @{
                shutter = "1/250"
                wdr = "High"
            }
            lowLight = @{
                irMode = "auto"
                noiseReduction = "medium"
            }
        }
        applyVia = "vms"
        credentials = @{
            server_ip = $WaveServer
            port = $WavePort
            username = $WaveUsername
            password = $WavePassword
        }
        verifyAfterApply = $true
    }

    $url = "$BackendUrl/api/apply"

    Write-Host ""
    Write-Host "NOTE: This test will attempt to modify camera settings!" -ForegroundColor Yellow
    Write-Host "Press Ctrl+C within 5 seconds to cancel..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5

    $test4 = Test-Endpoint -Name "Apply Settings via WAVE VMS" `
                            -Method "POST" `
                            -Url $url `
                            -Body $applyRequest `
                            -ExpectSuccess $true

    if ($test4.Success) {
        $jobId = $test4.Response.job_id

        Write-Host ""
        Write-Host "🔄 Apply job created: $jobId" -ForegroundColor Cyan

        # Poll job status
        Write-Host "Checking job status..." -ForegroundColor Yellow

        $maxAttempts = 10
        $attempt = 0
        $jobCompleted = $false

        while ($attempt -lt $maxAttempts -and -not $jobCompleted) {
            Start-Sleep -Seconds 2
            $attempt++

            try {
                $statusUrl = "$BackendUrl/api/apply/status/$jobId"
                $status = Invoke-RestMethod -Uri $statusUrl -Method GET

                Write-Host "  Attempt $attempt : $($status.status) - Progress: $($status.progress)%" -ForegroundColor Gray

                if ($status.status -eq "completed" -or $status.status -eq "failed") {
                    $jobCompleted = $true

                    if ($status.status -eq "completed") {
                        Write-Host ""
                        Write-Host "✅ Job completed successfully!" -ForegroundColor Green
                        Write-Host "Steps completed:" -ForegroundColor Gray

                        foreach ($step in $status.steps) {
                            $emoji = if ($step.status -eq "completed") { "✓" } elseif ($step.status -eq "failed") { "✗" } else { "○" }
                            Write-Host "  $emoji $($step.name) - $($step.status)" -ForegroundColor Gray
                        }
                    } else {
                        Write-Host ""
                        Write-Host "❌ Job failed: $($status.error.message)" -ForegroundColor Red
                    }
                }

            } catch {
                Write-Host "  Failed to get status: $($_.Exception.Message)" -ForegroundColor Red
                break
            }
        }

        if (-not $jobCompleted) {
            Write-Host ""
            Write-Host "⚠️ Job did not complete within timeout" -ForegroundColor Yellow
        }
    }
}

# ==============================================================================
# Test Summary
# ==============================================================================

Write-Host ""
Write-Host ""
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "  Test Summary" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host ""

$totalTests = $testResults.Count
$passedTests = ($testResults | Where-Object { $_.Success }).Count
$failedTests = $totalTests - $passedTests
$totalDuration = ($testResults | Measure-Object -Property Duration -Sum).Sum

Write-Host "Total Tests:  $totalTests" -ForegroundColor White
Write-Host "Passed:       $passedTests" -ForegroundColor Green
Write-Host "Failed:       $failedTests" -ForegroundColor $(if ($failedTests -gt 0) { "Red" } else { "Gray" })
Write-Host "Duration:     $($totalDuration.ToString('F2'))s" -ForegroundColor Gray
Write-Host ""

foreach ($result in $testResults) {
    $status = if ($result.Success) { "✅ PASS" } else { "❌ FAIL" }
    $color = if ($result.Success) { "Green" } else { "Red" }

    Write-Host "$status : $($result.Name) ($($result.Duration.ToString('F2'))s)" -ForegroundColor $color

    if (-not $result.Success -and $result.Error) {
        Write-Host "       Error: $($result.Error)" -ForegroundColor DarkRed
    }
}

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host ""

# Exit with error code if any tests failed
if ($failedTests -gt 0) {
    exit 1
} else {
    exit 0
}
