// --- Constants ---
const API_BASE_URL: string = "";
const TILE_BASE_SIZE_PX: number = 80;
const TILE_MARGIN_PX: number = 8;

// --- TypeScript Interfaces to match Backend Pydantic Models ---
interface ApiGameStateData {
    board: number[][];
    score: number;
    progress: "IN_PROGRESS" | "GAME_WON" | "GAME_OVER";
    win_tile: number;
    board_size: number;
}

interface ApiMoveResponseData extends ApiGameStateData {
    move_was_effective: boolean;
    message?: string;
}

// --- Global State Variables ---
let currentGameId: string | null = null;
let currentGrid: number[][] = [];
let currentScore: number = 0;
let boardSize: number = 4;
let currentWinTile: number = 2048;

// --- DOM Elements ---
const gameBoardElement = document.getElementById("game-board") as HTMLDivElement;
const scoreElement = document.getElementById("score") as HTMLSpanElement;
const newGameButton = document.getElementById("new-game-button") as HTMLButtonElement;
const boardSizeInput = document.getElementById("board-size") as HTMLInputElement;
const gameOverMessageElement = document.getElementById("game-over-message") as HTMLDivElement;
const finalScoreElement = document.getElementById("final-score") as HTMLSpanElement;
const restartGameButton = document.getElementById("restart-game-button") as HTMLButtonElement;

// --- API Fetch Utility ---
async function fetchAPI<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    try {
        const response: Response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...options,
            headers: {
                "Content-Type": "application/json",
                ...options.headers,
            },
        });
        if (!response.ok) {
            const errorData: { message?: string; detail?: any } = await response.json().catch(() => ({ message: "Unknown API error or non-JSON response" }));
            console.error("API Error Response:", response.status, response.statusText, errorData);
            // FastAPI often puts validation errors in errorData.detail
            let errorMessage = errorData.message || (Array.isArray(errorData.detail) ? errorData.detail.map(d => d.msg).join(', ') : JSON.stringify(errorData.detail)) || response.statusText;
            throw new Error(`API request to ${endpoint} failed: ${response.status} ${errorMessage}`);
        }
        return response.json() as Promise<T>;
    } catch (error) {
        console.error("Fetch API Error (outer):", error);
        const errorMessage = error instanceof Error ? error.message : "An unknown error occurred";
        if (errorMessage.startsWith("API request")) {
             alert(`Error communicating with the game server: ${errorMessage}`);
        } else {
             alert(`Error communicating with the game server: Failed to fetch. Check console for details.`);
        }
        throw error;
    }
}

// --- Board Rendering and Styling ---
function updateBoardSizeStyle(size: number): void {
    if (!gameBoardElement) return;
    const boardDimension: number = (TILE_BASE_SIZE_PX * size) + (TILE_MARGIN_PX * (size + 1));
    gameBoardElement.style.width = `${boardDimension}px`;
    gameBoardElement.style.height = `${boardDimension}px`;
    gameBoardElement.style.gridTemplateColumns = `repeat(${size}, 1fr)`;
    gameBoardElement.style.gridTemplateRows = `repeat(${size}, 1fr)`;
    gameBoardElement.style.gap = `${TILE_MARGIN_PX}px`;
    gameBoardElement.style.padding = `${TILE_MARGIN_PX}px`;
}

function renderBoard(): void {
    if (!gameBoardElement) return;
    gameBoardElement.innerHTML = "";
    updateBoardSizeStyle(boardSize);
    currentGrid.forEach((row: number[]) => {
        row.forEach((value: number) => {
            const tile: HTMLDivElement = document.createElement("div");
            tile.className = "tile";
            if (value > 0) {
                tile.textContent = value.toString();
                tile.dataset.value = value.toString();
                if (value > 1000 && value < 10000) tile.style.fontSize = "1.4em";
                else if (value >= 10000) tile.style.fontSize = "1.1em";
                else tile.style.fontSize = "1.8em";
            } else {
                tile.classList.add("tile-empty");
            }
            gameBoardElement.appendChild(tile);
        });
    });
}

// --- Game Logic ---
type MoveDirectionString = "up" | "down" | "left" | "right";

// Mapping from string direction to number expected by backend
const directionToNumberMap: { [key in MoveDirectionString]: number } = {
    "up": 1,    // Corresponds to core.DIRECTION.UP
    "down": 2,  // Corresponds to core.DIRECTION.DOWN
    "left": 3,  // Corresponds to core.DIRECTION.LEFT
    "right": 4  // Corresponds to core.DIRECTION.RIGHT
};

async function startNewGame(): Promise<void> {
    try {
        const requestedBoardSize: number = parseInt(boardSizeInput.value, 10);
        if (isNaN(requestedBoardSize) || requestedBoardSize < 2 || requestedBoardSize > 6) {
            alert("Please enter a valid board size between 2 and 6.");
            boardSizeInput.value = "4";
            boardSize = 4;
        } else {
            boardSize = requestedBoardSize;
        }
        const settingsPayload = { size: boardSize };
        const data: ApiGameStateData = await fetchAPI<ApiGameStateData>("/game/new", {
            method: "POST",
            body: JSON.stringify(settingsPayload),
        });
        currentGrid = data.board;
        currentScore = data.score;
        currentWinTile = data.win_tile;
        boardSize = data.board_size;
        boardSizeInput.value = String(boardSize);
        updateScoreDisplay();
        renderBoard();
        if (data.progress === "GAME_OVER" || data.progress === "GAME_WON") {
            handleGameOver();
        } else {
            if (gameOverMessageElement) gameOverMessageElement.classList.add("hidden");
            if (gameBoardElement) gameBoardElement.classList.remove("blurred");
        }
        console.log("New game started. Size:", boardSize, "Win Tile:", currentWinTile, "Initial Score:", currentScore);
    } catch (error) {
        console.error("Failed to start new game:", error);
    }
}

async function makeMove(directionString: MoveDirectionString): Promise<void> {
    if (!currentGrid || currentGrid.length === 0) {
        console.warn("No active game board to make a move.");
        return;
    }
    if (gameOverMessageElement && !gameOverMessageElement.classList.contains("hidden")) {
        console.log("Game is over, no moves allowed.");
        return;
    }

    // Map the string direction to its numeric representation
    const numericDirection = directionToNumberMap[directionString];
    console.log("Making move:", directionString, "Numeric Direction:", numericDirection);

    try {
        const payload = {
            board: currentGrid,
            score: currentScore,
            direction: numericDirection, // Send the numeric direction
            win_tile: currentWinTile
        };
        console.log("Making move with payload:", payload);

        const data: ApiMoveResponseData = await fetchAPI<ApiMoveResponseData>("/game/move", {
            method: "POST",
            body: JSON.stringify(payload),
        });

        console.log("Move response data:", data);
        currentGrid = data.board;
        currentScore = data.score;
        updateScoreDisplay();
        renderBoard();
        if (data.progress === "GAME_OVER" || data.progress === "GAME_WON") {
            if (data.message) console.log("Game message from server:", data.message);
            handleGameOver();
        } else {
            if (data.message) {
                console.log("Game message from server:", data.message);
            }
        }
    } catch (error) {
        console.error(`Failed to make move ${directionString}:`, error);
    }
}

function updateScoreDisplay(): void {
    if (scoreElement) {
        scoreElement.textContent = currentScore.toString();
    }
}

function handleGameOver(): void {
    if (finalScoreElement) finalScoreElement.textContent = currentScore.toString();
    if (gameOverMessageElement) gameOverMessageElement.classList.remove("hidden");
    if (gameBoardElement) gameBoardElement.classList.add("blurred");
    console.log("Game Over! Final Score:", currentScore);
}

// --- Event Handlers ---
function handleKeyPress(event: KeyboardEvent): void {
    if (gameOverMessageElement && !gameOverMessageElement.classList.contains("hidden")) {
        return;
    }
    let moved: boolean = false;
    let directionString: MoveDirectionString | null = null;

    switch (event.key) {
        case "ArrowUp": case "w": directionString = "up"; break;
        case "ArrowDown": case "s": directionString = "down"; break;
        case "ArrowLeft": case "a": directionString = "left"; break;
        case "ArrowRight": case "d": directionString = "right"; break;
    }
    if (directionString) {
        makeMove(directionString);
        moved = true;
    }
    if (moved) {
        event.preventDefault();
    }
}

// --- Initialization ---
document.addEventListener("DOMContentLoaded", () => {
    if (newGameButton) {
        newGameButton.addEventListener("click", startNewGame);
    }
    if (restartGameButton) {
        restartGameButton.addEventListener("click", startNewGame);
    }
    document.addEventListener("keydown", handleKeyPress);
    if (boardSizeInput) {
        boardSizeInput.value = String(boardSize);
    }
    startNewGame();
});

// --- Swipe Detection ---
let touchstartX: number = 0;
let touchstartY: number = 0;
let touchendX: number = 0;
let touchendY: number = 0;

gameBoardElement?.addEventListener('touchstart', (event: TouchEvent) => {
    if (gameOverMessageElement && !gameOverMessageElement.classList.contains("hidden")) {
        return;
    }
    touchstartX = event.changedTouches[0].screenX;
    touchstartY = event.changedTouches[0].screenY;
}, { passive: true });

gameBoardElement?.addEventListener('touchend', (event: TouchEvent) => {
    if (gameOverMessageElement && !gameOverMessageElement.classList.contains("hidden")) {
        return;
    }
    touchendX = event.changedTouches[0].screenX;
    touchendY = event.changedTouches[0].screenY;
    handleSwipe();
}, false);

function handleSwipe(): void {
    const deltaX: number = touchendX - touchstartX;
    const deltaY: number = touchendY - touchstartY;
    const threshold: number = 30;
    let directionString: MoveDirectionString | null = null;

    if (Math.abs(deltaX) < threshold && Math.abs(deltaY) < threshold) {
        return;
    }
    if (Math.abs(deltaX) > Math.abs(deltaY)) {
        directionString = deltaX > 0 ? "right" : "left";
    } else {
        directionString = deltaY > 0 ? "down" : "up";
    }
    if (directionString) {
        makeMove(directionString);
    }
}