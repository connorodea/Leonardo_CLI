#!/bin/bash

echo "=== Leonardo CLI Dependency Installation ==="

# Check if we're in a virtual environment
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ Virtual environment detected: $VIRTUAL_ENV"
else
    echo "⚠️  No virtual environment detected. Consider creating one:"
    echo "   python3 -m venv leonardo-cli-env"
    echo "   source leonardo-cli-env/bin/activate"
    echo ""
fi

# Install required packages
echo "Installing required Python packages..."

pip install --upgrade pip

# Core dependencies
pip install click>=8.0.0
pip install requests>=2.25.0
pip install rich>=10.0.0

# Optional but recommended
pip install pathlib

echo ""
echo "=== Installation Summary ==="
echo "Installed packages:"
pip list | grep -E "(click|requests|rich|pathlib)"

echo ""
echo "=== Making CLI Executable ==="
chmod +x leonardo_cli.py

echo ""
echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "1. Configure your API key: ./leonardo_cli.py configure"
echo "2. Test the CLI: ./leonardo_cli.py --help"
echo "3. Start generating: ./leonardo_cli.py generate 'your prompt here'"
