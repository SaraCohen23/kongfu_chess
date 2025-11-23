#!/usr/bin/env python3
"""
Quick start script for Chess Game Server/Client
"""

import sys
import asyncio
import subprocess
import time

def install_requirements():
    """Install required packages"""
    print("Installing required packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Requirements installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing requirements: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Chess Game - Client/Server")
        print("Usage:")
        print("  python run.py server    # Start the server")
        print("  python run.py client    # Start a client with graphics")
        print("  python run.py console   # Start a console-only client")
        print("  python run.py install   # Install requirements")
        return
    
    mode = sys.argv[1].lower()
    
    if mode == "install":
        install_requirements()
    elif mode == "server":
        print("Starting Chess Game Server...")
        from server import main as server_main
        asyncio.run(server_main())
    elif mode == "client":
        print("Starting Chess Game Client...")
        from client import main as client_main
        asyncio.run(client_main())
    elif mode == "console":
        print("Starting Console Chess Game Client...")
        from client import main as console_client_main
        asyncio.run(console_client_main())
    else:
        print(f"Unknown mode: {mode}")
        print("Use 'server', 'client', 'console', or 'install'")

if __name__ == "__main__":
    main()
