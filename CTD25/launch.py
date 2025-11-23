#!/usr/bin/env python3
"""
Chess Game Launcher
Ensures we're running from the correct directory and launches the appropriate component.
"""

import os
import sys
import subprocess
import asyncio

def check_environment():
    """Check if we're in the correct directory and have all required files"""
    print("Checking environment...")
    
    # Check if we're in the project root
    if not os.path.exists("pieces/board.csv"):
        print(" Error: Cannot find pieces/board.csv")
        print("   Make sure you're running this from the CTD25_Solutions directory")
        return False
    
    if not os.path.exists("KFC_Py/run.py"):
        print(" Error: Cannot find KFC_Py/run.py")
        print("   Make sure the KFC_Py directory exists")
        return False
    
    print(" Environment check passed")
    print(f"   Project directory: {os.getcwd()}")
    return True

def install_requirements():
    """Install required packages"""
    print("Installing required packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print(" Requirements installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f" Error installing requirements: {e}")
        return False

async def run_server():
    """Run the server"""
    print("🖥️  Starting Chess Game Server...")
    try:
        # Add current directory to Python path
        sys.path.insert(0, os.path.join(os.getcwd(), 'KFC_Py'))
        
        from server import main as server_main
        await server_main()
    except Exception as e:
        print(f" Server error: {e}")

async def run_client():
    """Run the graphics client"""
    print(" Starting Chess Game Client (Graphics)...")
    try:
        # Add current directory to Python path
        sys.path.insert(0, os.path.join(os.getcwd(), 'KFC_Py'))
        
        from fixed_client import main as client_main
        await client_main()
    except Exception as e:
        print(f" Client error: {e}")

async def run_console():
    """Run the console client"""
    print(" Starting Chess Game Client (Console)...")
    try:
        # Add current directory to Python path
        sys.path.insert(0, os.path.join(os.getcwd(), 'KFC_Py'))
        
        from client import main as console_main
        await console_main()
    except Exception as e:
        print(f" Console client error: {e}")

def main():
    if not check_environment():
        sys.exit(1)
    
    if len(sys.argv) < 2:
        print("Chess Game - Client/Server")
        print("=" * 40)
        print("Usage:")
        print("  python launch.py server    # Start the server")
        print("  python launch.py client    # Start a client with graphics")
        print("  python launch.py console   # Start a console-only client")
        print("  python launch.py install   # Install requirements")
        print()
        print("Example workflow:")
        print("  1. python launch.py install   # First time setup")
        print("  2. python launch.py server    # In terminal 1")
        print("  3. python launch.py client    # In terminal 2")
        print("  4. python launch.py client    # In terminal 3")
        return
    
    mode = sys.argv[1].lower()
    
    if mode == "install":
        install_requirements()
    elif mode == "server":
        asyncio.run(run_server())
    elif mode == "client":
        asyncio.run(run_client())
    elif mode == "console":
        asyncio.run(run_console())
    else:
        print(f" Unknown mode: {mode}")
        print("Use 'server', 'client', 'console', or 'install'")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n Goodbye!")
    except Exception as e:
        print(f" Unexpected error: {e}")
        sys.exit(1)
