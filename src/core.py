# core.py
# This file is intended to be the stateless core logic for a 2048 game.

from enum import Enum
from typing import Tuple, List
import random

class GameProgressState(Enum):
    """Represents the current progress state of the game."""
    IN_PROGRESS = 1
    GAME_OVER = 2  # Lost
    GAME_WON = 3

class DIRECTION(Enum):
    """Represents the possible move directions."""
    UP = 1
    DOWN = 2
    LEFT = 3
    RIGHT = 4

# --- Board Helper Functions ---

def get_board_size(board: List[List[int]]) -> int:
    """
    Gets the size (N) of an N x N board.
    Args:
        board (List[List[int]]): The game board.
    Returns:
        int: The dimension of the board.
    Raises:
        ValueError: If the board is not square or empty.
    """
    if not board or not all(len(row) == len(board) for row in board):
        raise ValueError("Board must be a non-empty square matrix.")
    return len(board)

def get_empty_cells(board: List[List[int]]) -> List[Tuple[int, int]]:
    """
    Get coordinates of empty (0-value) cells in the given board.
    Args:
        board (List[List[int]]): The board to check.
    Returns:
        List[Tuple[int, int]]: List of (row, col) tuples for empty cells.
    """
    n = get_board_size(board)
    empty_cells = []
    for row in range(n):
        for col in range(n):
            if board[row][col] == 0:
                empty_cells.append((row, col))
    return empty_cells

def add_random_tile(board: List[List[int]]) -> Tuple[List[List[int]], bool]:
    """
    Adds a new tile (90% chance of 2, 10% chance of 4) to an empty cell on a copy of the board.
    Args:
        board (List[List[int]]): The current game board.
    Returns:
        Tuple[List[List[int]], bool]: A new board with the added tile and a boolean 
                                      indicating if a tile was successfully added.
                                      If no empty cells, returns the original board and False.
    """
    empty_cells = get_empty_cells(board)
    if not empty_cells:
        return [list(row) for row in board], False # Return a copy, no tile added

    new_board = [list(row) for row in board] # Work on a copy
    row, col = random.choice(empty_cells)
    new_board[row][col] = 4 if random.random() < 0.1 else 2
    return new_board, True

def initialize_board(size: int = 4) -> Tuple[List[List[int]], int, GameProgressState]:
    """
    Initializes a new game board with two random tiles.
    Args:
        size (int): The dimension of the N x N game board. Default is 4.
    Returns:
        Tuple[List[List[int]], int, GameProgressState]: The initial board, score (0), 
                                                       and game state (IN_PROGRESS).
    Raises:
        ValueError: If board size is not a positive integer.
    """
    if not isinstance(size, int) or size <= 0:
        raise ValueError("Board size must be a positive integer.")
    
    current_board: List[List[int]] = [[0] * size for _ in range(size)]
    
    # Add two initial tiles
    current_board, _ = add_random_tile(current_board)
    current_board, _ = add_random_tile(current_board)
    
    initial_score = 0
    initial_state = GameProgressState.IN_PROGRESS
    
    return current_board, initial_score, initial_state

# --- Line Manipulation (Core Move Logic Helpers) ---

def _compress_line(line: List[int]) -> Tuple[List[int], bool]:
    """
    Compresses a single line to the left (moves all non-zero tiles to the "start").
    Args:
        line (List[int]): The line to compress.
    Returns:
        Tuple[List[int], bool]: The compressed line and a boolean indicating if it changed.
    """
    n = len(line)
    original_line_tuple = tuple(line)
    new_line_compressed = [i for i in line if i != 0]
    new_line_compressed += [0] * (n - len(new_line_compressed))
    changed = (tuple(new_line_compressed) != original_line_tuple)
    return new_line_compressed, changed

def _merge_line(line: List[int]) -> Tuple[List[int], int, bool]:
    """
    Merges adjacent identical numbers in a line (assumed to be moving left / towards index 0).
    It's best if the line is already compressed before calling this.
    Args:
        line (List[int]): The input line to be merged.
    Returns:
        Tuple[List[int], int, bool]: Merged line, score increase from merges, 
                                     and a boolean indicating if changed by merging.
    """
    n = len(line)
    original_line_tuple = tuple(line)
    score_increase = 0
    new_line_merged = [0] * n 
    write_idx = 0
    read_idx = 0
    
    while read_idx < n:
        current_val = line[read_idx]
        if current_val == 0: # Should ideally not happen if pre-compressed
            read_idx += 1
            continue

        if read_idx + 1 < n and current_val == line[read_idx + 1]:
            merged_value = current_val * 2
            new_line_merged[write_idx] = merged_value
            score_increase += merged_value
            read_idx += 2 # Skip current and next tile (which was merged)
        else:
            new_line_merged[write_idx] = current_val
            read_idx += 1
        write_idx += 1
            
    changed_by_merge = (tuple(new_line_merged) != original_line_tuple)
    return new_line_merged, score_increase, changed_by_merge

def _process_single_line_leftwise(line: List[int]) -> Tuple[List[int], int, bool]:
    """
    Applies compress, merge, then compress again to a single line, moving left.
    Args:
        line (List[int]): The line to process.
    Returns:
        Tuple[List[int], int, bool]: The processed line, score increase, and if the line changed.
    """
    original_line_tuple = tuple(line)
    
    # Step 1: Compress
    compressed_line, _ = _compress_line(line)
    # Step 2: Merge
    merged_line, score_delta_from_merge, _ = _merge_line(compressed_line)
    # Step 3: Compress again (after merge)
    final_processed_line, _ = _compress_line(merged_line)
    
    line_actually_changed = (tuple(final_processed_line) != original_line_tuple)
    
    return final_processed_line, score_delta_from_merge, line_actually_changed

# --- Board Transformations ---

def transpose_board(board: List[List[int]]) -> List[List[int]]:
    """
    Transposes a given board (swaps rows and columns).
    Args:
        board (List[List[int]]): The board to transpose.
    Returns:
        List[List[int]]: A new transposed board.
    """
    n = get_board_size(board)
    new_board = [[0] * n for _ in range(n)]
    for r in range(n):
        for c in range(n):
            new_board[c][r] = board[r][c]
    return new_board

def reverse_rows(board: List[List[int]]) -> List[List[int]]:
    """
    Reverses each row in a given board.
    Args:
        board (List[List[int]]): The board whose rows are to be reversed.
    Returns:
        List[List[int]]: A new board with rows reversed.
    """
    new_board = []
    for row in board:
        new_board.append(row[::-1]) # Create a new reversed list for each row
    return new_board

# --- Core Game Move Processing ---

def _apply_left_processing_to_all_lines(current_board_state: List[List[int]]) -> Tuple[List[List[int]], int, bool]:
    """
    Processes all lines of a board by applying leftward compress-merge-compress.
    Args:
        current_board_state (List[List[int]]): The board to process.
    Returns:
        Tuple[List[List[int]], int, bool]: The processed board, total score increase, 
                                           and a flag if any part of the board changed.
    """
    n = get_board_size(current_board_state)
    board_changed_overall = False
    total_score_increase = 0
    processed_board = [list(r) for r in current_board_state] # Work on a copy

    for r_idx in range(n):
        line_to_process = processed_board[r_idx]
        final_line, score_from_line, line_changed = _process_single_line_leftwise(line_to_process)
        
        if line_changed:
            processed_board[r_idx] = final_line
            total_score_increase += score_from_line
            board_changed_overall = True
    
    return processed_board, total_score_increase, board_changed_overall

def process_move(board: List[List[int]], direction: DIRECTION) -> Tuple[List[List[int]], int, bool]:
    """
    Processes a move in the specified direction on a copy of the board.
    Args:
        board (List[List[int]]): The current game board.
        direction (DIRECTION): The direction to move.
    Returns:
        Tuple[List[List[int]], int, bool]: 
            - The new board state after the move.
            - The score gained from this move.
            - A boolean indicating if the board changed as a result of the move.
    Raises:
        ValueError: If an invalid direction is specified.
    """
    board_to_operate_on = [list(r) for r in board] # Work on a copy
    score_gained = 0
    move_changed_board = False

    if direction == DIRECTION.LEFT:
        board_to_operate_on, score_gained, move_changed_board = \
            _apply_left_processing_to_all_lines(board_to_operate_on)
    
    elif direction == DIRECTION.RIGHT:
        temp_reversed_board = reverse_rows(board_to_operate_on)
        processed_reversed_board, score_gained, move_changed_board = \
            _apply_left_processing_to_all_lines(temp_reversed_board)
        if move_changed_board:
            board_to_operate_on = reverse_rows(processed_reversed_board)

    elif direction == DIRECTION.UP:
        temp_transposed_board = transpose_board(board_to_operate_on)
        processed_transposed_board, score_gained, move_changed_board = \
            _apply_left_processing_to_all_lines(temp_transposed_board)
        if move_changed_board:
            board_to_operate_on = transpose_board(processed_transposed_board)

    elif direction == DIRECTION.DOWN:
        temp_transposed_board = transpose_board(board_to_operate_on)
        temp_reversed_transposed_board = reverse_rows(temp_transposed_board)
        
        processed_board_intermediate, score_gained, move_changed_board = \
            _apply_left_processing_to_all_lines(temp_reversed_transposed_board)
        
        if move_changed_board:
            unreversed_board = reverse_rows(processed_board_intermediate)
            board_to_operate_on = transpose_board(unreversed_board)
    else:
        raise ValueError("Invalid direction specified for process_move.")

    return board_to_operate_on, score_gained, move_changed_board

# --- Game State Checks ---

def check_for_win(board: List[List[int]], win_tile: int = 2048) -> bool:
    """
    Check if the game is won (a tile with win_tile value exists).
    Args:
        board (List[List[int]]): The game board.
        win_tile (int): The tile value that signifies a win. Default is 2048.
    Returns:
        bool: True if the game is won, False otherwise.
    """
    n = get_board_size(board)
    for r in range(n):
        for c in range(n):
            if board[r][c] == win_tile:
                return True
    return False

def is_move_possible_in_direction(board: List[List[int]], direction: DIRECTION) -> bool:
    """
    Check if any tile can move or merge in the given specific direction.
    Args:
        board (List[List[int]]): The game board.
        direction (DIRECTION): The direction to check.
    Returns:
       bool: True if at least one tile can move or merge in that direction, False otherwise.
    """
    n = get_board_size(board)
    for r_idx in range(n):
        for c_idx in range(n):
            if board[r_idx][c_idx] == 0:
                continue  # Only non-empty tiles can initiate a move

            if direction == DIRECTION.UP:
                if r_idx > 0 and (board[r_idx-1][c_idx] == 0 or board[r_idx-1][c_idx] == board[r_idx][c_idx]):
                    return True
            elif direction == DIRECTION.DOWN:
                if r_idx < n - 1 and (board[r_idx+1][c_idx] == 0 or board[r_idx+1][c_idx] == board[r_idx][c_idx]):
                    return True
            elif direction == DIRECTION.LEFT:
                if c_idx > 0 and (board[r_idx][c_idx-1] == 0 or board[r_idx][c_idx-1] == board[r_idx][c_idx]):
                    return True
            elif direction == DIRECTION.RIGHT:
                if c_idx < n - 1 and (board[r_idx][c_idx+1] == 0 or board[r_idx][c_idx+1] == board[r_idx][c_idx]):
                    return True
    return False

def is_any_move_possible(board: List[List[int]]) -> bool:
    """
    Checks if any move is possible in any direction on the board.
    Args:
        board (List[List[int]]): The game board.
    Returns:
        bool: True if any move can be made, False otherwise.
    """
    for direction_enum_member in DIRECTION:
        if is_move_possible_in_direction(board, direction_enum_member):
            return True
    return False

def determine_game_status(board: List[List[int]], win_tile: int = 2048) -> GameProgressState:
    """
    Determines the current progress state of the game based on the board.
    Args:
        board (List[List[int]]): The current game board.
        win_tile (int): The tile value that signifies a win. Default is 2048.
    Returns:
        GameProgressState: The current state (IN_PROGRESS, GAME_WON, GAME_OVER).
    """
    if check_for_win(board, win_tile):
        return GameProgressState.GAME_WON
    
    if not get_empty_cells(board) and not is_any_move_possible(board):
        # Board is full AND no moves are possible (merges or shifts to empty)
        return GameProgressState.GAME_OVER
        
    if not is_any_move_possible(board) and not get_empty_cells(board): # Redundant with above but explicit
        return GameProgressState.GAME_OVER

    # If not won and moves are still possible (either to empty or merge)
    # Or if there are empty cells (meaning a tile could potentially be added after a move,
    # or a shift move is possible into an empty cell)
    if is_any_move_possible(board) or get_empty_cells(board):
         return GameProgressState.IN_PROGRESS
    
    # Default fallback, though above conditions should cover states.
    # This means no win, but also no moves possible.
    return GameProgressState.GAME_OVER
