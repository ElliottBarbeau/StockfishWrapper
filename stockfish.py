from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import chess
import chess.engine

STOCKFISH_PATH = "/usr/games/stockfish"

app = FastAPI()

class EvalRequest(BaseModel):
    fen: str
    depth: int = 15
    lines: int = 3

@app.post("/eval")
async def eval_position(req: EvalRequest):
    try:
        # Start Stockfish fresh for each request
        engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)

        board = chess.Board(req.fen)

        info = engine.analyse(
            board,
            chess.engine.Limit(depth=req.depth),
            multipv=req.lines
        )

        engine.quit()

        results = []
        for pv in info:
            pv_moves = [move.uci() for move in pv["pv"]]

            if pv["score"].is_mate():
                score = f"mate {pv['score'].mate()}"
            else:
                score = pv["score"].pov(board.turn).score()

            results.append({
                "pv": pv_moves,
                "score": score
            })

        return {"results": results}

    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run("stockfish:app", host="0.0.0.0", port=8000)
