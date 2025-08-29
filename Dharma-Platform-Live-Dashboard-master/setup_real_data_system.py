#!/usr/bin/env python3
"""
Setup Script for Dharma Platform Real Data System
Helps users configure API keys and initialize the system
"""

import os
import sys
import subprocess
import asyncio
from pathlib import Path
from api_config import setup_environment_variables, get_api_config
from real_data_collector import RealDataCollector
from real_time_analyzer import RealTimeAnalyzer

class DharmaSetup:
    """Setup manager for Dharma Platform"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        
    def install_dependencies(self):
        """Install required dependencies"""
        print("📦 Installing required dependencies...")
        
        dependencies = [
            'streamlit>=1.28.0',
            'fastapi>=0.104.0',
            'uvicorn[standard]>=0.24.0',
            'pandas>=2.0.0',
            'numpy>=1.24.0',
            'plotly>=5.17.0',
            'tweepy>=4.14.0',
            'aiohttp>=3.9.0',
            'textblob>=0.17.0',
            'requests>=2.31.0',
            'python-dotenv>=1.0.0'
        ]
        
        for dep in dependencies:
            try:
                print(f"Installing {dep}...")
                result = subprocess.run([
                    sys.executable, '-m', 'pip', 'install', dep
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    print(f"✅ {dep} installed")
                else:
                    print(f"⚠️  Warning: {dep} installation failed")
                    
            except Exception as e:
                print(f"❌ Error installing {dep}: {e}")
        
        # Download TextBlob corpora
        try:
            print("📚 Downloading TextBlob corpora...")
            import nltk
            nltk.download('punkt', quiet=True)
            nltk.download('brown', quiet=True)
            print("✅ TextBlob corpora downloaded")
        except:
            print("⚠️  TextBlob corpora download failed (optional)")
    
    def setup_api_keys(self):
        """Setup API keys interactively"""
        print("\n🔑 API Keys Configuration")
        print("=" * 40)
        
        setup_environment_variables()
    
    def initialize_database(self):
        """Initialize the database"""
        print("\n🗄️  Initializing database...")
        
        try:
            collector = RealDataCollector()
            print("✅ Database initialized successfully")
            return True
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            return False
    
    def test_api_connections(self):
        """Test API connections"""
        print("\n🔌 Testing API connections...")
        
        config = get_api_config()
        
        # Test Twitter
        if config.is_twitter_configured():
            try:
                import tweepy
                client = tweepy.Client(bearer_token=config.twitter_bearer_token)
                # Simple test query
                tweets = client.search_recent_tweets(query="test", max_results=10)
                print("✅ Twitter API connection successful")
            except Exception as e:
                print(f"❌ Twitter API test failed: {e}")
        else:
            print("⚠️  Twitter API not configured")
        
        # Test YouTube
        if config.is_youtube_configured():
            try:
                import aiohttp
                import asyncio
                
                async def test_youtube():
                    async with aiohttp.ClientSession() as session:
                        url = "https://www.googleapis.com/youtube/v3/search"
                        params = {
                            'part': 'snippet',
                            'q': 'test',
                            'type': 'video',
                            'maxResults': 1,
                            'key': config.youtube_api_key
                        }
                        async with session.get(url, params=params) as response:
                            return response.status == 200
                
                if asyncio.run(test_youtube()):
                    print("✅ YouTube API connection successful")
                else:
                    print("❌ YouTube API test failed")
                    
            except Exception as e:
                print(f"❌ YouTube API test failed: {e}")
        else:
            print("⚠️  YouTube API not configured")
        
        # Test Reddit (always available)
        try:
            import aiohttp
            
            async def test_reddit():
                async with aiohttp.ClientSession() as session:
                    url = "https://www.reddit.com/r/india/hot.json"
                    params = {'limit': 1}
                    headers = {'User-Agent': 'DharmaPlatform/1.0'}
                    async with session.get(url, params=params, headers=headers) as response:
                        return response.status == 200
            
            if asyncio.run(test_reddit()):
                print("✅ Reddit API connection successful")
            else:
                print("❌ Reddit API test failed")
                
        except Exception as e:
            print(f"❌ Reddit API test failed: {e}")
    
    def collect_initial_data(self):
        """Collect initial data sample"""
        print("\n📊 Collecting initial data sample...")
        
        try:
            async def collect_data():
                collector = RealDataCollector()
                posts = await collector.collect_all_data(max_results_per_platform=20)
                return len(posts)
            
            post_count = asyncio.run(collect_data())
            print(f"✅ Collected {post_count} initial posts")
            
            # Run initial analysis
            print("🤖 Running initial AI analysis...")
            analyzer = RealTimeAnalyzer()
            asyncio.run(analyzer.run_analysis_batch())
            print("✅ Initial analysis complete")
            
            return True
            
        except Exception as e:
            print(f"❌ Initial data collection failed: {e}")
            return False
    
    def create_startup_script(self):
        """Create a startup script for easy launching"""
        print("\n📝 Creating startup script...")
        
        startup_script = '''#!/usr/bin/env python3
"""
Dharma Platform Startup Script
Quick start for the real data system
"""

import subprocess
import sys
import webbrowser
import time
from pathlib import Path

def main():
    print("🚀 Starting Dharma Platform...")
    
    # Start the enhanced dashboard
    dashboard_file = Path(__file__).parent / "enhanced_real_data_dashboard.py"
    
    try:
        # Start Streamlit dashboard
        process = subprocess.Popen([
            sys.executable, '-m', 'streamlit', 'run', 
            str(dashboard_file),
            '--server.port', '8501',
            '--server.headless', 'true',
            '--browser.gatherUsageStats', 'false'
        ])
        
        print("✅ Dashboard started on http://localhost:8501")
        print("🌐 Opening in browser...")
        
        # Wait a moment then open browser
        time.sleep(3)
        webbrowser.open('http://localhost:8501')
        
        print("\\n⏳ Dashboard running... Press Ctrl+C to stop")
        
        # Wait for user to stop
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\\n⏹️  Stopping dashboard...")
            process.terminate()
            process.wait()
            print("✅ Dashboard stopped")
            
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")

if __name__ == "__main__":
    main()
'''
        
        startup_file = self.project_root / "start_dharma.py"
        with open(startup_file, 'w') as f:
            f.write(startup_script)
        
        # Make executable on Unix systems
        try:
            import stat
            startup_file.chmod(startup_file.stat().st_mode | stat.S_IEXEC)
        except:
            pass
        
        print(f"✅ Created startup script: {startup_file}")
    
    def show_completion_info(self):
        """Show completion information"""
        print("\n" + "="*50)
        print("🎉 Dharma Platform Setup Complete!")
        print("="*50)
        
        config = get_api_config()
        configured_platforms = config.get_configured_platforms()
        
        print(f"\n📊 Configured Platforms: {', '.join(configured_platforms)}")
        
        print("\n🚀 How to Start:")
        print("1. Run: python start_dharma.py")
        print("2. Or run: python enhanced_real_data_dashboard.py")
        print("3. Or run: streamlit run enhanced_real_data_dashboard.py")
        
        print("\n📋 Available Features:")
        print("• Real-time social media data collection")
        print("• AI-powered sentiment analysis")
        print("• Bot detection and risk assessment")
        print("• Interactive dashboard with clickable posts")
        print("• Threat level monitoring")
        print("• Multi-platform support")
        
        print("\n🔧 Management Commands:")
        print("• Collect data: python real_data_collector.py")
        print("• Run analysis: python real_time_analyzer.py")
        print("• Configure APIs: python api_config.py")
        
        print("\n💡 Tips:")
        print("• Add more API keys anytime by running: python api_config.py")
        print("• The system works with Reddit even without API keys")
        print("• Click on threat posts in the dashboard to view originals")
        print("• Data is stored in dharma_real_data.db SQLite database")
        
        if not any([config.is_twitter_configured(), config.is_youtube_configured()]):
            print("\n⚠️  Note: Limited to Reddit data without API keys")
            print("   Add Twitter/YouTube API keys for full functionality")
    
    def run_setup(self):
        """Run the complete setup process"""
        print("🛡️  Dharma Platform Real Data System Setup")
        print("=" * 45)
        
        try:
            # Install dependencies
            self.install_dependencies()
            
            # Setup API keys
            self.setup_api_keys()
            
            # Initialize database
            if not self.initialize_database():
                print("❌ Setup failed at database initialization")
                return False
            
            # Test API connections
            self.test_api_connections()
            
            # Collect initial data
            if not self.collect_initial_data():
                print("⚠️  Initial data collection failed, but setup continues...")
            
            # Create startup script
            self.create_startup_script()
            
            # Show completion info
            self.show_completion_info()
            
            return True
            
        except KeyboardInterrupt:
            print("\n⏹️  Setup interrupted by user")
            return False
        except Exception as e:
            print(f"\n❌ Setup failed: {e}")
            return False

def main():
    """Main setup function"""
    setup = DharmaSetup()
    
    print("Welcome to Dharma Platform Setup!")
    print("This will configure the real data collection system.")
    
    response = input("\nProceed with setup? (y/n): ").strip().lower()
    if response not in ['y', 'yes']:
        print("Setup cancelled.")
        return
    
    success = setup.run_setup()
    
    if success:
        print("\n🎉 Setup completed successfully!")
        
        start_now = input("\nStart the dashboard now? (y/n): ").strip().lower()
        if start_now in ['y', 'yes']:
            print("🚀 Starting dashboard...")
            subprocess.run([sys.executable, "start_dharma.py"])
    else:
        print("\n❌ Setup failed. Please check the errors above.")

if __name__ == "__main__":
    main()