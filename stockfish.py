import chess
import chess.engine
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

STOCKFISH_PATH = "/usr/games/stockfish"

app = FastAPI()

class EvalRequest(BaseModel):
    fen: str
    depth: int = 15
    lines: int = 3

@app.post("/eval")
async def eval_post(req: EvalRequest):

    try:
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
            moves_san = []
            temp_board = board.copy()

            for move in pv["pv"]:
                moves_san.append(temp_board.san(move))
                temp_board.push(move)

            score = None
            if pv["score"].is_mate():
                score = f"mate {pv['score'].mate()}"
            else:
                score = pv["score"].pov(board.turn).score()

            results.append({
                "score": score,
                "pv_san": moves_san
            })

        return {"results": results}

    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run("stockfish:app", host="0.0.0.0", port=8000)
