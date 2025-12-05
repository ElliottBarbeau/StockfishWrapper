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
        result = engine.analyse(board, chess.engine.Limit(depth=depth), multipv=lines)
        return result
    finally:
        engine.quit()

def format_result(info_list):
    formatted = []
    for pv in info_list:
        moves_uci = [m.uci() for m in pv["pv"]]
        formatted.append({
            "score_cp": pv["score"].pov(chess.WHITE).score(mate_score=100000),
            "mate": pv["score"].pov(chess.WHITE).mate(),
            "pv_uci": moves_uci,
            "best_move": moves_uci[0] if moves_uci else None
        })
    return formatted

@app.post("/eval")
async def evaluate_post(request: Request):
    data = await request.json()
    fen = data["fen"]
    depth = data.get("depth", 14)
    lines = data.get("lines", 3)

    loop = asyncio.get_event_loop()
    try:
        raw = await loop.run_in_executor(
            None,
            lambda: run_stockfish_once(fen, depth, lines)
        )
    except Exception as exc:
        return {"error": str(exc)}

    return {
        "fen": fen,
        "depth": depth,
        "lines": lines,
        "results": format_result(raw)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("stockfish:app", host="0.0.0.0", port=8000)
