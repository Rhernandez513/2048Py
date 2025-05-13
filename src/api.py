from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Optional
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

import core

# Initialize the rate limiter
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="2048 Game API",
    description="A stateless API for playing the 2048 game. "\
                "Manage your game state (board, score, win_tile) on the client side.",
    version="1.0.0"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- Pydantic Models for API requests and responses ---

class NewGameSettings(BaseModel):
    """Settings for creating a new game."""
    size: Optional[int] = Field(
        default=4,
        gt=1, # Board size must be at least 2x2
        description="Size of the N x N game board (e.g., 4 for a 4x4 board)."
    )
    win_tile: Optional[int] = Field(
        default=2048,
        gt=0,
        description="The tile value to achieve for winning the game (e.g., 2048)."
    )

class GameStateData(BaseModel):
    """Represents the complete state of a game instance."""
    board: List[List[int]] = Field(..., description="The N x N game board, represented as a list of lists.")
    score: int = Field(..., ge=0, description="Current score of the game.")
    progress: core.GameProgressState = Field(
        ...,
        description="Current progress state of the game (IN_PROGRESS, GAME_WON, GAME_OVER)."
    )
    win_tile: int = Field(..., gt=0, description="The tile value required to win this game instance.")
    board_size: int = Field(..., gt=0, description="The dimension N of the N x N board.")


class MoveRequestData(BaseModel):
    """Data required to make a move."""
    board: List[List[int]] = Field(..., description="Current N x N game board state before the move.")
    score: int = Field(..., ge=0, description="Current score before the move.")
    direction: core.DIRECTION = Field(
        ...,
        description="Direction of the move (UP, DOWN, LEFT, RIGHT)."
    )
    win_tile: int = Field(..., gt=0, description="The win condition tile for this game instance.")
    # board_size is implicitly derived from the board structure.

class MoveResponseData(GameStateData):
    """Response after a move, including the new game state and move effectiveness."""
    move_was_effective: bool = Field(
        ...,
        description="True if the move resulted in a change to the board state, False otherwise."
    )
    message: Optional[str] = Field(
        default=None,
        description="An optional message, e.g., if a move was invalid, game ended, or other info."
    )

# --- API Endpoints ---

@app.post("/game/new", response_model=GameStateData, summary="Start a New 2048 Game")
@limiter.limit("100/minute")
async def start_new_game(request: Request, settings: NewGameSettings):
    """
    Initializes a new 2048 game based on the provided settings (size and win_tile).

    - **size**: Dimension of the N x N board (e.g., 4 for 4x4). Default is 4.
    - **win_tile**: Tile value to reach to win (e.g., 2048). Default is 2048.

    Returns the initial game state, including the board with two random tiles,
    score (0), progress status (IN_PROGRESS), and the specified win_tile.
    """
    try:
        # Initialize the board using the game logic function
        initial_board, initial_score, _ = core.initialize_board(settings.size if settings.size is not None else 4)

        # Determine the initial game progress state using the specified win_tile.
        # For a standard new game, this should always be IN_PROGRESS.
        current_progress = core.determine_game_status(initial_board, settings.win_tile if settings.win_tile is not None else 2048)

        return GameStateData(
            board=initial_board,
            score=initial_score,
            progress=current_progress,
            win_tile=settings.win_tile,
            board_size=settings.size  # or core.get_board_size(initial_board)
        )
    except ValueError as e:
        # Handle errors from game_logic.initialize_board (e.g., invalid size)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Catch any other unexpected errors during game initialization
        # It's good practice to log these errors on the server.
        # logger.error(f"Unexpected error in /game/new: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during game creation: {str(e)}")


@app.post("/game/move", response_model=MoveResponseData, summary="Make a Move in the Game")
@limiter.limit("100/minute")
async def make_move(request: Request, request_data: MoveRequestData):
    """
    Processes a player's move in the game.

    Requires the current `board` state, `score`, the `direction` of the move,
    and the `win_tile` for this game instance.

    The API will:
    1. Attempt to process the move (slide tiles, merge).
    2. If the move changed the board, add a new random tile (2 or 4).
    3. Determine the new game status (IN_PROGRESS, GAME_WON, GAME_OVER).

    Returns the updated game state, whether the move was effective, and an optional message.
    """
    current_board = request_data.board
    current_score = request_data.score
    direction = request_data.direction
    win_tile = request_data.win_tile

    # Basic validation for board structure (optional, game_logic might also do this)
    try:
        board_size_from_request = core.get_board_size(current_board)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid board structure in request: {str(e)}")

    # Initialize variables for the response
    final_board = [list(row) for row in current_board] # Work on a copy
    final_score = current_score
    message_for_client: Optional[str] = None
    move_was_effective: bool = False

    try:
        # Step 1: Process the slide and merge logic for the chosen direction
        board_after_slide, score_increase, slide_changed_board = core.process_move(
            current_board, direction
        )

        move_was_effective = slide_changed_board

        if move_was_effective:
            final_board = board_after_slide
            final_score += score_increase

            # Step 2: If the slide was effective, add a new random tile
            board_after_tile_add, tile_successfully_added = core.add_random_tile(final_board)

            if tile_successfully_added:
                final_board = board_after_tile_add
            # If a tile couldn't be added (e.g., board became full after slide but before new tile),
            # final_board remains the state after the slide.
            # game_logic.determine_game_status will correctly assess this state.
        else:
            # The attempted move did not change the board state
            message_for_client = "Move was not effective; board state unchanged by slide."
            # final_board and final_score remain as current_board and current_score

        # Step 3: Determine the new game status based on the (potentially) updated final_board
        current_progress = core.determine_game_status(final_board, win_tile)

        # Enhance client message based on game status
        if current_progress == core.GameProgressState.GAME_WON:
            message_for_client = "Congratulations! You won!"
        elif current_progress == core.GameProgressState.GAME_OVER:
            message_for_client = "Game Over. No more valid moves."

        return MoveResponseData(
            board=final_board,
            score=final_score,
            progress=current_progress,
            win_tile=win_tile,
            board_size=board_size_from_request, # Size of the board
            move_was_effective=move_was_effective,
            message=message_for_client
        )
    except ValueError as e:
        # Handles errors from game_logic functions if invalid parameters are somehow passed
        # (e.g., an invalid direction if enum wasn't used, or issues from board manipulation)
        raise HTTPException(status_code=400, detail=f"Error processing move: {str(e)}")
    except Exception as e:
        # Catch any other unexpected errors from the game logic
        # logger.error(f"Unexpected error in /game/move: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred while processing the move: {str(e)}")
