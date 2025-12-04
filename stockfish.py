from fastapi import FastAPI, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi.responses import JSONResponse

import chess
import chess.engine
import uvicorn


limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter


# -----------------------------
# Engine Loader (Corrected)
# -----------------------------
ENGINE_PATH = "/usr/games/stockfish"

def load_engine():
    engine = chess.engine.SimpleEngine.popen_uci(ENGINE_PATH)

    # Configure safely AFTER starting the engine
    try:
        engine.configure({
            "Threads": 1,
            "Hash": 32
        })
    except Exception as e:
        print("Engine config warning:", e)

    return engine


engine = load_engine()


# -----------------------------
# Restart engine on crash
# -----------------------------
def restart_engine():
    global engine
    try:
        engine.quit()
    except:
        pass
    engine = load_engine()


# -----------------------------
# Request Model
# -----------------------------
class EvalRequest(BaseModel):
    fen: str
    lines: int = 1
    depth: int = 16


# -----------------------------
# Evaluation Endpoint
# -----------------------------
@app.post("/eval")
@limiter.limit("20/minute")
async def evaluate(request: Request, data: EvalRequest):

    fen = data.fen
    depth = min(data.depth, 18)
    lines = min(data.lines, 2)

    board = chess.Board(fen)

    try:
        info = engine.analyse(
            board,
            chess.engine.Limit(depth=depth),
            multipv=lines
        )
    except chess.engine.EngineTerminatedError:
        restart_engine()
        return JSONResponse(
            status_code=500,
            content={"error": "Stockfish crashed and was automatically restarted."}
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

    # Format results
    lines_out = []
    for entry in info:
        pv_moves = [m.uci() for m in entry.get("pv", [])]
        score = entry["score"]

        lines_out.append({
            "best_move_uci": pv_moves[0] if pv_moves else None,
            "pv_uci": pv_moves,
            "score_cp": score.white().score(mate_score=100000) if score.is_cp() else None,
            "score_mate": score.white().mate() if score.is_mate() else None
        })

    return {
        "fen": fen,
        "depth": depth,
        "lines": lines,
        "results": lines_out
    }


@app.get("/")
def root():
    return {"status": "Stockfish Wrapper Online"}


if __name__ == "__main__":
    uvicorn.run("stockfish:app", host="0.0.0.0", port=8000)
