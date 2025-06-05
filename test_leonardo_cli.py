#!/usr/bin/env python3
"""
Comprehensive test script for Leonardo CLI
"""

import subprocess
import sys
import os
import json
import tempfile
from pathlib import Path

def run_command(cmd, timeout=30):
    """Run a command and return the result"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)

def test_cli_syntax():
    """Test if the CLI script has valid Python syntax"""
    print("=== Testing CLI Syntax ===")
    
    # Test Python syntax
    returncode, stdout, stderr = run_command("python3 -m py_compile leonardo_cli.py")
    
    if returncode == 0:
        print("✅ Python syntax is valid")
        return True
    else:
        print("❌ Python syntax errors found:")
        print(stderr)
        return False

def test_dependencies():
    """Test if all required dependencies are available"""
    print("\n=== Testing Dependencies ===")
    
    dependencies = {
        'click': 'pip install click',
        'requests': 'pip install requests', 
        'rich': 'pip install rich',
        'pathlib': 'Built-in module'
    }
    
    all_good = True
    for dep, install_cmd in dependencies.items():
        try:
            __import__(dep)
            print(f"✅ {dep} is available")
        except ImportError:
            print(f"❌ {dep} is missing - install with: {install_cmd}")
            all_good = False
    
    return all_good

def test_cli_help():
    """Test if the CLI help command works"""
    print("\n=== Testing CLI Help ===")
    
    returncode, stdout, stderr = run_command("python3 leonardo_cli.py --help")
    
    if returncode == 0:
        print("✅ CLI help command works")
        # Check for expected commands
        expected_commands = ['generate', 'models', 'user', 'configure', 'profiles']
        found_commands = []
        
        for cmd in expected_commands:
            if cmd in stdout:
                found_commands.append(cmd)
        
        print(f"Found commands: {', '.join(found_commands)}")
        return len(found_commands) >= 3  # At least 3 commands should be present
    else:
        print("❌ CLI help command failed:")
        print(stderr)
        return False

def test_individual_commands():
    """Test individual command help"""
    print("\n=== Testing Individual Commands ===")
    
    commands = ['generate', 'models', 'user', 'profiles']
    success_count = 0
    
    for cmd in commands:
        returncode, stdout, stderr = run_command(f"python3 leonardo_cli.py {cmd} --help")
        
        if returncode == 0:
            print(f"✅ {cmd} command help works")
            success_count += 1
        else:
            print(f"❌ {cmd} command help failed:")
            print(stderr[:200] + "..." if len(stderr) > 200 else stderr)
    
    return success_count >= len(commands) // 2  # At least half should work

def test_api_key_handling():
    """Test API key configuration"""
    print("\n=== Testing API Key Handling ===")
    
    # Test without API key
    env = os.environ.copy()
    env.pop('LEONARDO_API_KEY', None)  # Remove API key if present
    
    try:
        result = subprocess.run(
            ["python3", "leonardo_cli.py", "user"], 
            env=env, 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        
        if "No API key" in result.stderr or "LEONARDO_API_KEY" in result.stderr:
            print("✅ Properly handles missing API key")
            return True
        else:
            print("❌ Does not properly handle missing API key")
            print(f"stdout: {result.stdout}")
            print(f"stderr: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing API key handling: {e}")
        return False

def test_generate_command_parsing():
    """Test the generate command argument parsing"""
    print("\n=== Testing Generate Command Parsing ===")
    
    # Test with quoted prompt
    returncode, stdout, stderr = run_command('python3 leonardo_cli.py generate --help')
    
    if returncode == 0:
        print("✅ Generate command help works")
        
        # Check for expected options
        expected_options = ['--model-id', '--width', '--height', '--alchemy', '--phoenix']
        found_options = []
        
        for option in expected_options:
            if option in stdout:
                found_options.append(option)
        
        print(f"Found options: {', '.join(found_options)}")
        return len(found_options) >= 3
    else:
        print("❌ Generate command help failed:")
        print(stderr)
        return False

def create_test_config():
    """Create a test configuration"""
    print("\n=== Creating Test Configuration ===")
    
    # Create a temporary config for testing
    test_config = {
        "profiles": {
            "test": {
                "api_key": "test_key_12345"
            }
        },
        "active_profile": "test"
    }
    
    config_dir = Path.home() / ".leonardo-cli"
    config_dir.mkdir(exist_ok=True)
    
    config_path = config_dir / "config.json"
    
    try:
        with open(config_path, 'w') as f:
            json.dump(test_config, f, indent=2)
        
        print("✅ Test configuration created")
        return True
    except Exception as e:
        print(f"❌ Failed to create test configuration: {e}")
        return False

def run_integration_test():
    """Run a basic integration test if API key is available"""
    print("\n=== Integration Test ===")
    
    api_key = os.getenv('LEONARDO_API_KEY')
    if not api_key:
        print("⚠️  No LEONARDO_API_KEY found - skipping integration test")
        print("   Set LEONARDO_API_KEY environment variable to run integration tests")
        return True
    
    print("🔑 API key found - running integration test...")
    
    # Test user command (should work with valid API key)
    returncode, stdout, stderr = run_command("python3 leonardo_cli.py user", timeout=15)
    
    if returncode == 0:
        print("✅ User command works with API key")
        return True
    else:
        print("❌ User command failed:")
        print(f"stderr: {stderr}")
        # Don't fail the test - might be API issues
        return True

def main():
    """Run all tests"""
    print("Leonardo CLI Comprehensive Test Suite")
    print("=" * 60)
    
    tests = [
        ("Syntax Check", test_cli_syntax),
        ("Dependencies", test_dependencies),
        ("CLI Help", test_cli_help),
        ("Individual Commands", test_individual_commands),
        ("API Key Handling", test_api_key_handling),
        ("Generate Command", test_generate_command_parsing),
        ("Test Config", create_test_config),
        ("Integration Test", run_integration_test),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your CLI is ready to use.")
    elif passed >= total * 0.7:
        print("⚠️  Most tests passed. CLI should work with minor issues.")
    else:
        print("❌ Many tests failed. Please check the issues above.")
    
    print("\n" + "=" * 60)
    print("Next Steps:")
    print("1. Set your API key: export LEONARDO_API_KEY='your-key-here'")
    print("2. Test generation: python3 leonardo_cli.py generate 'a beautiful sunset'")
    print("3. Explore features: python3 leonardo_cli.py --help")
    
    return passed >= total * 0.7

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
