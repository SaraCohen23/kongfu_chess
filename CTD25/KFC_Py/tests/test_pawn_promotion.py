"""
Test for Pawn Promotion feature - when a pawn reaches the end of the board, it should promote to a queen.
"""

import pathlib
import time
from GameFactory import create_game
from GraphicsFactory import MockImgFactory
from Command import Command

PIECES_ROOT = pathlib.Path(__file__).parent.parent.parent / "pieces"


def test_white_pawn_promotion():
    """Test white pawn promotion when reaching row 0 (top of board)."""
    game = create_game(PIECES_ROOT, MockImgFactory())
    game._update_cell2piece_map()

    # Find a white pawn on the board 
    white_pawn = None
    for piece in game.pieces:
        if piece.id.startswith('PW'):
            white_pawn = piece
            break
    
    assert white_pawn is not None, "No white pawn found"
    original_id = white_pawn.id
    
    # Call promotion check directly with row 0 (promotion row for white pawns)
    game._check_pawn_promotion(white_pawn, (0, 3))
    game._update_cell2piece_map()
    
    # Check that pawn was promoted
    # The original pawn should no longer exist
    assert original_id not in game.piece_by_id, "Original pawn should be removed after promotion"
    
    # The piece itself should now be a queen
    assert white_pawn.id.startswith('QW'), f"Promoted piece should be a white queen, got {white_pawn.id}"
    
    print(f"✅ White pawn {original_id} promoted to queen {white_pawn.id}")


def test_black_pawn_promotion():
    """Test black pawn promotion when reaching row 7 (bottom of board)."""
    game = create_game(PIECES_ROOT, MockImgFactory())
    game._update_cell2piece_map()

    # Find a black pawn on the board
    black_pawn = None
    for piece in game.pieces:
        if piece.id.startswith('PB'):
            black_pawn = piece
            break
    
    assert black_pawn is not None, "No black pawn found"
    original_id = black_pawn.id
    
    # Call promotion check directly with row 7 (promotion row for black pawns)
    game._check_pawn_promotion(black_pawn, (7, 3))
    game._update_cell2piece_map()
    
    # Check that pawn was promoted
    # The original pawn should no longer exist
    assert original_id not in game.piece_by_id, "Original pawn should be removed after promotion"
    
    # The piece itself should now be a queen
    assert black_pawn.id.startswith('QB'), f"Promoted piece should be a black queen, got {black_pawn.id}"
    
    print(f"✅ Black pawn {original_id} promoted to queen {black_pawn.id}")


def test_no_promotion_middle_board():
    """Test that pawns do not promote when moving to middle rows."""
    game = create_game(PIECES_ROOT, MockImgFactory())
    game._time_factor = 1_000_000_000  # Speed up for testing
    game._update_cell2piece_map()

    # Find a white pawn
    white_pawn = None
    for piece in game.pieces:
        if piece.id.startswith('PW'):
            white_pawn = piece
            break
    
    assert white_pawn is not None, "No white pawn found"
    original_id = white_pawn.id
    
    # Move pawn to middle of board (row 4)
    start_pos = white_pawn.current_cell()
    target_pos = (4, start_pos[1])
    
    # Move manually to avoid movement validation
    white_pawn.state.physics.cell = target_pos
    
    # Check promotion
    game._check_pawn_promotion(white_pawn, target_pos)
    
    # Pawn should still exist with same ID
    assert original_id in game.piece_by_id, "Pawn should not be promoted in middle of board"
    assert white_pawn.id == original_id, "Pawn ID should not change"
    
    print(f"✅ Pawn {original_id} correctly did not promote at row 4")


if __name__ == '__main__':
    test_white_pawn_promotion()
    test_black_pawn_promotion() 
    test_no_promotion_middle_board()
    print("🎉 All pawn promotion tests passed!")
