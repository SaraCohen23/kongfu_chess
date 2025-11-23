import pathlib
from Board import Board
from PieceFactory import PieceFactory
from Game import Game

CELL_PX = 64
# Board coordinates on background - calculated dynamically based on background size
# Background is 1321x830, Board is 8*64=512 wide
# Center X = 1321/2 = 660.5, Board left = 660.5 - 512/2 = 404.5 ≈ 405
BOARD_OFFSET_X = 405  # Centered horizontally
BOARD_OFFSET_Y = 130


def create_game(pieces_root: str | pathlib.Path, img_factory) -> Game:
    """Build a *Game* from the on-disk asset hierarchy rooted at *pieces_root*.

    This reads *board.csv* located inside *pieces_root*, creates a board
    with background image, instantiates every piece via PieceFactory
    and returns a ready-to-run *Game* instance.
    """
    pieces_root = pathlib.Path(pieces_root)
    board_csv = pieces_root / "board.csv"
    if not board_csv.exists():
        raise FileNotFoundError(board_csv)

    # Background image
    background_png = pieces_root / "background.png"
    if not background_png.exists():
        # Try BACKGROUND.PNG as well
        background_png = pieces_root / "BACKGROUND.PNG"
        if not background_png.exists():
            raise FileNotFoundError(f"Background image not found: {background_png}")

    # Board image  
    board_png = pieces_root / "board.png"
    if not board_png.exists():
        raise FileNotFoundError(board_png)

    loader = img_factory

    # Load the background (no resizing - keep original size)
    background_img = loader(background_png, None, False)
    
    # Load the board
    board_only_img = loader(board_png, (CELL_PX*8, CELL_PX*8), False)
    
    # Draw the board on the background at the specified position
    board_only_img.draw_on(background_img, BOARD_OFFSET_X, BOARD_OFFSET_Y)

    # Load and add the logo in the top-left corner
    logo_png = pieces_root / "logo .png"  # Filename with space
    if logo_png.exists():
        try:
            # Load logo in medium size and beautiful proportions
            logo_img = loader(logo_png, (150, 100), True)  # Medium size, keep aspect ratio
            # Place in the top-left corner with nice spacing
            logo_x = 20   # Margin from left
            logo_y = 20   # Margin from top
            logo_img.draw_on(background_img, logo_x, logo_y)
        except Exception as e:
            print(f"Warning: Could not load logo: {e}")

    # Create board with adjusted coordinates (use background as final board image)
    board = Board(cell_H_pix=CELL_PX, cell_W_pix=CELL_PX, 
                  W_cells=8, H_cells=8, 
                  img=background_img,
                  board_offset_x=BOARD_OFFSET_X, 
                  board_offset_y=BOARD_OFFSET_Y)

    from GraphicsFactory import GraphicsFactory
    gfx_factory = GraphicsFactory(img_factory)
    pf = PieceFactory(board, pieces_root, graphics_factory=gfx_factory)

    pieces = []
    with board_csv.open() as f:
        for r, line in enumerate(f):
            for c, code in enumerate(line.strip().split(",")):
                if code:
                    pieces.append(pf.create_piece(code, (r, c)))

    return Game(pieces, board, pieces_root, img_factory) 