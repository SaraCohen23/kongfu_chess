Chess Game – Client/Server Architecture
The game has been adapted to work with a client-server architecture, allowing two players to play from different computers or terminals.
Solution Structure
New Files:


server.py – main server that manages the game


client.py – client that connects to the server


server_game.py – game logic on the server side (no graphics)


run.py – quick start script


requirements.txt – required packages


Dependencies:


websockets – client-server communication


keyboard – keyboard input handling


opencv-python + numpy – for existing graphics



How to Run
1. Install dependencies:
pip install -r requirements.txt

Or:
python run.py install

2. Start the server:
python run.py server

Or directly:
python server.py

The server will run on localhost:8765 and wait for two clients.
3. Start clients:
Terminal 2 (Player 1 – with graphics):
python run.py client

Terminal 3 (Player 2 – with graphics):
python run.py client

Alternatively – console-only client (no graphics):
python run.py console


How It Works
Server:


Waits for two player connections


Initializes a new game when both players are connected


Receives commands from clients and validates them


Sends updates to both clients with the current board state


Client:


Connects to the server via WebSocket


Displays the full graphical board (like the original game)


Receives user input (arrows + Enter)


Sends commands to the server and updates the display


Client Types:


python run.py client – full graphics client


python run.py console – simple console client (text only)



Controls
Player 1 (White):


Arrows – navigate the board


Enter – select piece / make move


ESC – exit


Player 2 (Black):


WASD – navigate the board


F – select piece / make move


ESC – exit



Display
Graphical client (python run.py client):


Full graphical chess board (like the original game)


Realistic chess pieces with animations


Nice background and professional design


Green highlight for selection


Yellow highlight for selected piece


Console client (python run.py console):


Simple text-based chess board


Current cursor position shown as []


Selected piece shown as *piece*


Displays player turn and game status



Changes from Original Code


Logic separation: Game logic moved to ServerGame without graphics


Network communication: WebSocket communication added between client and server


Simplified interface: Console client displays simple board instead of full graphics


Central game state: Server maintains the real game state



Possible Extensions


 Add full graphics for the client


 Advanced move validation


 Detect check/checkmate


 Save/load games


 Support more than two players (multiple games)


 Web-based interface instead of console



Common Issues


Server does not start – check if port 8765 is free


Client cannot connect – ensure the server is running


Input issues – ensure the keyboard package is installed with proper permissions



Message Structure
Client → Server:
{
  "type": "move",
  "piece_id": "PW1",
  "from": [6, 0],
  "to": [4, 0]
}

Server → Client:
{
  "type": "game_state",
  "state": {
    "pieces": [...],
    "current_turn": "white",
    "game_status": "playing"
  }
}

