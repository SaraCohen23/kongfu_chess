from Board import Board
from Physics import IdlePhysics, MovePhysics, JumpPhysics, RestPhysics, BasePhysics, KnightJumpPhysics


class PhysicsFactory:
    """Instantiate the correct *Physics* subclass for a given state."""

    def __init__(self, board: Board):
        self.board = board

    def create(self, start_cell, state_name: str, cfg, piece_type: str = None) -> BasePhysics:
        speed = cfg.get("speed_m_per_sec", 0.0)

        name_l = state_name.lower()
        
        # Special case for Knight pieces - they can jump over other pieces even with "move"
        if piece_type and piece_type.startswith('N') and name_l == "move":
            cls = KnightJumpPhysics
        elif name_l == "move":
            cls = MovePhysics
        elif name_l == "jump":
            cls = JumpPhysics
        elif name_l.endswith("rest") or name_l == "rest":
            cls = RestPhysics
        else:
            cls = IdlePhysics

        if cls is RestPhysics:
            duration_ms = cfg.get("duration_ms", 3000)
            return cls(self.board, duration_ms / 1000)  # duration in seconds

        # For other physics classes param is speed/duration
        return cls(self.board, speed)
