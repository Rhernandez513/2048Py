# cli_driver.py
# This file is intended to be run to play or test the 2048 game on the CLI

from typing import List

from core import (
    DIRECTION,
    GameProgressState,
    initialize_board,
    process_move,
    add_random_tile,
    get_empty_cells,
    determine_game_status
)

def main():
    BOARD_SIZE = 4
    WIN_CONDITION_TILE = 2048 # For testing, can be set lower e.g. 32 or 64

    # 1. Initialize game
    current_board, current_score, current_progress = initialize_board(BOARD_SIZE)
    display_board_state(current_board, current_score, current_progress)

    # 2. Game Loop
    while current_progress == GameProgressState.IN_PROGRESS:
        # Get player input (simplified here)
        move_input = input("Enter move (W/A/S/D for Up/Left/Down/Right, Q to quit): ").upper()
        
        if move_input == 'Q':
            print("Quitting game.")
            break

        direction_map = {'W': DIRECTION.UP, 'A': DIRECTION.LEFT, 'S': DIRECTION.DOWN, 'D': DIRECTION.RIGHT}
        chosen_direction = direction_map.get(move_input)

        if not chosen_direction:
            print("Invalid input. Use W, A, S, D.")
            continue

        # 3. Process the move
        next_board_candidate, score_increase, move_was_made = process_move(current_board, chosen_direction)

        if move_was_made:
            current_board = next_board_candidate
            current_score += score_increase
            
            # 4. Add a new random tile if the move changed the board
            current_board, tile_added = add_random_tile(current_board)
            
            # If board is full and tile couldn't be added, game might be over.
            # determine_game_status will check this.
            if not tile_added and not get_empty_cells(current_board):
                 pass # Let determine_game_status handle the full board scenario

            # 5. Update game progress state
            current_progress = determine_game_status(current_board, WIN_CONDITION_TILE)
        else:
            print("Move did not change the board. Try a different direction.")
            # Optional: Check if game is over even if move didn't change board
            # This is important if the only available moves don't change the board state
            # but the game is not yet technically over (e.g. full board, no merges)
            # However, determine_game_status after a failed move attempt isn't strictly necessary
            # if the board itself hasn't changed. The state would be the same.
            # But if a player tries a direction that does nothing, they might be stuck.
            # Re-evaluating status ensures we catch game over if no valid moves exist.
            current_progress = determine_game_status(current_board, WIN_CONDITION_TILE)


        display_board_state(current_board, current_score, current_progress)

    # 6. Game Ended
    print("\n--- Final Board State ---")
    display_board_state(current_board, current_score, current_progress)
    if current_progress == GameProgressState.GAME_WON:
        print("Congratulations! You reached the 2048 tile (or configured win tile)!")
    elif current_progress == GameProgressState.GAME_OVER:
        print("No more moves possible. Better luck next time!")


# --- Display Function (Example of external usage) ---
def display_board_state(board: List[List[int]], score: int, progress: GameProgressState):
    """Prints the board, score, and game status to the console."""
    print(f"\nScore: {score}")
    status_message = {
        GameProgressState.IN_PROGRESS: f"Status: {progress.name}",
        GameProgressState.GAME_WON: "YOU WON!",
        GameProgressState.GAME_OVER: "GAME OVER!"
    }
    print(status_message.get(progress, f"Status: {progress.name} (Unknown)"))
            
    for row in board:
        print("\t".join(map(str, row)))
    print("-" * (len(board) * 6)) # Adjust width based on board size

# --- Example Game Loop (how to use the stateless functions) ---
if __name__ == "__main__":
    main()