import os
os.environ["PYTHON_CHESS_ENGINE_SYNC"] = "1"

import chess
import chess.engine
import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

STOCKFISH_PATH = "/usr/games/stockfish"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def run_stockfish_once(fen: str, depth: int, lines: int):
    board = chess.Board(fen)
    engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
    try:
        return engine.analyse(board, chess.engine.Limit(depth=depth), multipv=lines)
    finally:
        engine.quit()

def format_result(info_list):
    out = []
    for pv in info_list:
        moves = [m.uci() for m in pv["pv"]]
        score = pv["score"].pov(chess.WHITE)
        out.append({
            "best_move": moves[0] if moves else None,
            "pv_uci": moves,
            "score_cp": score.score(mate_score=100000),
            "mate": score.mate(),
        })
    return out

@app.post("/eval")
async def eval_post(request: Request):
    data = await request.json()
    fen = data["fen"]
    depth = data.get("depth", 14)
    lines = data.get("lines", 3)

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            None, lambda: run_stockfish_once(fen, depth, lines)
        )
    except Exception as exc:
        return {"error": str(exc)}

    return {
        "fen": fen,
        "depth": depth,
        "lines": lines,
        "results": format_result(result),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("stockfish:app", host="0.0.0.0", port=8000)
