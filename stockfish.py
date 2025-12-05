from fastapi import FastAPI, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi.responses import JSONResponse
import uvicorn
import chess
import chess.engine
import asyncio
import traceback

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter

ENGINE_PATH = "/usr/games/stockfish"

def load_engine():
    engine = chess.engine.SimpleEngine.popen_uci(ENGINE_PATH)
    try:
        engine.configure({"Threads": 1, "Hash": 32})
    except:
        pass
    return engine

engine = load_engine()

def restart_engine():
    global engine
    try:
        engine.quit()
    except:
        pass
    engine = load_engine()

async def run_analyse(board, depth, lines):
    loop = asyncio.get_running_loop()
    def _analyse():
        try:
            return engine.analyse(
                board,
                chess.engine.Limit(depth=depth),
                multipv=lines
            )
        except Exception as e:
            print("ANALYSE ERROR:")
            traceback.print_exc()
            raise e
    return await loop.run_in_executor(None, _analyse)

class EvalRequest(BaseModel):
    fen: str
    lines: int = 1
    depth: int = 14

@app.post("/eval")
@limiter.limit("30/minute")
async def evaluate_post(request: Request, data: EvalRequest):
    fen = data.fen
    depth = min(data.depth, 18)
    lines = min(data.lines, 3)
    board = chess.Board(fen)

    try:
        info = await run_analyse(board, depth, lines)
    except chess.engine.EngineTerminatedError:
        restart_engine()
        return JSONResponse(status_code=500, content={"error": "Stockfish crashed and was restarted."})
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e), "type": str(type(e))})

    results = []
    for entry in info:
        pv = [m.uci() for m in entry.get("pv", [])]
        score = entry["score"]
        results.append({
            "best_move_uci": pv[0] if pv else None,
            "pv_uci": pv,
            "score_cp": score.white().score(mate_score=100000) if score.is_cp() else None,
            "score_mate": score.white().mate() if score.is_mate() else None
        })

    return {"fen": fen, "depth": depth, "lines": lines, "results": results}

@app.get("/eval")
async def evaluate_get(request: Request, fen: str, lines: int = 1, depth: int = 12):
    data = EvalRequest(fen=fen, lines=lines, depth=depth)
    return await evaluate_post(request, data)

@app.get("/")
def root():
    return {"status": "Stockfish API is running"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
