import queue, threading, time, math, logging
import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional, Set
from collections import defaultdict

from Board import Board
from Command import Command
from Piece import Piece
from events import EventManager, Event, EventType, MoveTracker, ScoreTracker
from SoundManager import SoundManager

from KeyboardInput import KeyboardProcessor, KeyboardProducer

# set up a module-level logger – real apps can configure handlers/levels
logger = logging.getLogger(__name__)


class InvalidBoard(Exception): ...


class Game:
    def __init__(self, pieces: List[Piece], board: Board, pieces_root=None, img_factory=None):
        if not self._validate(pieces):
            raise InvalidBoard("missing kings")
        self.pieces = pieces
        self.board = board
        self.pieces_root = pieces_root  # Store pieces root path for promotions
        self.img_factory = img_factory  # Store image factory for loading queen graphics
        self.START_NS = time.monotonic_ns()
        self._time_factor = 1  # for tests
        
        # Game control variables
        self.should_exit = False  # Exit when ESC is pressed
        
        # Track promoted pawns to prevent double promotion
        self.promoted_pawns = set()  # Set of original pawn IDs that were promoted
        self.promoted_queens = set()  # Set of queen IDs that were created from promoted pawns
        self.user_input_queue = queue.Queue()  # thread-safe

        # Event system setup
        self.event_manager = EventManager()
        self.move_tracker = MoveTracker(self.event_manager)
        self.score_tracker = ScoreTracker(self.event_manager)
        
        # Sound system setup
        self.sound_manager = SoundManager()
        
        # For displaying temporary messages on screen
        self.temp_messages = []  # List of (message, end_time) tuples
        
        # Track previous positions for capture moves
        self.piece_previous_positions = {}  # piece_id -> (row, col)

        # Subscribe to capture events for temporary messages
        self.event_manager.subscribe(EventType.PIECE_CAPTURED, self.on_piece_captured_display)
        
        # Subscribe to events for sound effects
        self.event_manager.subscribe(EventType.PIECE_MOVED, self.on_piece_moved_sound)
        self.event_manager.subscribe(EventType.PIECE_CAPTURED, self.on_piece_captured_sound)

        # lookup tables ---------------------------------------------------
        self.pos: Dict[Tuple[int, int], List[Piece]] = defaultdict(list)
        self.piece_by_id: Dict[str, Piece] = {p.id: p for p in pieces}

        self.selected_id_1: Optional[str] = None
        self.selected_id_2: Optional[str] = None
        self.last_cursor2: Tuple[int, int] | None = None
        self.last_cursor1: Tuple[int, int] | None = None
        
        # Track selected pieces for visual indication
        self.selected_piece_1: Optional[str] = None  # Player 1's selected piece
        self.selected_piece_2: Optional[str] = None  # Player 2's selected piece
        
        # Control cursor display - can be disabled by clients
        self.show_cursors: bool = True  # Allow clients to disable cursor drawing

        # keyboard helpers ---------------------------------------------------
        self.keyboard_processor: Optional[KeyboardProcessor] = None
        self.keyboard_producer: Optional[KeyboardProducer] = None

    def game_time_ms(self) -> int:
        return self._time_factor * (time.monotonic_ns() - self.START_NS) // 1_000_000
    
    def add_temp_message(self, message: str, duration_ms: int = 3000):
        """Add a temporary message to display on screen."""
        end_time = self.game_time_ms() + duration_ms
        self.temp_messages.append((message, end_time))
    
    def on_piece_captured_display(self, event: Event):
        """Handle piece capture events for display."""
        data = event.data
        captured_piece_id = data.get('piece_type', '')
        captured_by = data.get('captured_by', '')
        
        # Create a nice message - English only
        piece_names = {
            'P': 'Pawn', 'N': 'Knight', 'B': 'Bishop', 
            'R': 'Rook', 'Q': 'Queen', 'K': 'King'
        }
        
        if len(captured_piece_id) >= 2:
            piece_type = captured_piece_id[0]
            piece_color = 'White' if captured_piece_id[1] == 'W' else 'Black'
            piece_name = piece_names.get(piece_type, 'Piece')
            
            message = f"{piece_color} {piece_name} captured!"
            self.add_temp_message(message, 2500)  # Show for 2.5 seconds

    def on_piece_moved_sound(self, event: Event):
        """Handle piece move events for sound effects."""
        self.sound_manager.play_move()
    
    def on_piece_captured_sound(self, event: Event):
        """Handle piece capture events for sound effects."""
        self.sound_manager.play_eat()

    def clone_board(self) -> Board:
        return self.board.clone()

    def start_user_input_thread(self):

        # player 1 key mapping (arrow keys and enter)
        p1_map = {
            "up": "up", "down": "down", "left": "left", "right": "right",
            "enter": "select", "+": "jump", "esc": "exit"
        }
        # player 2 key mapping (WASD keys and additional keys for both English and Hebrew layouts)
        p2_map = {
            # English keys
            "w": "up", "s": "down", "a": "left", "d": "right",
            "f": "select", "g": "jump",
            # Hebrew keys (same physical keys on Hebrew layout)
            "ץ": "up",  
            "ד": "down",    
            "ש": "left", 
            "ג": "right", 
            "כ": "select",
            "ע": "jump",  
            "esc": "exit"  # ESC works for both players
        }

        # create two processors
        self.kp1 = KeyboardProcessor(self.board.H_cells,
                                     self.board.W_cells,
                                     keymap=p1_map)
        self.kp2 = KeyboardProcessor(self.board.H_cells,
                                     self.board.W_cells,
                                     keymap=p2_map)

        # Create keyboard producers with player numbers as the 4th argument
        self.kb_prod_1 = KeyboardProducer(self,
                                          self.user_input_queue,
                                          self.kp1,
                                          player=1)
        self.kb_prod_2 = KeyboardProducer(self,
                                          self.user_input_queue,
                                          self.kp2,
                                          player=2)

        self.kb_prod_1.start()
        self.kb_prod_2.start()

    def _update_cell2piece_map(self):
        self.pos.clear()
        for p in self.pieces:
            self.pos[p.current_cell()].append(p)

    def _run_game_loop(self, num_iterations=None, is_with_graphics=True):
        it_counter = 0
        while not self.should_exit:  # Changed from _is_win() to manual exit control
            now = self.game_time_ms()

            for p in self.pieces:
                p.update(now)

            # Ensure promoted queens maintain their graphics after state updates
            self._ensure_promoted_queens_graphics()

            self._update_cell2piece_map()

            while not self.user_input_queue.empty():
                cmd: Command = self.user_input_queue.get()
                self._process_input(cmd)

            if is_with_graphics:
                self._draw()
                self._show()

            # First resolve collisions (captures), then check for promotions
            self._resolve_collisions()
            
            # Check for pawn promotions AFTER collisions are resolved
            self._check_post_collision_promotions()
            
            # Check for win condition and display message but don't exit
            self._check_and_announce_win()

            # for testing
            if num_iterations is not None:
                it_counter += 1
                if num_iterations <= it_counter:
                    return

    def run(self, num_iterations=None, is_with_graphics=True):
        # Publish game started event
        self.event_manager.publish(Event(
            EventType.GAME_STARTED,
            {'game_time_ms': self.game_time_ms()}
        ))
        
        # Add welcome message
        self.add_temp_message("Welcome to Chess Kingdom! Let the battle begin!", 4000)
        
        self.start_user_input_thread()
        start_ms = self.START_NS
        for p in self.pieces:
            p.reset(start_ms)

        self._run_game_loop(num_iterations, is_with_graphics)

        # Publish game ended event
        white_score, black_score = self.score_tracker.get_scores()
        winner = self.score_tracker.get_leading_player()
        
        # Add game end message
        if winner != 'Tied':
            end_message = f"Game Over! {winner} Wins! ({white_score}-{black_score})"
            # Play victory sound
            self.sound_manager.play_victory()
        else:
            end_message = f"Game Over! It's a Tie! ({white_score}-{black_score})"
        self.add_temp_message(end_message, 8000)  # Show for 8 seconds
        
        self.event_manager.publish(Event(
            EventType.GAME_ENDED,
            {
                'game_time_ms': self.game_time_ms(),
                'final_scores': self.score_tracker.get_scores()
            }
        ))

        self._announce_win()
        if self.kb_prod_1:
            self.kb_prod_1.stop()
            self.kb_prod_2.stop()

    def _draw(self):
        self.curr_board = self.clone_board()
        
        # Draw pieces in layers for proper z-ordering
        knights = []
        other_pieces = []
        
        # Separate knights from other pieces
        for p in self.pieces:
            if p.id.startswith('N'):  # Knight pieces (NW, NB)
                knights.append(p)
            else:
                other_pieces.append(p)
        
        # Draw other pieces first
        for p in other_pieces:
            p.draw_on_board(self.curr_board, now_ms=self.game_time_ms())
        
        # Draw knights last (always on top)
        for p in knights:
            p.draw_on_board(self.curr_board, now_ms=self.game_time_ms())

        # Draw special visual indicators for promoted queens
        self._draw_promoted_queen_indicators()
        
        # Draw selection indicators for selected pieces
        self._draw_selection_indicators()

        # overlay both players' cursors with simple styling (only if enabled)
        if self.show_cursors and self.kp1 and self.kp2:
            for player, kp, last in (
                    (1, self.kp1, 'last_cursor1'),
                    (2, self.kp2, 'last_cursor2')
            ):
                r, c = kp.get_cursor()
                # Calculate cursor position
                y1 = r * self.board.cell_H_pix + self.board.board_offset_y
                x1 = c * self.board.cell_W_pix + self.board.board_offset_x
                y2 = y1 + self.board.cell_H_pix - 1
                x2 = x1 + self.board.cell_W_pix - 1
                
                # Simple color scheme - only black, white, blue
                black_color = (0, 0, 0)
                white_color = (255, 255, 255)
                blue_color = (255, 0, 0)  # Blue in BGR
                
                if player == 1:
                    # Player 1: White cursor with blue border
                    main_color = white_color
                    border_color = blue_color
                else:
                    # Player 2: Black cursor with blue border
                    main_color = black_color
                    border_color = blue_color
                
                # Draw simple cursor
                # Outer blue border
                cv2.rectangle(self.curr_board.img.img, 
                             (x1 - 2, y1 - 2), (x2 + 2, y2 + 2), 
                             border_color, 3)
                
                # Inner border
                cv2.rectangle(self.curr_board.img.img, 
                             (x1, y1), (x2, y2), 
                             main_color, 2)
                
                # only move cursor if it actually moved
                prev = getattr(self, last)
                if prev != (r, c):
                    logger.debug("Marker P%s moved to (%s, %s)", player, r, c)
                    setattr(self, last, (r, c))
        else:
            pass  # No updates needed
    
    def _draw_promoted_queen_indicators(self):
        """Draw indicators for promoted queens - disabled per user request."""
        # No visual indicators - user doesn't want golden borders or crowns
        pass
    
    def _draw_selection_indicators(self):
        """Draw blue transparent rectangles for selected pieces."""
        # Check if we have selected pieces
        for player_num in [1, 2]:
            selected_piece_id = getattr(self, f'selected_piece_{player_num}', None)
            if selected_piece_id and selected_piece_id in self.piece_by_id:
                piece = self.piece_by_id[selected_piece_id]
                r, c = piece.current_cell()
                
                # Calculate piece position
                y1 = r * self.board.cell_H_pix + self.board.board_offset_y
                x1 = c * self.board.cell_W_pix + self.board.board_offset_x
                y2 = y1 + self.board.cell_H_pix
                x2 = x1 + self.board.cell_W_pix
                
                # Create blue transparent overlay
                blue_color = (255, 100, 0)  # Blue in BGR with some transparency effect
                
                # Create overlay for transparency effect
                overlay = self.curr_board.img.img.copy()
                cv2.rectangle(overlay, (x1, y1), (x2, y2), blue_color, -1)
                
                # Apply transparency (alpha blending)
                alpha = 0.3  # 30% transparency
                cv2.addWeighted(overlay, alpha, self.curr_board.img.img, 1 - alpha, 0, self.curr_board.img.img)
                
                # Add border for better visibility
                cv2.rectangle(self.curr_board.img.img, (x1, y1), (x2, y2), blue_color, 3)
    
    def _draw_move_tables(self):
        """Draw clean move tables with black, white and turquoise colors."""
        # Get recent moves for both colors
        white_moves, black_moves = self.move_tracker.get_all_moves_by_color(10)
        
        # Calculate table positions based on actual board position
        board_width = self.board.W_cells * self.board.cell_W_pix
        board_height = self.board.H_cells * self.board.cell_H_pix
        
        # Use the actual board position from GameFactory (not calculated)
        screen_width = self.curr_board.img.img.shape[1]
        board_left = self.board.board_offset_x  # Use actual board position
        
        # Simple table dimensions
        table_width = 300
        table_spacing = 30
        row_height = 30
        
        # Left table (White moves) - aligned with board Y position
        left_table_x = board_left - table_width - table_spacing
        table_y_start = self.board.board_offset_y  # Same Y as board
        
        # Right table (Black moves) - aligned with board Y position
        right_table_x = board_left + board_width + table_spacing
        
        # Clean color scheme - only black, white, blue
        black_color = (0, 0, 0)
        white_color = (255, 255, 255)
        blue_color = (255, 0, 0)  # Blue in BGR format
        gray_color = (128, 128, 128)
        
        def draw_simple_table(x, y, moves, title, is_white_table=True):
            # Fixed table height - same as board height
            table_height = board_height
            max_visible_moves = (table_height - 70) // row_height  # Leave space for header
            
            # Take only the most recent moves that fit in the table
            displayed_moves = moves[-max_visible_moves:] if len(moves) > max_visible_moves else moves
            
            # Simple white background - starts at same Y as board
            cv2.rectangle(self.curr_board.img.img, 
                         (x, y), 
                         (x + table_width, y + table_height),
                         white_color, -1)
            
            # Black border - starts at same Y as board
            cv2.rectangle(self.curr_board.img.img, 
                         (x, y), 
                         (x + table_width, y + table_height),
                         black_color, 2)
            
            # Title in blue - positioned at top of table
            self.curr_board.img.put_text(title, x + 10, y + 20, 0.6, blue_color, 2)
            
            # Simple line under title
            cv2.line(self.curr_board.img.img, 
                     (x + 10, y + 35), 
                     (x + table_width - 10, y + 35), 
                     black_color, 1)
            
            # Column headers in black
            self.curr_board.img.put_text("Time", x + 10, y + 50, 0.5, black_color, 1)
            self.curr_board.img.put_text("Move", x + 100, y + 50, 0.5, black_color, 1)
            
            # Draw moves (only the ones that fit)
            for i, (time_str, move_str) in enumerate(displayed_moves):
                y_pos = y + 70 + (i * row_height)
                
                # Only draw if within table bounds
                if y_pos + row_height > y + table_height - 10:
                    break  # Stop if we exceed the table height
                
                # Alternating background - white and light gray
                if i % 2 == 1:
                    cv2.rectangle(self.curr_board.img.img, 
                                 (x + 5, y_pos - 10), 
                                 (x + table_width - 5, y_pos + 15),
                                 (240, 240, 240), -1)  # Light gray
                
                # Time in blue
                self.curr_board.img.put_text(time_str, x + 10, y_pos, 0.4, blue_color, 1)
                
                # Move in black
                self.curr_board.img.put_text(move_str, x + 100, y_pos, 0.4, black_color, 1)
            
            # Add scroll indicator if there are more moves than can be displayed
            if len(moves) > max_visible_moves:
                scroll_text = f"... ({len(moves) - max_visible_moves} more)"
                self.curr_board.img.put_text(scroll_text, x + 10, y + table_height - 25, 0.3, blue_color, 1)
        
        # Draw both tables
        if left_table_x > 0:
            draw_simple_table(left_table_x, table_y_start, white_moves, "WHITE MOVES", True)
        
        if right_table_x + table_width < screen_width:
            draw_simple_table(right_table_x, table_y_start, black_moves, "BLACK MOVES", False)

    def _draw_score_panel(self):
        """Draw simple score text - just blue text without frames."""
        # Get score data
        white_score, black_score = self.score_tracker.get_scores()
        
        # Center the text at the top (no logo anymore)
        screen_width = self.curr_board.img.img.shape[1]
        text_x = screen_width // 2 - 100  # Center the text
        text_y = 30  # Top of screen (no logo to avoid)
        
        # Blue color for the score text
        blue_color = (255, 0, 0)  # Blue in BGR format
        
        # Simple score text - just the numbers
        score_text = f"WHITE: {white_score}  -  BLACK: {black_score}"
        self.curr_board.img.put_text(score_text, text_x, text_y, 0.7, blue_color, 2)


    def _show(self):
        current_time = self.game_time_ms()
        
        # Draw move tables on both sides of the board
        self._draw_move_tables()
        
        # Create a styled score panel
        self._draw_score_panel()
        
        # Display temporary messages and remove expired ones
        self.temp_messages = [(msg, end_time) for msg, end_time in self.temp_messages if end_time > current_time]
        
        y_offset = 120  # Start below the other text
        for message, end_time in self.temp_messages:
            # Make message blink by changing color based on time
            time_left = end_time - current_time
            if time_left < 500:  # Last 0.5 seconds - make it blink
                color = (0, 0, 255) if (current_time // 100) % 2 else (255, 255, 255)  # Red/White blink
            else:
                color = (0, 255, 255)  # Cyan for normal display
            
            # Calculate center position
            screen_width = self.curr_board.img.img.shape[1]
            text_width = len(message) * 12  # Rough estimate
            center_x = (screen_width - text_width) // 2
            
            # Add a semi-transparent background for better readability
            # Draw a rectangle behind the text (approximate size)
            self.curr_board.img.img = cv2.rectangle(
                self.curr_board.img.img, 
                (center_x - 5, y_offset - 20), 
                (center_x + text_width + 5, y_offset + 5), 
                (0, 0, 0, 128),  # Semi-transparent black
                -1  # Filled rectangle
            )
                
            self.curr_board.img.put_text(
                message,
                x=center_x,
                y=y_offset,
                font_size=0.7,
                color=color,
                thickness=2
            )
            y_offset += 35  # Move down for next message
        
        self.curr_board.show()

    def _side_of(self, piece_id: str) -> str:
        return piece_id[1]

    def _process_input(self, cmd: Command):
        # Handle ESC key to exit the game
        if cmd.type == "exit":
            self.should_exit = True
            return
        
        mover = self.piece_by_id.get(cmd.piece_id)
        if not mover:
            logger.debug("Unknown piece id %s", cmd.piece_id)
            return

        # Store old position before move
        old_position = mover.current_cell()
        
        # Store old state to detect successful transitions
        old_state = mover.state
        
        # Store previous position for potential capture moves
        self.piece_previous_positions[cmd.piece_id] = old_position
        
        # Check if this move will result in a capture by checking the move pattern
        is_potential_capture = False
        if cmd.type in ['move', 'capture', 'jump'] and len(cmd.params) >= 2:
            # Check if the move delta corresponds to a capture move pattern
            src_pos = cmd.params[0]
            dst_pos = cmd.params[1]
            dr, dc = dst_pos[0] - src_pos[0], dst_pos[1] - src_pos[1]
            
            # Check the piece's moves configuration to see if this delta is tagged as "capture"
            if hasattr(mover.state, 'moves') and mover.state.moves:
                move_tag = mover.state.moves.moves.get((dr, dc), "")
                if move_tag == "capture":
                    is_potential_capture = True
        
        # Execute the move
        mover.on_command(cmd, self.pos)
        
        # Get new position and state after move command processing
        new_position = mover.current_cell()
        new_state = mover.state
        
        
        # Only publish PIECE_MOVED event if:
        # 1. The move was successful
        # 2. It's NOT a potential capture move (captures will be handled by collision resolution)
        is_move_command = cmd.type in ['move', 'capture', 'jump'] and len(cmd.params) >= 2
        position_changed = old_position != new_position
        state_transitioned = old_state != new_state
        
        if is_move_command and (position_changed or (state_transitioned and "move" in str(new_state).lower())):
            if not is_potential_capture:  # Only publish for non-capture moves
                target_position = cmd.params[1] if len(cmd.params) >= 2 else new_position
                
                # Determine which player moved (based on piece color)
                player_color = 'white' if cmd.piece_id[1] == 'W' else 'black'
                
                self.event_manager.publish(Event(
                    EventType.PIECE_MOVED,
                    {
                        'piece': cmd.piece_id,
                        'from': old_position,
                        'to': target_position,
                        'command_type': cmd.type,
                        'game_time_ms': self.game_time_ms()
                    }
                ))
                
                # Publish turn changed event
                self.event_manager.publish(Event(
                    EventType.TURN_CHANGED,
                    {
                        'current_player': player_color,
                        'move_piece': cmd.piece_id,
                        'game_time_ms': self.game_time_ms()
                    }
                ))
            else:
                # Non-move command completed
                pass
        elif position_changed:
            # Handle other types of position changes (non-move commands)
            player_color = 'white' if cmd.piece_id[1] == 'W' else 'black'
            
            self.event_manager.publish(Event(
                EventType.PIECE_MOVED,
                {
                    'piece': cmd.piece_id,
                    'from': old_position,
                    'to': new_position,
                    'command_type': cmd.type,
                    'game_time_ms': self.game_time_ms()
                }
            ))
        else:
            # No position change
            pass
        
        # Check for pawn promotion after move commands only
        if mover.id.startswith('P') and cmd.type == 'move' and len(cmd.params) >= 2:
            # Use the piece's actual current position, not the target from command
            actual_position = mover.current_cell()
            self._check_pawn_promotion(mover, actual_position)

    def _check_pawn_promotion(self, piece: Piece, position: Tuple[int, int]):
        """Check if a pawn has reached the end of the board and promote it to queen."""
        # Only check pawns (not already promoted pieces)
        if not piece.id.startswith('P'):
            return
            
        # Check if this pawn was already promoted
        if piece.id in self.promoted_pawns:
            return
            
        row, col = position
        piece_color = piece.id[1]  # 'W' or 'B'
        
        # White pawns promote when reaching row 0 (top of board)
        # Black pawns promote when reaching row 7 (bottom of board)
        should_promote = False
        if piece_color == 'W' and row == 0:
            should_promote = True
        elif piece_color == 'B' and row == 7:
            should_promote = True
            
        if should_promote:
            # Check if there are enemy pieces that could immediately threaten this position
            self._update_cell2piece_map()
            enemy_pieces_at_location = [p for p in self.pos.get(position, []) 
                                       if p.id != piece.id and self._side_of(p.id) != piece_color]
            
            # Mark as promoted BEFORE the actual promotion
            self.promoted_pawns.add(piece.id)
            self._promote_pawn_to_queen(piece)
    
    def _promote_pawn_to_queen(self, pawn: Piece):
        """Convert a pawn to a queen by changing its ID and loading queen moves."""
        old_id = pawn.id
        
        # Check if already promoted (safety check)
        if not old_id.startswith('P'):
            return
            
        piece_color = pawn.id[1]  # 'W' or 'B'
        
        # Find a unique queen ID (Q + color + number)
        queen_base = f'Q{piece_color}'
        queen_number = 1
        while f'{queen_base}_{queen_number}' in self.piece_by_id:
            queen_number += 1
        new_id = f'{queen_base}_{queen_number}'
        
        # Update the piece ID
        old_position = pawn.current_cell()
        del self.piece_by_id[old_id]
        pawn.id = new_id
        self.piece_by_id[new_id] = pawn
        
        # Track this queen as a promoted piece
        self.promoted_queens.add(new_id)
        
        # No special protection needed - queen promotion should work like normal piece interactions
        
        # Load queen moves and graphics from the pieces folder
        try:
            queen_folder = f'Q{piece_color}'
            
            # Load complete queen state machine using PieceFactory
            from PieceFactory import PieceFactory
            from GraphicsFactory import GraphicsFactory
            
            if self.img_factory is not None:
                gfx_factory = GraphicsFactory(self.img_factory)
                temp_pf = PieceFactory(self.board, self.pieces_root, graphics_factory=gfx_factory)
                
                # Build the complete queen state machine
                queen_piece_dir = self.pieces_root / queen_folder
                queen_states = temp_pf._build_state_machine(queen_piece_dir, queen_folder)
                
                if queen_states:
                    # Store the current position before changing state
                    old_position = pawn.current_cell()
                    
                    # Replace the pawn's state machine with the queen's
                    pawn.state = queen_states
                    
                    # Load queen graphics AFTER state machine is loaded to ensure proper graphics
                    queen_sprites_path = self.pieces_root / queen_folder / "states" / "idle" / "sprites"
                    
                    # Load queen graphics with same cell size as current piece
                    cell_size = (64, 64)  # Standard cell size
                    if hasattr(pawn.state, 'graphics') and hasattr(pawn.state.graphics, '_cell_size'):
                        cell_size = pawn.state.graphics._cell_size
                        
                    queen_graphics = gfx_factory.load(
                        queen_sprites_path,
                        cfg={"is_loop": True, "frames_per_sec": 6.0},
                        cell_size=cell_size
                    )
                    
                    # Update the piece's graphics to queen graphics
                    pawn.state.graphics = queen_graphics
                    
                    # Mark the piece as having queen graphics to prevent overwrites
                    if hasattr(pawn.state, '__dict__'):
                        pawn.state._has_queen_graphics = True
                    
                    # Apply graphics to ALL states in the state machine
                    if hasattr(pawn.state, 'states') and pawn.state.states:
                        for state_name, state_obj in pawn.state.states.items():
                            if hasattr(state_obj, 'graphics'):
                                state_sprites_path = self.pieces_root / queen_folder / "states" / state_name / "sprites"
                                try:
                                    state_graphics = gfx_factory.load(
                                        state_sprites_path,
                                        cfg={"is_loop": True, "frames_per_sec": 6.0},
                                        cell_size=cell_size
                                    )
                                    state_obj.graphics = state_graphics
                                    if hasattr(state_obj, '__dict__'):
                                        state_obj._has_queen_graphics = True
                                except Exception:
                                    pass  # Silent fail
                    
                    # Reset to idle state at current position
                    from Command import Command
                    current_time = self.game_time_ms()
                    reset_cmd = Command(current_time, new_id, "idle", [old_position])
                    pawn.state.reset(reset_cmd)
                else:
                    pass  # Could not load queen state machine
            else:
                pass  # No img_factory available
                
        except Exception as e:
            logger.warning(f"Could not load queen moves for promoted pawn: {e}")
            # Fallback: try to load just the graphics without state machine
            try:
                if self.img_factory is not None:
                    from GraphicsFactory import GraphicsFactory
                    gfx_factory = GraphicsFactory(self.img_factory)
                    queen_sprites_path = self.pieces_root / f'Q{piece_color}' / "states" / "idle" / "sprites"
                    
                    queen_graphics = gfx_factory.load(
                        queen_sprites_path,
                        cfg={"is_loop": True, "frames_per_sec": 6.0},
                        cell_size=(64, 64)
                    )
                    
                    pawn.state.graphics = queen_graphics
                    if hasattr(pawn.state, '__dict__'):
                        pawn.state._has_queen_graphics = True
            except Exception as fallback_e:
                pass  # Silent fallback fail
        
        # Update position to new position
        new_position = pawn.current_cell()
        
        # Add simple promotion message
        color_name = 'White' if piece_color == 'W' else 'Black'
        message = f"{color_name} Pawn promoted to Queen!"
        self.add_temp_message(message, 3000)  # Show for 3 seconds
        
        # Play victory sound for promotion
        self.sound_manager.play_victory()
        
        # Log the promotion - simple version
        # Log the promotion
        logger.info(f"Pawn {old_id} promoted to Queen {new_id} at position {new_position}")
        
        # Don't automatically move the queen - let the player decide where to move
        # self._try_move_queen_to_safety(pawn, new_position)  # Disabled for better UX
        
        # Publish promotion event
        self.event_manager.publish(Event(
            EventType.PIECE_MOVED,  # Using existing event type
            {
                'piece': new_id,
                'from': new_position,
                'to': new_position,  # Same position but new piece type
                'command_type': 'promotion',
                'game_time_ms': self.game_time_ms(),
                'promotion': True,
                'old_piece_id': old_id
            }
        ))

    def _try_move_queen_to_safety(self, queen: Piece, current_pos: Tuple[int, int]):
        """Try to move the newly promoted queen to a safer square."""
        try:
            # Get possible queen moves
            if hasattr(queen.state, 'moves') and queen.state.moves:
                # Get all possible moves for the queen
                possible_moves = []
                for dr, dc in queen.state.moves.moves.keys():
                    new_row, new_col = current_pos[0] + dr, current_pos[1] + dc
                    # Check if the move is within board bounds
                    if (0 <= new_row < self.board.H_cells and 
                        0 <= new_col < self.board.W_cells):
                        possible_moves.append((new_row, new_col))
                
                # Find a safe square (not occupied by enemy pieces)
                safe_squares = []
                self._update_cell2piece_map()
                
                for target_pos in possible_moves:
                    enemy_pieces_at_target = [
                        p for p in self.pos.get(target_pos, [])
                        if self._side_of(p.id) != self._side_of(queen.id)
                    ]
                    if not enemy_pieces_at_target:
                        safe_squares.append(target_pos)
                
                if safe_squares:
                    # Move to the first safe square
                    target_pos = safe_squares[0]
                    
                    from Command import Command
                    current_time = self.game_time_ms()
                    safety_cmd = Command(current_time, queen.id, "move", [current_pos, target_pos])
                    queen.on_command(safety_cmd, self.pos)
                else:
                    pass  # No safe squares found
            else:
                pass  # No moves available
        except Exception as e:
            pass  # Failed to move to safety

    def _ensure_promoted_queens_graphics(self):
        """Ensure all promoted queens maintain their queen graphics after state transitions."""
        if not hasattr(self, 'promoted_queens'):
            return
        
        # Check all promoted queens and restore graphics if needed - less frequent checks
        for piece in self.pieces:
            if piece.id in self.promoted_queens:
                # Check less frequently - every 2 seconds instead of every 500ms
                current_frame = self.game_time_ms() // 100  # Check every 100ms
                if current_frame % 20 == 0:  # Check every 2000ms (2 seconds)
                    self._restore_queen_graphics(piece)
                
                # Also check if graphics flag is missing
                if (not hasattr(piece.state, '_has_queen_graphics') or 
                    not piece.state._has_queen_graphics):
                    self._restore_queen_graphics(piece)
                    # Remove debug message to keep it clean
    
    def _restore_queen_graphics(self, piece):
        """Restore queen graphics for a promoted pawn."""
        try:
            piece_color = piece.id[1]  # W or B
            queen_folder = f"Q{piece_color}"
            
            # Get current state name to load the correct graphics
            current_state_name = "idle"
            if hasattr(piece.state, 'current_state_name'):
                current_state_name = piece.state.current_state_name
            elif hasattr(piece.state, '_current_state') and piece.state._current_state:
                current_state_name = piece.state._current_state
            
            queen_sprites_path = self.pieces_root / queen_folder / "states" / current_state_name / "sprites"
            
            # Fallback to idle if the current state sprites don't exist
            if not queen_sprites_path.exists():
                queen_sprites_path = self.pieces_root / queen_folder / "states" / "idle" / "sprites"
            
            from GraphicsFactory import GraphicsFactory
            
            if self.img_factory is not None:
                gfx_factory = GraphicsFactory(self.img_factory)
                
                cell_size = (64, 64)
                if hasattr(piece.state, 'graphics') and hasattr(piece.state.graphics, '_cell_size'):
                    cell_size = piece.state.graphics._cell_size
                
                queen_graphics = gfx_factory.load(
                    queen_sprites_path,
                    cfg={"is_loop": True, "frames_per_sec": 6.0},
                    cell_size=cell_size
                )
                
                # Force update the graphics
                piece.state.graphics = queen_graphics
                piece.state._has_queen_graphics = True
                
                # Also update any sub-states if they exist
                if hasattr(piece.state, 'states') and piece.state.states:
                    for state_name, state_obj in piece.state.states.items():
                        if hasattr(state_obj, 'graphics'):
                            try:
                                state_sprites_path = self.pieces_root / queen_folder / "states" / state_name / "sprites"
                                if state_sprites_path.exists():
                                    state_graphics = gfx_factory.load(
                                        state_sprites_path,
                                        cfg={"is_loop": True, "frames_per_sec": 6.0},
                                        cell_size=cell_size
                                    )
                                    state_obj.graphics = state_graphics
                                    if hasattr(state_obj, '__dict__'):
                                        state_obj._has_queen_graphics = True
                            except Exception:
                                pass  # Silent fail
                
                # Graphics restored successfully
                
        except Exception as e:
            logger.warning(f"Failed to restore graphics for {piece.id}: {e}")
            # Emergency fallback - try to load any queen graphics
            try:
                piece_color = piece.id[1]
                fallback_path = self.pieces_root / f"Q{piece_color}" / "states" / "idle" / "sprites"
                if fallback_path.exists() and self.img_factory is not None:
                    from GraphicsFactory import GraphicsFactory
                    gfx_factory = GraphicsFactory(self.img_factory)
                    fallback_graphics = gfx_factory.load(
                        fallback_path,
                        cfg={"is_loop": True, "frames_per_sec": 6.0},
                        cell_size=(64, 64)
                    )
                    piece.state.graphics = fallback_graphics
                    piece.state._has_queen_graphics = True
            except Exception as fallback_e:
                logger.warning(f"Emergency fallback failed for {piece.id}: {fallback_e}")

    def _check_post_collision_promotions(self):
        """Check for pawn promotions after collisions are resolved."""
        for p in self.pieces:
            if p.id.startswith('P') and p.id not in self.promoted_pawns:
                current_pos = p.current_cell()
                piece_color = p.id[1]
                # Check if pawn reached promotion row and survived any collisions
                if (piece_color == 'W' and current_pos[0] == 0) or (piece_color == 'B' and current_pos[0] == 7):
                    self._check_pawn_promotion(p, current_pos)

    def _resolve_collisions(self):
        self._update_cell2piece_map()
        occupied = self.pos

        for cell, plist in occupied.items():
            if len(plist) < 2:
                continue

            # Find pieces that can attack (can_capture)
            attacking_pieces = []
            for p in plist:
                if p.state.can_capture():
                    # Special case for Knights: they can only capture at their destination
                    from Physics import KnightJumpPhysics
                    if isinstance(p.state.physics, KnightJumpPhysics):
                        if hasattr(p.state.physics, 'can_capture_at_current_position'):
                            if p.state.physics.can_capture_at_current_position():
                                attacking_pieces.append(p)
                            else:
                                # Knight is passing through - don't add to attacking pieces
                                continue
                        else:
                            attacking_pieces.append(p)  # Fallback for safety
                    else:
                        attacking_pieces.append(p)
            
            if not attacking_pieces:
                # No attacking pieces - but check for Knights passing through
                non_knight_pieces = []
                knights_passing_through = []
                
                for p in plist:
                    from Physics import KnightJumpPhysics
                    if isinstance(p.state.physics, KnightJumpPhysics):
                        if hasattr(p.state.physics, 'can_capture_at_current_position'):
                            if not p.state.physics.can_capture_at_current_position():
                                knights_passing_through.append(p)
                                continue
                    non_knight_pieces.append(p)
                
                if non_knight_pieces:
                    # Keep the most recent non-passing-knight piece (most recent arrival wins)
                    winner = max(non_knight_pieces, key=lambda p: p.state.physics.get_start_ms())
                elif knights_passing_through:
                    # Only knights passing through - no winner, no captures
                    continue
                else:
                    # Keep the most recent piece (fallback)
                    winner = max(plist, key=lambda p: p.state.physics.get_start_ms())
            else:
                # The attacker that moved most recently wins
                winner = max(attacking_pieces, key=lambda p: p.state.physics.get_start_ms())

            # Remove pieces that can be captured and are from opposite side
            captured_pieces = []
            for p in plist:
                if p is winner:
                    continue
                
                # Special case for Knights: they can only be captured at their destination
                from Physics import KnightJumpPhysics
                if isinstance(p.state.physics, KnightJumpPhysics):
                    if hasattr(p.state.physics, 'can_capture_at_current_position'):
                        if not p.state.physics.can_capture_at_current_position():
                            continue  # Knight is passing through - cannot be captured
                        else:
                            # Knight can capture at this position
                            pass
                
                # Only capture pieces from opposite side that can be captured
                if (p.state.can_be_captured() and 
                    self._side_of(p.id) != self._side_of(winner.id)):
                    captured_pieces.append(p)
                    self.pieces.remove(p)
                else:
                    # Piece cannot be captured or is on same side
                    pass
            
            # Publish capture events
            for captured_piece in captured_pieces:
                # Get the previous position of the attacking piece
                attacker_prev_pos = self.piece_previous_positions.get(winner.id, (0, 0))
                
                self.event_manager.publish(Event(
                    EventType.PIECE_CAPTURED,
                    {
                        'piece_type': captured_piece.id,
                        'captured_by': winner.id,
                        'from_position': attacker_prev_pos,
                        'position': cell,
                        'game_time_ms': self.game_time_ms()
                    }
                ))

    def _validate(self, pieces):
        """Ensure both kings present and no two pieces share a cell."""
        has_white_king = has_black_king = False
        seen_cells: dict[tuple[int, int], str] = {}
        for p in pieces:
            cell = p.current_cell()
            if cell in seen_cells:
                # Allow overlap only if piece is from opposite side
                if seen_cells[cell] == p.id[1]:
                    return False
            else:
                seen_cells[cell] = p.id[1]
            if p.id.startswith("KW"):
                has_white_king = True
            elif p.id.startswith("KB"):
                has_black_king = True
        return has_white_king and has_black_king

    def _is_win(self) -> bool:
        kings = [p for p in self.pieces if p.id.startswith(('KW', 'KB'))]
        return len(kings) < 2

    def _check_and_announce_win(self):
        """Check for win condition and announce but don't exit the game."""
        if self._is_win():
            # Only announce once - check if we already announced
            if not hasattr(self, '_win_announced'):
                # Check which side won
                winner_text = 'Black wins!' if any(p.id.startswith('KB') for p in self.pieces) else 'White wins!'
                
                # Show permanent win message - only once
                self.add_temp_message(f"Victory! {winner_text} Press ESC to exit", 10000)  # Show for 10 seconds
                
                logger.info(winner_text)
                self._win_announced = True
                
                # Publish game ended event
                white_score, black_score = self.score_tracker.get_scores()
                
                self.event_manager.publish(Event(
                    EventType.GAME_ENDED,
                    {
                        'game_time_ms': self.game_time_ms(),
                        'final_scores': self.score_tracker.get_scores(),
                        'winner': winner_text
                    }
                ))
                
                # Play victory sound
                self.sound_manager.play_victory()

    def _announce_win(self):
        text = 'Black wins!' if any(p.id.startswith('KB') for p in self.pieces) else 'White wins!'
        logger.info(text)
