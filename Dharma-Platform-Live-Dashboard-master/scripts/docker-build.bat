@echo off
REM Build all Docker images for Project Dharma services

echo Building Project Dharma Docker images...

REM Build services
set services=data-collection-service ai-analysis-service api-gateway-service dashboard-service

for %%s in (%services%) do (
    echo Building %%s...
    docker build -t dharma/%%s:latest ./services/%%s
    if errorlevel 1 (
        echo Failed to build %%s
        exit /b 1
    )
    echo ✓ Built %%s
)

echo All Docker images built successfully!

REM Optional: Tag images for registry
if "%1"=="--tag-registry" (
    set REGISTRY=%2
    if "%REGISTRY%"=="" set REGISTRY=your-registry.com
    
    for %%s in (%services%) do (
        docker tag dharma/%%s:latest %REGISTRY%/dharma/%%s:latest
        echo ✓ Tagged %%s for registry %REGISTRY%
    )
)