"""
Test for Pawn Promotion Graphics - verify that promoted pawns display as queens.
"""

import pathlib
from GameFactory import create_game
from GraphicsFactory import ImgFactory


PIECES_ROOT = pathlib.Path(__file__).parent.parent.parent / "pieces"


def test_pawn_promotion_graphics_real_game():
    """Test pawn promotion graphics in a real game with actual images."""
    # Create game with REAL image factory (not mock)
    game = create_game(PIECES_ROOT, ImgFactory())
    game._update_cell2piece_map()

    # Find a white pawn
    white_pawn = None
    for piece in game.pieces:
        if piece.id.startswith('PW'):
            white_pawn = piece
            break
    
    assert white_pawn is not None, "No white pawn found"
    original_id = white_pawn.id
    
    # Get the original graphics frame count (pawn should have different frames than queen)
    original_frames_count = len(white_pawn.state.graphics.frames)
    original_first_frame = white_pawn.state.graphics.frames[0]
    
    print(f"Original pawn {original_id} has {original_frames_count} frames")
    
    # Promote the pawn
    game._check_pawn_promotion(white_pawn, (0, 3))  # Row 0 = promotion for white
    
    # Check that graphics changed
    new_frames_count = len(white_pawn.state.graphics.frames)
    new_first_frame = white_pawn.state.graphics.frames[0]
    
    print(f"Promoted queen {white_pawn.id} has {new_frames_count} frames")
    
    # The graphics should be different (different frames)
    assert new_first_frame != original_first_frame, "Graphics should change after promotion"
    
    # The piece should now be a queen
    assert white_pawn.id.startswith('QW'), f"Piece should be queen, got {white_pawn.id}"
    
    print(f"✅ Graphics successfully updated: {original_id} → {white_pawn.id}")
    print(f"✅ Frame count: {original_frames_count} → {new_frames_count}")


if __name__ == '__main__':
    test_pawn_promotion_graphics_real_game()
    print("🎉 Graphics promotion test passed!")
