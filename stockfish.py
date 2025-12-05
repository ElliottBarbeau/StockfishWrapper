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
    board = chess.Board(req.fen)

    try:
        # Start engine fresh each request
        engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)

        info_list = engine.analyse(
            board,
            chess.engine.Limit(depth=req.depth),
            multipv=req.lines
        )

        engine.quit()

        results = []

        for info in info_list:
            score_obj = info["score"].pov(board.turn)

            # Score normalization
            if score_obj.is_mate():
                score = f"M{score_obj.mate()}"
            else:
                score = score_obj.score()  # centipawns

            pv_moves = [m.uci() for m in info["pv"]]

            results.append({
                "pv": pv_moves,
                "score": score
            })

        return {"results": results}

    except Exception as e:
        return {"error": f"Engine failure: {e}"}


if __name__ == "__main__":
    uvicorn.run("stockfish:app", host="0.0.0.0", port=8000)
