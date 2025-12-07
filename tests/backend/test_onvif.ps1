# ONVIF Integration Test Script
# This script tests all ONVIF endpoints

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "ONVIF INTEGRATION TEST" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check if backend is running
Write-Host "[1/6] Checking backend server..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/docs" -Method HEAD -TimeoutSec 2
    Write-Host "[OK] Backend server is running" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Backend server is not running!" -ForegroundColor Red
    Write-Host "Please start with: uvicorn main:app --reload" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Test 1: Discovery
Write-Host "[2/6] Testing camera discovery..." -ForegroundColor Yellow
Write-Host "      Scanning network for ONVIF cameras (timeout: 10s)..." -ForegroundColor Gray

$discoveryResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/discover?timeout=10" -Method GET

$cameraCount = $discoveryResponse.foundCameras
Write-Host "      Found $cameraCount cameras" -ForegroundColor Gray

if ($cameraCount -eq 0) {
    Write-Host "[WARNING] No cameras found" -ForegroundColor Yellow
    Write-Host "          - Make sure Docker is running" -ForegroundColor Gray
    Write-Host "          - Run: docker run -d --name onvif-sim -p 8080:8080 oznu/onvif-camera-simulator" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Do you want to continue testing with manual camera input? (Y/N)" -ForegroundColor Yellow
    $continue = Read-Host

    if ($continue -ne "Y" -and $continue -ne "y") {
        Write-Host "Exiting..." -ForegroundColor Red
        exit 0
    }

    # Manual camera input
    Write-Host ""
    Write-Host "Enter camera details for testing:" -ForegroundColor Cyan
    $cameraIp = Read-Host "Camera IP (e.g., 127.0.0.1)"
    $cameraPort = Read-Host "Camera Port (default: 8080)"
    $cameraUser = Read-Host "Camera Username (default: admin)"
    $cameraPass = Read-Host "Camera Password (default: admin)" -AsSecureString
    $cameraPassPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($cameraPass)
    )

    if ([string]::IsNullOrEmpty($cameraPort)) { $cameraPort = "8080" }
    if ([string]::IsNullOrEmpty($cameraUser)) { $cameraUser = "admin" }
    if ([string]::IsNullOrEmpty($cameraPassPlain)) { $cameraPassPlain = "admin" }

} else {
    Write-Host "[OK] Found cameras on network" -ForegroundColor Green

    # Use first discovered camera
    $camera = $discoveryResponse.cameras[0]
    $cameraIp = $camera.ip
    $cameraPort = $camera.port
    $cameraUser = "admin"  # Default
    $cameraPassPlain = "admin"  # Default

    Write-Host "      Using: $($camera.manufacturer) $($camera.model) at ${cameraIp}:${cameraPort}" -ForegroundColor Gray
}

Write-Host ""

# Test 2: Capabilities
Write-Host "[3/6] Testing capabilities query..." -ForegroundColor Yellow
Write-Host "      Querying camera capabilities at ${cameraIp}:${cameraPort}..." -ForegroundColor Gray

try {
    $capUrl = "http://localhost:8000/api/cameras/test-cam/capabilities?ip=$cameraIp&port=$cameraPort&username=$cameraUser&password=$cameraPassPlain"
    $capResponse = Invoke-RestMethod -Uri $capUrl -Method GET -TimeoutSec 30

    Write-Host "[OK] Capabilities retrieved" -ForegroundColor Green
    Write-Host "      Manufacturer: $($capResponse.capabilities.device.manufacturer)" -ForegroundColor Gray
    Write-Host "      Model: $($capResponse.capabilities.device.model)" -ForegroundColor Gray
    Write-Host "      Firmware: $($capResponse.capabilities.device.firmware)" -ForegroundColor Gray
    Write-Host "      Max Resolution: $($capResponse.capabilities.max_resolution)" -ForegroundColor Gray
    Write-Host "      Codecs: $($capResponse.capabilities.supported_codecs -join ', ')" -ForegroundColor Gray
} catch {
    Write-Host "[ERROR] Failed to query capabilities" -ForegroundColor Red
    Write-Host "        $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Test 3: Current Settings
Write-Host "[4/6] Testing current settings query..." -ForegroundColor Yellow
Write-Host "      Querying current camera settings..." -ForegroundColor Gray

try {
    $settingsUrl = "http://localhost:8000/api/cameras/test-cam/current-settings?ip=$cameraIp&port=$cameraPort&username=$cameraUser&password=$cameraPassPlain"
    $settingsResponse = Invoke-RestMethod -Uri $settingsUrl -Method GET -TimeoutSec 30

    Write-Host "[OK] Current settings retrieved" -ForegroundColor Green
    Write-Host "      Resolution: $($settingsResponse.currentSettings.stream.resolution)" -ForegroundColor Gray
    Write-Host "      Codec: $($settingsResponse.currentSettings.stream.codec)" -ForegroundColor Gray
    Write-Host "      FPS: $($settingsResponse.currentSettings.stream.fps)" -ForegroundColor Gray
    Write-Host "      Bitrate: $($settingsResponse.currentSettings.stream.bitrateMbps) Mbps" -ForegroundColor Gray
} catch {
    Write-Host "[ERROR] Failed to query settings" -ForegroundColor Red
    Write-Host "        $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Test 4: Apply Settings
Write-Host "[5/6] Testing settings apply..." -ForegroundColor Yellow
Write-Host "      WARNING: This will modify camera settings!" -ForegroundColor Red
Write-Host "      Do you want to test applying settings? (Y/N)" -ForegroundColor Yellow
$applyTest = Read-Host

if ($applyTest -eq "Y" -or $applyTest -eq "y") {
    Write-Host "      Applying test settings (H.265, 1280x720, 15 FPS, 2 Mbps)..." -ForegroundColor Gray

    $applyBody = @{
        camera = @{
            id = "test-cam"
            ip = $cameraIp
        }
        settings = @{
            stream = @{
                resolution = "1280x720"
                codec = "H.265"
                fps = 15
                bitrateMbps = 2.0
                keyframeInterval = 30
            }
            exposure = @{
                shutter = "1/125"
            }
            lowLight = @{
                irMode = "Auto"
            }
        }
        applyVia = "onvif"
        credentials = @{
            username = $cameraUser
            password = $cameraPassPlain
            port = [int]$cameraPort
        }
        verifyAfterApply = $true
    } | ConvertTo-Json -Depth 10

    try {
        $applyResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/apply" -Method POST -Body $applyBody -ContentType "application/json" -TimeoutSec 60

        if ($applyResponse.status -eq "completed") {
            Write-Host "[OK] Settings applied successfully!" -ForegroundColor Green
            Write-Host "      Job ID: $($applyResponse.job_id)" -ForegroundColor Gray
            Write-Host "      Progress: $($applyResponse.progress)%" -ForegroundColor Gray

            if ($applyResponse.result.verification_status -eq "success") {
                Write-Host "      Verification: PASSED" -ForegroundColor Green
            } else {
                Write-Host "      Verification: FAILED or PARTIAL" -ForegroundColor Yellow
            }
        } else {
            Write-Host "[WARNING] Apply job status: $($applyResponse.status)" -ForegroundColor Yellow
            if ($applyResponse.error) {
                Write-Host "              Error: $($applyResponse.error.message)" -ForegroundColor Red
            }
        }
    } catch {
        Write-Host "[ERROR] Failed to apply settings" -ForegroundColor Red
        Write-Host "        $($_.Exception.Message)" -ForegroundColor Red
    }
} else {
    Write-Host "[SKIPPED] Settings apply test skipped by user" -ForegroundColor Yellow
}

Write-Host ""

# Test 5: Integration with Claude Vision
Write-Host "[6/6] Testing full optimization + apply workflow..." -ForegroundColor Yellow
Write-Host "      Do you want to test Claude Vision optimization + ONVIF apply? (Y/N)" -ForegroundColor Yellow
$fullTest = Read-Host

if ($fullTest -eq "Y" -or $fullTest -eq "y") {
    Write-Host "      Step 1: Running Claude Vision optimization..." -ForegroundColor Gray

    # Build optimization request with current settings from camera
    $optimizeBody = @{
        camera = @{
            id = "test-cam"
            ip = $cameraIp
            vendor = "Unknown"
            model = "ONVIF Camera"
            sceneType = "entrance"
            purpose = "facial"
        }
        capabilities = @{
            maxResolution = "1920x1080"
            supportedCodecs = @("H.264", "H.265")
            maxFps = 30
            wdrLevels = @("Off", "Low", "Medium", "High")
            irModes = @("Off", "Auto", "On")
        }
        currentSettings = @{
            stream = @{
                resolution = "1920x1080"
                codec = "H.264"
                fps = 30
                bitrateMbps = 6.0
            }
            exposure = @{
                shutter = "1/30"
                wdr = "Off"
            }
            lowLight = @{
                irMode = "Auto"
            }
        }
        context = @{
            bandwidthLimitMbps = 4.0
            targetRetentionDays = 30
            notes = "ONVIF simulator test"
        }
    } | ConvertTo-Json -Depth 10

    try {
        $optimizeResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/optimize" -Method POST -Body $optimizeBody -ContentType "application/json" -TimeoutSec 60

        Write-Host "      [OK] Claude Vision optimization complete" -ForegroundColor Green
        Write-Host "           AI Provider: $($optimizeResponse.aiProvider)" -ForegroundColor Gray
        Write-Host "           Confidence: $([math]::Round($optimizeResponse.confidence * 100, 1))%" -ForegroundColor Gray
        Write-Host "           Processing Time: $([math]::Round($optimizeResponse.processingTime, 2))s" -ForegroundColor Gray

        Write-Host ""
        Write-Host "      Step 2: Apply optimized settings to camera? (Y/N)" -ForegroundColor Yellow
        $applyOptimized = Read-Host

        if ($applyOptimized -eq "Y" -or $applyOptimized -eq "y") {
            $applyOptimizedBody = @{
                camera = @{
                    id = "test-cam"
                    ip = $cameraIp
                }
                settings = $optimizeResponse.recommendedSettings
                applyVia = "onvif"
                credentials = @{
                    username = $cameraUser
                    password = $cameraPassPlain
                    port = [int]$cameraPort
                }
                verifyAfterApply = $true
            } | ConvertTo-Json -Depth 10

            $finalApply = Invoke-RestMethod -Uri "http://localhost:8000/api/apply" -Method POST -Body $applyOptimizedBody -ContentType "application/json" -TimeoutSec 60

            if ($finalApply.status -eq "completed") {
                Write-Host "      [OK] Optimized settings applied!" -ForegroundColor Green
                Write-Host "           🎉 End-to-end workflow successful!" -ForegroundColor Cyan
            } else {
                Write-Host "      [WARNING] Apply failed: $($finalApply.status)" -ForegroundColor Yellow
            }
        }
    } catch {
        Write-Host "      [ERROR] Optimization failed" -ForegroundColor Red
        Write-Host "              $($_.Exception.Message)" -ForegroundColor Red
    }
} else {
    Write-Host "[SKIPPED] Full workflow test skipped by user" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "TEST COMPLETE" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Review test results above" -ForegroundColor Gray
Write-Host "  2. Check Swagger UI for more testing: http://localhost:8000/docs" -ForegroundColor Gray
Write-Host "  3. View ONVIF testing guide: backend/ONVIF_TESTING.md" -ForegroundColor Gray
Write-Host ""
