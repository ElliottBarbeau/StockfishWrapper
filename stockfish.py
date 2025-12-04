from fastapi import FastAPI
import chess
import chess.engine

app = FastAPI()

STOCKFISH_PATH = "/usr/bin/stockfish"  # default on Ubuntu
engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)


@app.get("/eval")
async def evaluate(fen: str, lines: int = 3, depth: int = 20):
    """
    Evaluate a chess position using local Stockfish.
    Returns multipv best lines in UCI and SAN.
    """

    board = chess.Board(fen)

    info = engine.analyse(board, chess.engine.Limit(depth=depth), multipv=lines)

    results = []

    for pv in info:
        # UCI moves
        uci_moves = [m.uci() for m in pv["pv"]]

        # SAN moves (human readable)
        san_moves = []
        temp_board = board.copy()
        for move in pv["pv"]:
            san_moves.append(temp_board.san(move))
            temp_board.push(move)

        results.append({
            "score_cp": pv.get("score").white().score(mate_score=100000),
            "mate": pv.get("score").white().mate(),
            "pv_uci": uci_moves,
            "pv_san": san_moves,
        })

    return {
        "fen": fen,
        "depth": depth,
        "lines": lines,
        "results": results
    }
