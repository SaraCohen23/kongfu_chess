#!/usr/bin/env python3
"""
Quick test to check if the graphics client can initialize
"""

import sys
import os

def test_client_initialization():
    """Test if the client can be initialized properly"""
    print("Testing client initialization...")
    
    try:
        # Add the KFC_Py directory to path
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'KFC_Py'))
        
        # Test imports
        from simple_client import SimpleChessClient
        print("✓ SimpleChessClient import successful")
        
        # Test client creation (without connecting)
        client = SimpleChessClient()
        print("✓ Client created successfully")
        
        # Check if game was initialized
        if client.game:
            print("✓ Game display initialized")
            print(f"  - Board size: {client.game.board.H_cells}x{client.game.board.W_cells}")
            print(f"  - Number of pieces: {len(client.game.pieces)}")
        else:
            print("✗ Game display not initialized")
            return False
            
        print("✓ All tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    print("Chess Game Client - Initialization Test")
    print("=" * 50)
    
    success = test_client_initialization()
    
    print("=" * 50)
    if success:
        print("✓ Client is ready to run!")
        print("\nTo test the full system:")
        print("1. Terminal 1: python KFC_Py/run.py server")
        print("2. Terminal 2: python KFC_Py/run.py client")
        print("3. Terminal 3: python KFC_Py/run.py client")
    else:
        print("✗ Client initialization failed.")
        print("Make sure all dependencies are installed:")
        print("pip install -r requirements.txt")

if __name__ == "__main__":
    main()
