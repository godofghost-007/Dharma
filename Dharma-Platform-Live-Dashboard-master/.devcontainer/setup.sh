#!/bin/bash
# Project Dharma - Codespace Setup Script
# Optimized for hackathon demo environment

echo "🚀 Setting up Project Dharma for Hackathon Demo..."

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements_demo.txt
pip install streamlit pandas numpy plotly

# Install additional tools for demo
echo "🔧 Installing demo tools..."
pip install tree

# Make scripts executable
echo "🔐 Setting up permissions..."
chmod +x scripts/*.sh
chmod +x codespace_demo.py
chmod +x launch.py

# Create demo shortcuts
echo "⚡ Creating demo shortcuts..."
echo '#!/bin/bash' > /usr/local/bin/demo
echo 'cd /workspaces/Project-Dharma && python codespace_demo.py' >> /usr/local/bin/demo
chmod +x /usr/local/bin/demo

echo '#!/bin/bash' > /usr/local/bin/dashboard
echo 'cd /workspaces/Project-Dharma && streamlit run demo_app.py --server.port 8501' >> /usr/local/bin/dashboard
chmod +x /usr/local/bin/dashboard

echo '#!/bin/bash' > /usr/local/bin/verify
echo 'cd /workspaces/Project-Dharma && python verify_completion.py' >> /usr/local/bin/verify
chmod +x /usr/local/bin/verify

# Setup welcome message
echo "📋 Setting up welcome message..."
cat << 'EOF' > ~/.zshrc_custom
echo ""
echo "🛡️  PROJECT DHARMA - HACKATHON DEMO ENVIRONMENT"
echo "================================================"
echo ""
echo "🎯 Quick Commands:"
echo "   demo      - Launch demo menu"
echo "   dashboard - Start interactive dashboard"
echo "   verify    - Check system completion"
echo ""
echo "📊 Project Status: 100% Complete (15/15 tasks)"
echo "🏆 Ready for hackathon presentation!"
echo ""
EOF

echo "source ~/.zshrc_custom" >> ~/.zshrc

# Display completion message
echo ""
echo "✅ Project Dharma setup complete!"
echo "🎪 Ready for hackathon demo!"
echo ""
echo "🚀 Quick start:"
echo "   Type 'demo' to launch the demo menu"
echo "   Type 'dashboard' for interactive demo"
echo "   Type 'verify' to check completion status"
echo ""