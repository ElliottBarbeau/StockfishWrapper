import chess
import chess.engine
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time

STOCKFISH_PATH = "/usr/games/stockfish"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def analyse_fen(fen: str, depth: int, lines: int):
    try:
        # Create a NEW engine for every request
        engine = chess.engine.SimpleEngine.popen_uci(
            STOCKFISH_PATH,
            use_pty=True  # CRITICAL FOR NEW STOCKFISH BUILDS
        )
    except Exception as e:
        return {"error": f"Engine failed to start: {e}"}

    board = chess.Board(fen)

    try:
        analysis = engine.analyse(
            board,
            chess.engine.Limit(depth=depth),
            multipv=lines
        )
    except Exception as e:
        engine.quit()
        return {"error": f"Engine crashed: {e}"}

    engine.quit()

    # Parse PV results
    results = []
    for entry in analysis:
        score = None
        if entry["score"].cp is not None:
            score = entry["score"].cp
        elif entry["score"].mate is not None:
            score = f"mate {entry['score'].mate}"

        pv_moves = [m.uci() for m in entry.get("pv", [])]

        results.append({
            "score": score,
            "pv": pv_moves
        })

    return {"results": results}


@app.post("/eval")
async def eval_post(request: Request):
    data = await request.json()
    fen = data["fen"]
    depth = int(data.get("depth", 15))
    lines = int(data.get("lines", 3))

    return analyse_fen(fen, depth, lines)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("stockfish:app", host="0.0.0.0", port=8000)
