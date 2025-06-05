#!/bin/bash

echo "🎨 Leonardo AI CLI Setup Script"
echo "================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python 3 is installed
print_status "Checking Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    print_success "Found $PYTHON_VERSION"
else
    print_error "Python 3 is not installed. Please install Python 3.7 or higher."
    exit 1
fi

# Check if pip is installed
print_status "Checking pip installation..."
if command -v pip3 &> /dev/null; then
    print_success "pip3 is available"
else
    print_error "pip3 is not installed. Please install pip."
    exit 1
fi

# Create virtual environment if it doesn't exist
VENV_DIR="leonardo-cli-env"
if [ ! -d "$VENV_DIR" ]; then
    print_status "Creating virtual environment..."
    python3 -m venv $VENV_DIR
    print_success "Virtual environment created: $VENV_DIR"
else
    print_warning "Virtual environment already exists: $VENV_DIR"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source $VENV_DIR/bin/activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install required packages
print_status "Installing required packages..."
pip install click>=8.0.0
pip install requests>=2.25.0
pip install rich>=10.0.0

# Verify installations
print_status "Verifying installations..."
python3 -c "import click, requests, rich; print('All packages imported successfully')"

if [ $? -eq 0 ]; then
    print_success "All dependencies installed successfully!"
else
    print_error "Some dependencies failed to install."
    exit 1
fi

# Make CLI executable
print_status "Making CLI executable..."
chmod +x leonardo_cli.py
chmod +x leonardo_cli_fixed.py

# Create output directories
print_status "Creating output directories..."
mkdir -p leonardo-output
mkdir -p leonardo-batch-output
mkdir -p leonardo-downloads

# Create config directory
print_status "Creating config directory..."
mkdir -p ~/.leonardo-cli/templates

# Run tests
print_status "Running tests..."
python3 test_leonardo_cli.py

# Check for API key
print_status "Checking for API key..."
if [ -z "$LEONARDO_API_KEY" ]; then
    print_warning "LEONARDO_API_KEY environment variable not set."
    echo ""
    echo "To set your API key:"
    echo "  export LEONARDO_API_KEY='your-api-key-here'"
    echo ""
    echo "Or add it to your ~/.bashrc or ~/.zshrc:"
    echo "  echo 'export LEONARDO_API_KEY=\"your-api-key-here\"' >> ~/.bashrc"
    echo ""
else
    print_success "LEONARDO_API_KEY is set"
fi

# Create a simple usage example
cat > example_usage.sh << 'EOF'
#!/bin/bash

# Example usage of Leonardo CLI

echo "🎨 Leonardo CLI Examples"
echo "======================="

# Activate virtual environment
source leonardo-cli-env/bin/activate

echo ""
echo "1. Basic image generation:"
echo "   python3 leonardo_cli.py generate 'a beautiful sunset over mountains'"

echo ""
echo "2. High-quality generation with Alchemy:"
echo "   python3 leonardo_cli.py generate 'a futuristic cityscape' --alchemy --width 1024 --height 1024"

echo ""
echo "3. Phoenix model with custom contrast:"
echo "   python3 leonardo_cli.py generate 'a magical forest' --phoenix --contrast 3.5"

echo ""
echo "4. Check your account info:"
echo "   python3 leonardo_cli.py user"

echo ""
echo "5. List available models:"
echo "   python3 leonardo_cli.py models"

echo ""
echo "6. Interactive shell mode:"
echo "   python3 leonardo_cli.py shell"

echo ""
echo "Remember to set your API key first:"
echo "   export LEONARDO_API_KEY='your-api-key-here'"
EOF

chmod +x example_usage.sh

print_success "Setup complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Set your API key: export LEONARDO_API_KEY='your-api-key-here'"
echo "2. Activate the virtual environment: source leonardo-cli-env/bin/activate"
echo "3. Test the CLI: python3 leonardo_cli.py --help"
echo "4. Generate your first image: python3 leonardo_cli.py generate 'a beautiful landscape'"
echo "5. Check example_usage.sh for more examples"
echo ""
echo "🎉 Happy generating!"
