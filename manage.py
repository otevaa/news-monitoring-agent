#!/usr/bin/env python3
"""
NewsMonitor Pro - CLI Management Script
"""

import argparse
import os
import sys
from datetime import datetime

def run_server():
    """Run the Flask development server"""
    print("🚀 Starting NewsMonitor Pro...")
    print("📍 Server will be available at: http://localhost:5000")
    print("💡 Press Ctrl+C to stop the server")
    print("-" * 50)
    
    os.system("python app.py")

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    os.system("pip install -r requirements.txt")
    print("✅ Dependencies installed successfully!")

def check_status():
    """Check system status"""
    print("🔍 NewsMonitor Pro Status Check")
    print("-" * 30)
    
    # Check if required files exist
    required_files = [
        'app.py',
        'requirements.txt',
        'agent/fetch_rss.py',
        'agent/google_oauth.py',
        'agent/campaign_manager.py',
        'agent/integrations.py',
        'templates/dashboard.html'
    ]
    
    missing_files = []
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file} - MISSING")
            missing_files.append(file)
    
    print("-" * 30)
    
    if missing_files:
        print(f"⚠️  {len(missing_files)} file(s) missing!")
        print("Please ensure all files are present before running the application.")
        return False
    else:
        print("🎉 All required files are present!")
        
    # Check for data files
    print("\n📊 Data Files:")
    data_files = ['campaigns.json', 'integrations.json']
    for file in data_files:
        if os.path.exists(file):
            print(f"✅ {file} exists")
        else:
            print(f"📝 {file} will be created on first run")
    
    return True

def reset_data():
    """Reset all data (campaigns and integrations)"""
    print("⚠️  WARNING: This will delete all your campaigns and integration settings!")
    confirm = input("Type 'RESET' to confirm: ")
    
    if confirm == 'RESET':
        data_files = ['campaigns.json', 'integrations.json']
        for file in data_files:
            if os.path.exists(file):
                os.remove(file)
                print(f"🗑️  Deleted {file}")
        print("✅ Data reset complete!")
    else:
        print("❌ Reset cancelled")

def show_info():
    """Show application information"""
    print("""
🔍 NewsMonitor Pro
==================

A professional news monitoring platform that helps you:

📈 Features:
  • Create automated news monitoring campaigns
  • Search Google News RSS feeds
  • Save articles to Google Sheets or Airtable
  • Professional dashboard interface
  • Campaign management (pause, resume, delete)
  • Real-time statistics and analytics

🚀 Quick Start:
  1. Run: python manage.py install
  2. Run: python manage.py run
  3. Open: http://localhost:5000
  4. Connect your Google account
  5. Create your first campaign!

📚 Commands:
  • python manage.py run        - Start the server
  • python manage.py install    - Install dependencies
  • python manage.py status     - Check system status
  • python manage.py reset      - Reset all data
  • python manage.py info       - Show this information

🔧 Configuration:
  • Google OAuth: Place client_secret.json in root directory
  • Airtable: Configure API key through the web interface

📞 Support:
  For help and documentation, visit the integrations page in the app.
    """)

def main():
    parser = argparse.ArgumentParser(
        description='NewsMonitor Pro Management Script',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'command',
        choices=['run', 'install', 'status', 'reset', 'info'],
        help='Command to execute'
    )
    
    if len(sys.argv) == 1:
        show_info()
        return
    
    args = parser.parse_args()
    
    print(f"NewsMonitor Pro - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    if args.command == 'run':
        if check_status():
            run_server()
        else:
            print("\n❌ Please fix the issues above before running the server.")
            print("💡 Try: python manage.py install")
    
    elif args.command == 'install':
        install_dependencies()
    
    elif args.command == 'status':
        check_status()
    
    elif args.command == 'reset':
        reset_data()
    
    elif args.command == 'info':
        show_info()

if __name__ == '__main__':
    main()
