from fastapi import FastAPI, HTTPException, Header
import os
import chess
import chess.engine

app = FastAPI()

STOCKFISH_PATH = "/usr/bin/stockfish"
SECRET = os.getenv("STOCKFISH_SECRET")

engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)


@app.get("/eval")
async def evaluate(
    fen: str,
    lines: int = 3,
    depth: int = 20,
    x_api_key: str = Header(None)
):
    # Check API key
    if SECRET is None:
        raise HTTPException(status_code=500, detail="Server misconfigured: no secret set.")

    if x_api_key != SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Prepare evaluation
    board = chess.Board(fen)
    info = engine.analyse(board, chess.engine.Limit(depth=depth), multipv=lines)

    results = []

    for pv in info:
        uci_moves = [m.uci() for m in pv["pv"]]

        temp = board.copy()
        san_moves = []
        for move in pv["pv"]:
            san_moves.append(temp.san(move))
            temp.push(move)

        score = pv["score"].white()

        results.append({
            "score_cp": score.score(mate_score=100000),
            "mate": score.mate(),
            "pv_uci": uci_moves,
            "pv_san": san_moves
        })

    return {
        "fen": fen,
        "depth": depth,
        "lines": lines,
        "results": results
    }
