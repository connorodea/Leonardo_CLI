#!/bin/bash
# Comprehensive test script for Leonardo CLI

echo "=== Leonardo CLI Test Script ==="
echo "This script will test all major functionality of the Leonardo CLI"

# Set output directory for test results
TEST_DIR="./leonardo-test-results"
mkdir -p "$TEST_DIR"

echo -e "\n=== BASIC FUNCTIONALITY TESTS ==="

echo -e "\n>> Testing configuration status"
./leonardo_cli.py profiles

echo -e "\n>> Testing user account info"
./leonardo_cli.py user

echo -e "\n>> Testing API token usage"
./leonardo_cli.py usage

echo -e "\n>> Testing cost estimation"
./leonardo_cli.py estimate --width 512 --height 512 --num 1 --alchemy

echo -e "\n=== IMAGE GENERATION TESTS ==="

echo -e "\n>> Testing basic generation with quotes"
./leonardo_cli.py generate "A sunset over mountains" --alchemy

echo -e "\n>> Testing Phoenix model"
./leonardo_cli.py generate "A futuristic cityscape" --phoenix --contrast 3.5

echo -e "\n>> Getting models list"
./leonardo_cli.py models --all

echo -e "\n=== CLI COMMAND DIAGNOSTICS ==="
# This section will help diagnose command parsing issues

echo -e "\n>> Command syntax test"
# Test if the issue is with quote handling
./leonardo_cli.py generate "Test prompt with spaces"

# Alternative syntax test
echo -e "\n>> Alternative syntax test with variable" 
PROMPT="Another test prompt with spaces"
./leonardo_cli.py generate "$PROMPT"

echo -e "\n>> Command argument inspection"
# Create a diagnostic command to show exactly how args are processed
cat > ./diagnostic.py << 'EOL'
#!/usr/bin/env python3
import sys
print("Number of arguments:", len(sys.argv))
print("Arguments:", sys.argv)
EOL
chmod +x ./diagnostic.py
./diagnostic.py generate "Test prompt"

echo -e "\n=== TEST COMPLETE ==="
echo "Check $TEST_DIR for any generated outputs"
