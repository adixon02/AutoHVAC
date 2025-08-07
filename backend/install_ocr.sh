#!/bin/bash

# OCR Installation Script for AutoHVAC
# This script installs Tesseract and PaddleOCR for enhanced blueprint text extraction

echo "======================================"
echo "AutoHVAC OCR Installation Script"
echo "======================================"
echo ""

# Detect OS
OS=$(uname -s)

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install Tesseract based on OS
install_tesseract() {
    echo "📦 Installing Tesseract OCR..."
    
    if [ "$OS" = "Darwin" ]; then
        # macOS installation
        if command_exists brew; then
            echo "  Using Homebrew to install Tesseract..."
            brew install tesseract
        elif command_exists port; then
            echo "  Using MacPorts to install Tesseract..."
            sudo port install tesseract
        else
            echo "❌ Neither Homebrew nor MacPorts found!"
            echo "   Please install Homebrew first:"
            echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
            return 1
        fi
    elif [ "$OS" = "Linux" ]; then
        # Linux installation
        if command_exists apt-get; then
            echo "  Using apt-get to install Tesseract..."
            sudo apt-get update
            sudo apt-get install -y tesseract-ocr libtesseract-dev
        elif command_exists yum; then
            echo "  Using yum to install Tesseract..."
            sudo yum install -y tesseract
        else
            echo "❌ No supported package manager found!"
            return 1
        fi
    else
        echo "❌ Unsupported OS: $OS"
        return 1
    fi
    
    echo "✅ Tesseract installation complete!"
}

# Install Python packages
install_python_packages() {
    echo ""
    echo "📦 Installing Python packages..."
    
    # Check Python version
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    echo "  Python version: $PYTHON_VERSION"
    
    # Install PaddlePaddle (CPU version)
    echo "  Installing PaddlePaddle..."
    if [ "$OS" = "Darwin" ]; then
        # macOS - use specific version for Intel Mac
        pip3 install paddlepaddle==2.6.1 -i https://pypi.org/simple/
    else
        # Linux
        pip3 install paddlepaddle==2.6.1 -i https://pypi.org/simple/
    fi
    
    # Install PaddleOCR
    echo "  Installing PaddleOCR..."
    pip3 install "paddleocr>=2.7.0"
    
    # Install pytesseract
    echo "  Installing pytesseract..."
    pip3 install pytesseract
    
    echo "✅ Python packages installation complete!"
}

# Verify installation
verify_installation() {
    echo ""
    echo "🔍 Verifying installation..."
    
    # Check Tesseract
    if command_exists tesseract; then
        TESS_VERSION=$(tesseract --version 2>&1 | head -n 1)
        echo "  ✅ Tesseract: $TESS_VERSION"
    else
        echo "  ❌ Tesseract not found in PATH"
    fi
    
    # Check Python packages
    python3 -c "
import sys
errors = []
try:
    import paddlepaddle
    print('  ✅ PaddlePaddle: ' + paddlepaddle.__version__)
except ImportError:
    errors.append('PaddlePaddle')
    print('  ❌ PaddlePaddle not installed')

try:
    import paddleocr
    print('  ✅ PaddleOCR installed')
except ImportError:
    errors.append('PaddleOCR')
    print('  ❌ PaddleOCR not installed')

try:
    import pytesseract
    print('  ✅ pytesseract installed')
except ImportError:
    errors.append('pytesseract')
    print('  ❌ pytesseract not installed')

if errors:
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ All components installed successfully!"
        return 0
    else
        echo ""
        echo "⚠️  Some components failed to install. Please check the errors above."
        return 1
    fi
}

# Main installation flow
main() {
    echo "This script will install:"
    echo "  • Tesseract OCR (system package)"
    echo "  • PaddlePaddle (Python package)"
    echo "  • PaddleOCR (Python package)"
    echo "  • pytesseract (Python package)"
    echo ""
    read -p "Continue with installation? (y/n) " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        exit 0
    fi
    
    # Check if Tesseract is already installed
    if command_exists tesseract; then
        echo "ℹ️  Tesseract is already installed: $(tesseract --version 2>&1 | head -n 1)"
        read -p "Skip Tesseract installation? (y/n) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            install_tesseract
        fi
    else
        install_tesseract
    fi
    
    # Install Python packages
    install_python_packages
    
    # Verify everything
    verify_installation
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "======================================"
        echo "🎉 OCR setup complete!"
        echo "======================================"
        echo ""
        echo "Next steps:"
        echo "1. Make sure ENABLE_PADDLE_OCR=true in your .env file"
        echo "2. Restart your Python application"
        echo "3. OCR will now enhance blueprint text extraction"
    else
        echo ""
        echo "⚠️  Installation completed with some issues."
        echo "Please review the errors above and try again."
    fi
}

# Run main function
main