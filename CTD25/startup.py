#!/usr/bin/env python3
"""
Simple startup script that handles common issues
"""

import os
import sys
import time
import subprocess

def kill_existing_processes():
    """Kill any existing Python processes that might be using the port"""
    try:
        # On Windows, find and kill processes using port 8765
        result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        
        for line in lines:
            if ':8765' in line and 'LISTENING' in line:
                parts = line.split()
                if len(parts) > 4:
                    pid = parts[-1]
                    print(f"Found process {pid} using port 8765, attempting to kill...")
                    try:
                        subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True)
                        print(f"Killed process {pid}")
                    except:
                        print(f"Could not kill process {pid}")
        
        time.sleep(1)  # Give time for cleanup
        
    except Exception as e:
        print(f"Error checking/killing processes: {e}")

def main():
    print("Chess Game Startup Helper")
    print("=" * 30)
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python startup.py server")
        print("  python startup.py client")
        return
    
    mode = sys.argv[1].lower()
    
    # Change to project directory
    project_dir = r"C:\Users\1\Desktop\CTD25_Solutions"
    os.chdir(project_dir)
    print(f"Working directory: {os.getcwd()}")
    
    if mode == "server":
        print(" Cleaning up any existing server processes...")
        kill_existing_processes()
        
        print("  Starting server...")
        subprocess.run([sys.executable, "launch.py", "server"])
        
    elif mode == "client":
        print(" Starting client...")
        subprocess.run([sys.executable, "launch.py", "client"])
        
    else:
        print(f"Unknown mode: {mode}")

if __name__ == "__main__":
    main()
