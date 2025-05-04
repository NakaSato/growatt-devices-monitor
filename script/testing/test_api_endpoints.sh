#!/bin/bash
#
# API Endpoint Test Script for Growatt Devices Monitor
# This script tests all API endpoints in the application and validates responses.
#
# Usage: ./test_api_endpoints.sh [base_url] [username] [password]
# Example: ./test_api_endpoints.sh http://localhost:5000 admin password123
#

# Set default values
BASE_URL=${1:-"http://localhost:8000"}
USERNAME=${2:-"test_user"}
PASSWORD=${3:-"test_password"}
LOG_FILE="api_test_$(date +%Y%m%d_%H%M%S).log"
AUTH_TOKEN=""

# Color definitions for better readability
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Initialize counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0

# ----------------------------------------
# Utility Functions
# ----------------------------------------

log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

log_request() {
    log "${BLUE}REQUEST: $1 $2${NC}"
}

log_response() {
    log "${BLUE}RESPONSE (${3}):${NC} ${4:0:150}..."
}

log_passed() {
    log "${GREEN}✓ PASSED: $1${NC}"
    ((PASSED_TESTS++))
}

log_failed() {
    log "${RED}✗ FAILED: $1 - $2${NC}"
    ((FAILED_TESTS++))
}

log_skipped() {
    log "${YELLOW}⚠ SKIPPED: $1 - $2${NC}"
    ((SKIPPED_TESTS++))
}

run_test() {
    TEST_NAME=$1
    METHOD=$2
    ENDPOINT=$3
    EXPECTED_STATUS=$4
    DATA=${5:-""}
    HEADERS=${6:-""}
    CONTENT_TYPE=${7:-"application/json"}
    ((TOTAL_TESTS++))

    log "\n----------------------------------------------------------"
    log "Testing Endpoint: ${BLUE}$TEST_NAME${NC}"
    log "----------------------------------------------------------"
    log_request "$METHOD" "$ENDPOINT"

    # Create temporary file for response headers
    RESP_HEADERS=$(mktemp)

    # Build curl command
    CURL_CMD="curl -s -X $METHOD -w '%{http_code}' -D ${RESP_HEADERS}"
    
    # Add content type if provided
    if [ -n "$CONTENT_TYPE" ]; then
        CURL_CMD="$CURL_CMD -H 'Content-Type: $CONTENT_TYPE'"
    fi
    
    # Add Authorization header if authenticated
    if [ -n "$AUTH_TOKEN" ]; then
        CURL_CMD="$CURL_CMD -H 'Authorization: Bearer $AUTH_TOKEN'"
    fi
    
    # Add custom headers if provided
    if [ -n "$HEADERS" ]; then
        CURL_CMD="$CURL_CMD $HEADERS"
    fi
    
    # Add data if provided
    if [ -n "$DATA" ]; then
        CURL_CMD="$CURL_CMD -d '$DATA'"
    fi
    
    # Add URL
    CURL_CMD="$CURL_CMD '$BASE_URL$ENDPOINT'"
    
    # Execute curl command with retry logic for transient failures
    MAX_RETRIES=3
    RETRY_COUNT=0
    RETRY_DELAY=2
    
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        # Execute the command
        RESPONSE=$(eval "$CURL_CMD")
        STATUS_CODE=${RESPONSE: -3}
        RESPONSE_BODY=${RESPONSE:0:${#RESPONSE}-3}
        
        # Log response details
        log_response "$METHOD" "$ENDPOINT" "$STATUS_CODE" "$RESPONSE_BODY"
        
        if [[ ( "$STATUS_CODE" -ge 200 && "$STATUS_CODE" -lt 500 ) || "$STATUS_CODE" -eq "$EXPECTED_STATUS" ]]; then
            break
        fi
        
        log "${YELLOW}Transient error detected (HTTP $STATUS_CODE). Retrying in ${RETRY_DELAY}s...${NC}"
        ((RETRY_COUNT++))
        sleep $RETRY_DELAY
        RETRY_DELAY=$((RETRY_DELAY * 2)) # Exponential backoff
    done
    
    # Check if response status matches expected status
    if [ "$STATUS_CODE" -eq "$EXPECTED_STATUS" ]; then
        log_passed "$TEST_NAME"
    else
        log_failed "$TEST_NAME" "Expected status $EXPECTED_STATUS, got $STATUS_CODE"
    fi

    # Clean up temporary file
    rm -f "$RESP_HEADERS"

    # Return response for further processing if needed
    echo "$RESPONSE_BODY"
}

# ----------------------------------------
# Security Testing Functions
# ----------------------------------------

test_sql_injection() {
    log "\n=========================================================="
    log "${BLUE}SQL INJECTION TESTS${NC}"
    log "=========================================================="
    
    # Test SQL injection on plant_id parameter
    run_test "SQL Injection - Plant ID" "GET" "/api/plants/1' OR '1'='1" 400

    # Test SQL injection on authentication endpoint
    run_test "SQL Injection - Authentication" "POST" "/api/access" 401 '{"username":"admin\' OR \'1\'=\'1", "password":"password"}'
    
    # SQL injection in search parameter (if available)
    run_test "SQL Injection - Device Search" "GET" "/api/devices?search=test%27%20OR%20%271%27=%271" 200

    # Test SQL injection via user-agent header
    run_test "SQL Injection - User Agent Header" "GET" "/api/plants" 200 "" "-H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36\' OR \'1\'=\'1'"
}

test_xss_vulnerabilities() {
    log "\n=========================================================="
    log "${BLUE}CROSS-SITE SCRIPTING (XSS) TESTS${NC}"
    log "=========================================================="
    
    # Test XSS payload in URL parameters
    run_test "XSS - URL Parameter" "GET" "/api/plants?name=<script>alert(1)</script>" 200
    
    # Test XSS via JSON data submission
    run_test "XSS - JSON Payload" "POST" "/api/access" 401 '{"username":"<script>alert(1)</script>", "password":"password123"}'
    
    # Test XSS in custom headers
    run_test "XSS - Custom Header" "GET" "/api/plants" 200 "" "-H 'X-Custom-Header: <script>alert(1)</script>'"
}

test_authentication_bypass() {
    log "\n=========================================================="
    log "${BLUE}AUTHENTICATION BYPASS TESTS${NC}"
    log "=========================================================="
    
    # Test direct access to protected endpoints without authentication
    run_test "Auth Bypass - Protected Endpoint" "GET" "/api/operations/data" 401
    
    # Test with fake/malformed JWT token
    run_test "Auth Bypass - Invalid JWT" "GET" "/api/plants" 200 "" "-H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkhhY2tlciIsImlhdCI6MTUxNjIzOTAyMn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'"

    # Test accessing debug-env endpoint (which should be restricted)
    run_test "Auth Bypass - Debug Endpoint" "GET" "/api/debug-env" 403
    
    # Test access with empty authentication header
    run_test "Auth Bypass - Empty Auth Header" "GET" "/api/plants" 200 "" "-H 'Authorization: Bearer '"
}

test_injection_attacks() {
    log "\n=========================================================="
    log "${BLUE}INJECTION ATTACK TESTS${NC}"
    log "=========================================================="
    
    # Command injection test
    run_test "Command Injection - Parameter" "GET" "/api/devices?id=123;cat%20/etc/passwd" 200
    
    # LDAP injection test
    run_test "LDAP Injection" "POST" "/api/access" 401 '{"username":"*)(uid=*))(|(uid=*", "password":"password123"}'
    
    # NoSQL injection test
    run_test "NoSQL Injection" "POST" "/api/access" 401 '{"username": {"$ne": null}, "password": {"$ne": null}}'
    
    # XML injection for APIs that might accept XML
    run_test "XML Injection" "POST" "/api/import-data" 404 '<!DOCTYPE test [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><test>&xxe;</test>' "" "application/xml"
}

test_http_methods() {
    log "\n=========================================================="
    log "${BLUE}HTTP METHODS TESTS${NC}"
    log "=========================================================="
    
    # Test OPTIONS method
    run_test "OPTIONS Method" "OPTIONS" "/api/plants" 200
    
    # Test HTTP method override
    run_test "Method Override" "POST" "/api/plants" 405 "" "-H 'X-HTTP-Method-Override: PUT'"
    
    # Test TRACE method (should be disabled)
    run_test "TRACE Method" "TRACE" "/api/plants" 405
    
    # Test HEAD method
    run_test "HEAD Method" "HEAD" "/api/plants" 200
    
    # Test PUT to endpoint that should be read-only
    run_test "PUT to Read-Only" "PUT" "/api/plants" 405
    
    # Test DELETE to endpoint that should be read-only
    run_test "DELETE to Read-Only" "DELETE" "/api/plants" 405
}

test_session_attacks() {
    log "\n=========================================================="
    log "${BLUE}SESSION MANAGEMENT TESTS${NC}"
    log "=========================================================="
    
    # Test session fixation - First get a valid cookie
    run_test "Session Fixation - Auth with Preset Cookie" "POST" "/api/access" 401 '{"username":"'$USERNAME'", "password":"'$PASSWORD'"}' "-H 'Cookie: GROWATT_API_ACCESS=fixed_session_value'"
    
    # Test session hijacking with direct cookie manipulation
    run_test "Session Manipulation" "GET" "/api/plants" 200 "" "-H 'Cookie: GROWATT_API_ACCESS={\"authenticated\":true,\"username\":\"admin\"}'"
    
    # Test cross-site request forgery (simulated)
    run_test "CSRF Simulation" "POST" "/api/operations/configuration" 401 '{"system_name":"Hacked"}' "-H 'Referer: http://evil-site.com'"
}

test_rate_limiting() {
    log "\n=========================================================="
    log "${BLUE}RATE LIMITING TESTS${NC}"
    log "=========================================================="
    
    # Perform rapid requests to test rate limiting
    log "Performing 10 rapid requests to test rate limiting..."
    
    for i in {1..10}; do
        # Use a shorter timeout for these requests
        RAPID_RESPONSE=$(curl -s -m 2 -w '%{http_code}' "$BASE_URL/api/plants")
        STATUS_CODE=${RAPID_RESPONSE: -3}
        RESPONSE_BODY=${RAPID_RESPONSE:0:${#RAPID_RESPONSE}-3}
        
        log "Request $i: Status $STATUS_CODE"
        
        # If we hit a rate limit (429) or other error, we can stop
        if [ "$STATUS_CODE" -eq "429" ]; then
            log_passed "Rate Limiting Detected"
            break
        fi
        
        # Small delay to not completely overwhelm the server
        sleep 0.1
    done
    
    # If we didn't hit a rate limit after 10 requests, log as potential issue
    if [ "$STATUS_CODE" -ne "429" ]; then
        log_failed "Rate Limiting Test" "No rate limiting detected after 10 rapid requests"
    fi
}

test_error_information_leakage() {
    log "\n=========================================================="
    log "${BLUE}ERROR INFORMATION LEAKAGE TESTS${NC}"
    log "=========================================================="
    
    # Test with invalid JSON to trigger parser errors
    run_test "Invalid JSON" "POST" "/api/access" 400 '{invalid_json: "test"'
    
    # Test with invalid UUID to trigger database errors
    run_test "Invalid UUID" "GET" "/api/plants/not-a-valid-id" 404
    
    # Test very long input to trigger potential stack traces
    LONG_STRING=$(printf 'a%.0s' {1..5000})
    run_test "Buffer Overflow Attempt" "POST" "/api/access" 413 "{\"username\":\"$LONG_STRING\", \"password\":\"password123\"}"

    # Test unexpected content-type
    run_test "Unexpected Content-Type" "POST" "/api/access" 415 "<user>test</user>" "" "application/xml"
}

test_sensitive_data_exposure() {
    log "\n=========================================================="
    log "${BLUE}SENSITIVE DATA EXPOSURE TESTS${NC}"
    log "=========================================================="
    
    # Check for sensitive information in responses
    RESPONSE=$(run_test "Debug Mode Check" "GET" "/api/debug-env?debug=true" 403)
    
    # Check for password or token exposure in response
    if echo "$RESPONSE" | grep -i "password\|secret\|token\|key" > /dev/null; then
        log_failed "Sensitive Data Check" "Response contains potentially sensitive data"
    else
        log_passed "Sensitive Data Check"
    fi
    
    # Check cache-control headers to ensure proper caching of sensitive data
    run_test "Cache Control Headers" "GET" "/api/health" 200 "" "-H 'Cache-Control: no-cache'"
    
    # Check for directory traversal
    run_test "Directory Traversal" "GET" "/api/../../etc/passwd" 404
}

test_security_headers() {
    log "\n=========================================================="
    log "${BLUE}SECURITY HEADERS TESTS${NC}"
    log "=========================================================="
    
    # Create temporary file for response headers
    RESP_HEADERS=$(mktemp)
    
    # Get headers
    curl -s -o /dev/null -D "$RESP_HEADERS" "$BASE_URL/api/health"
    
    # Check for important security headers
    log "Checking security headers..."
    
    # List of headers to check
    HEADERS_TO_CHECK=(
        "Content-Security-Policy"
        "X-Content-Type-Options"
        "X-Frame-Options"
        "X-XSS-Protection"
        "Strict-Transport-Security"
        "Referrer-Policy"
    )
    
    MISSING_HEADERS=0
    
    for header in "${HEADERS_TO_CHECK[@]}"; do
        if grep -i "^$header:" "$RESP_HEADERS" > /dev/null; then
            log "${GREEN}✓ $header found${NC}"
        else
            log "${RED}✗ $header missing${NC}"
            ((MISSING_HEADERS++))
        fi
    done
    
    if [ $MISSING_HEADERS -eq 0 ]; then
        log_passed "Security Headers Check"
    else
        log_failed "Security Headers Check" "$MISSING_HEADERS security headers missing"
    fi
    
    # Clean up
    rm -f "$RESP_HEADERS"
}

# ----------------------------------------
# File Upload Vulnerability Tests
# ----------------------------------------
test_file_uploads() {
    log "\n=========================================================="
    log "${BLUE}FILE UPLOAD VULNERABILITY TESTS${NC}"
    log "=========================================================="
    
    # Create a harmless test file
    echo 'echo "test";' > test_script.php
    
    # Test uploading a PHP file (should be rejected)
    run_test "PHP File Upload" "POST" "/api/upload" 404 "-F 'file=@test_script.php'" "" "multipart/form-data"
    
    # Test uploading with malicious Content-Type
    run_test "Content-Type Bypass" "POST" "/api/upload" 404 "-F 'file=@test_script.php;type=image/jpeg'" "" "multipart/form-data"
    
    # Test null byte injection in filename
    run_test "Null Byte Injection" "POST" "/api/upload" 404 "-F 'file=@test_script.php;filename=image.jpg%00.php'" "" "multipart/form-data"
    
    # Clean up
    rm -f test_script.php
}

# ----------------------------------------
# Authentication
# ----------------------------------------
authenticate() {
    log "\n=========================================================="
    log "${BLUE}AUTHENTICATION${NC}"
    log "=========================================================="
    
    # Attempt login and capture response
    RESPONSE=$(run_test "Authentication" "POST" "/api/access" 200 "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}")
    
    # Parse authentication token if applicable
    # Assuming the API returns an authentication token in the response
    # Extract token from response if available
    if echo "$RESPONSE" | grep -q "authenticated"; then
        log "${GREEN}Successfully authenticated${NC}"
        
        # If your API uses a token-based authentication, extract and store the token
        # This is a placeholder - adjust based on your actual authentication response structure
        # AUTH_TOKEN=$(echo "$RESPONSE" | jq -r '.token // empty')
        
        # For session-based authentication, use the cookies from the response
        # This is handled automatically by curl's cookie jar
    else
        log "${RED}Authentication failed!${NC}"
        log "${YELLOW}Note: Some tests may fail due to missing authentication${NC}"
    fi
}

# ----------------------------------------
# Main API Endpoints
# ----------------------------------------
test_main_api_endpoints() {
    log "\n=========================================================="
    log "${BLUE}MAIN API ENDPOINTS${NC}"
    log "=========================================================="
    
    # Base API endpoint
    run_test "API Root" "GET" "/api" 200
    
    # Health check
    run_test "Health Check" "GET" "/api/health" 200
    
    # Activities
    run_test "Activities" "GET" "/api/activities" 200
    
    # Plants
    run_test "Plants List" "GET" "/api/plants" 200
    
    # First Plant (ID 1) - might fail if no plants exist
    run_test "Plant Detail" "GET" "/api/plants/1" 200
    
    # Devices
    run_test "Devices List" "GET" "/api/devices" 200
    
    # Weather
    run_test "Weather Data" "GET" "/api/weather" 200
    
    # Maps data
    run_test "Maps Data" "GET" "/api/maps" 200
    
    # Management data
    run_test "Management Data" "GET" "/api/management/data" 200
    
    # Connection status
    run_test "Connection Status" "GET" "/api/connection-status" 200
    
    # Cache stats
    run_test "Cache Statistics" "GET" "/api/cache-stats" 200
    
    # Fault logs (read-only)
    run_test "Fault Logs" "GET" "/api/device/fault-logs" 200
}

# ----------------------------------------
# Diagnosis Endpoints
# ----------------------------------------
test_diagnosis_endpoints() {
    log "\n=========================================================="
    log "${BLUE}DIAGNOSIS ENDPOINTS${NC}"
    log "=========================================================="
    
    # Diagnosis page
    run_test "Diagnosis Page" "GET" "/diagnosis" 200
    
    # IV Curve simulation
    run_test "IV Curve Simulation" "GET" "/api/diagnosis/simulate-iv-curve?i_ph=8.0&i_0=1e-10&r_s=0.1&r_sh=100&v_oc=40" 200
    
    # These endpoints might require specific data formats and might not be suitable for basic testing
    # Showing as examples but skipping actual execution
    log_skipped "IV Curve Analysis" "Requires specific IV curve data to test properly"
    log_skipped "IV Curve Plot" "Requires specific data to test properly"
    log_skipped "IV Curve Report" "Requires specific data to test properly"
    log_skipped "Train Model" "Requires model training data to test properly"
}

# ----------------------------------------
# Data Endpoints
# ----------------------------------------
test_data_endpoints() {
    log "\n=========================================================="
    log "${BLUE}DATA ENDPOINTS${NC}"
    log "=========================================================="
    
    # Data health
    run_test "Data Health" "GET" "/data/health" 200
    
    # Data stats
    run_test "Data Statistics" "GET" "/data/stats" 200
    
    # Sync status
    run_test "Sync Status" "GET" "/data/sync/status" 200
    
    # Power distribution
    run_test "Power Distribution" "GET" "/api/power-distribution" 200
    
    # These endpoints require POST data and might not be suitable for basic testing
    log_skipped "Data Collection" "POST endpoint that requires specific data payloads"
    log_skipped "Sync Schedule" "POST endpoint that modifies system settings"
}

# ----------------------------------------
# Operations & Scheduler Endpoints
# ----------------------------------------
test_operations_endpoints() {
    log "\n=========================================================="
    log "${BLUE}OPERATIONS & SCHEDULER ENDPOINTS${NC}"
    log "=========================================================="
    
    # Scheduler status
    run_test "Scheduler Status" "GET" "/api/scheduler/status" 200
    
    # System health 
    run_test "System Health" "GET" "/api/scheduler/system/health" 200
    
    # System health report
    run_test "System Health Report" "GET" "/api/scheduler/system/health/report" 200
    
    # Service status (using 'all' as service ID)
    run_test "Service Status" "GET" "/api/scheduler/system/services/all/status" 200
    
    # These endpoints perform actions and are not safe for automated testing
    log_skipped "Scheduler Pause" "POST endpoint that modifies system behavior"
    log_skipped "Scheduler Resume" "POST endpoint that modifies system behavior"
    log_skipped "Job Pause" "POST endpoint that modifies system behavior"
    log_skipped "Job Resume" "POST endpoint that modifies system behavior"
    log_skipped "Run Job Now" "POST endpoint that triggers immediate execution"
    log_skipped "Modify Job" "POST endpoint that modifies system configuration"
    log_skipped "System Diagnostics" "POST endpoint that runs system diagnostics"
    log_skipped "Restart Services" "POST endpoint that restarts system services"
    log_skipped "Database Optimize" "POST endpoint that performs database operations"
    log_skipped "Database Backup" "POST endpoint that performs database operations"
    log_skipped "Logs Cleanup" "POST endpoint that modifies system files"
}

# ----------------------------------------
# Cache Management
# ----------------------------------------
test_cache_endpoints() {
    log "\n=========================================================="
    log "${BLUE}CACHE MANAGEMENT ENDPOINTS${NC}"
    log "=========================================================="
    
    # Skip clear cache test as it modifies system state
    log_skipped "Clear Cache" "POST endpoint that clears application cache"
}

# ----------------------------------------
# Notification Testing
# ----------------------------------------
test_notification_endpoints() {
    log "\n=========================================================="
    log "${BLUE}NOTIFICATION ENDPOINTS${NC}"
    log "=========================================================="
    
    # Skip notification test as it might trigger actual notifications
    log_skipped "Test Notifications" "POST endpoint that triggers test notifications"
}

# ----------------------------------------
# Extra Tests (Debug, etc.)
# ----------------------------------------
test_extra_endpoints() {
    log "\n=========================================================="
    log "${BLUE}EXTRA ENDPOINTS${NC}"
    log "=========================================================="
    
    # Debug endpoints - only accessible in development mode
    run_test "Debug Environment" "GET" "/api/debug-env" 403
    
    # Test debug environment with explicit ?debug=true parameter
    run_test "Debug Environment (with param)" "GET" "/api/debug-env?debug=true" 403
}

# ----------------------------------------
# File Upload Vulnerability Tests
# ----------------------------------------
test_file_uploads() {
    log "\n=========================================================="
    log "${BLUE}FILE UPLOAD VULNERABILITY TESTS${NC}"
    log "=========================================================="
    
    # Create a harmless test file
    echo 'echo "test";' > test_script.php
    
    # Test uploading a PHP file (should be rejected)
    run_test "PHP File Upload" "POST" "/api/upload" 404 "-F 'file=@test_script.php'" "" "multipart/form-data"
    
    # Test uploading with malicious Content-Type
    run_test "Content-Type Bypass" "POST" "/api/upload" 404 "-F 'file=@test_script.php;type=image/jpeg'" "" "multipart/form-data"
    
    # Test null byte injection in filename
    run_test "Null Byte Injection" "POST" "/api/upload" 404 "-F 'file=@test_script.php;filename=image.jpg%00.php'" "" "multipart/form-data"
    
    # Clean up
    rm -f test_script.php
}

# ----------------------------------------
# Main Function
# ----------------------------------------
main() {
    log "=========================================================="
    log "${BLUE}GROWATT DEVICES MONITOR - API ENDPOINT TEST${NC}"
    log "=========================================================="
    log "Base URL: $BASE_URL"
    log "Timestamp: $(date)"
    log "=========================================================="
    
    # Login first if credentials provided
    authenticate
    
    # Run standard test groups
    test_main_api_endpoints
    test_diagnosis_endpoints
    test_data_endpoints
    test_operations_endpoints
    test_cache_endpoints
    test_notification_endpoints
    test_extra_endpoints
    
    # Run security-focused test groups
    test_sql_injection
    test_xss_vulnerabilities
    test_authentication_bypass
    test_injection_attacks
    test_http_methods
    test_session_attacks
    test_rate_limiting
    test_error_information_leakage
    test_sensitive_data_exposure
    test_security_headers
    test_file_uploads
    
    # Print summary
    log "\n=========================================================="
    log "${BLUE}TEST SUMMARY${NC}"
    log "=========================================================="
    log "Total tests: $TOTAL_TESTS"
    log "Passed: ${GREEN}$PASSED_TESTS${NC}"
    log "Failed: ${RED}$FAILED_TESTS${NC}"
    log "Skipped: ${YELLOW}$SKIPPED_TESTS${NC}"
    log "=========================================================="
    
    # Return exit code based on test results
    if [ $FAILED_TESTS -gt 0 ]; then
        log "${RED}Some tests failed.${NC} See log for details: $LOG_FILE"
        exit 1
    else
        log "${GREEN}All executed tests passed!${NC} Log saved to: $LOG_FILE"
        exit 0
    fi
}

# Run the main function
main