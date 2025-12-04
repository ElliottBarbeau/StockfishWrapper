from fastapi import FastAPI, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi.responses import JSONResponse

import chess
import chess.engine
import uvicorn

import subprocess

limiter = Limiter(key_func=get_remote_address)

app = FastAPI()
app.state.limiter = limiter


ENGINE_PATH = "/usr/games/stockfish"

def load_engine():
    """Load Stockfish safely with 1 thread + small memory footprint."""
    return chess.engine.SimpleEngine.popen_uci(
        ENGINE_PATH,
        options={
            "Threads": 1,
            "Hash": 32
        }
    )

engine = load_engine()  # initial engine load

class EvalRequest(BaseModel):
    fen: str
    lines: int = 1
    depth: int = 16

def restart_engine():
    global engine
    try:
        engine.quit()
    except:
        pass
    engine = load_engine()

@app.post("/eval")
@limiter.limit("20/minute")
async def evaluate(request: Request, data: EvalRequest):

    fen = data.fen
    depth = min(data.depth, 18)   # prevent memory spikes
    lines = min(data.lines, 2)    # multipv=3 causes instability on small VMs

    board = chess.Board(fen)

    try:
        info = engine.analyse(
            board,
            chess.engine.Limit(depth=depth),
            multipv=lines
        )
    except chess.engine.EngineTerminatedError:
        # Stockfish crashed — automatically restart safely
        restart_engine()
        return JSONResponse(
            status_code=500,
            content={"error": "Engine crashed and was restarted."}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

    lines_out = []
    for entry in info:
        move_list = [m.uci() for m in entry.get("pv", [])]

        lines_out.append({
            "score_cp": entry["score"].white().score(mate_score=100000)
                if entry["score"].is_cp()
                else None,
            "score_mate": entry["score"].white().mate()
                if entry["score"].is_mate()
                else None,
            "pv_uci": move_list,
            "best_move_uci": move_list[0] if move_list else None
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
