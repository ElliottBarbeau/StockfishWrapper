import pexpect
from fastapi import FastAPI, Request
from pydantic import BaseModel
import uvicorn

STOCKFISH_PATH = "/usr/games/stockfish"

app = FastAPI()

class EvalRequest(BaseModel):
    fen: str
    depth: int = 15
    lines: int = 3

def run_stockfish_uci(fen: str, depth: int, lines: int):
    try:
        engine = pexpect.spawn(STOCKFISH_PATH, encoding="utf-8", timeout=5)

        engine.sendline("uci")
        engine.expect("uciok")

        engine.sendline("isready")
        engine.expect("readyok")

        engine.sendline(f"setoption name MultiPV value {lines}")

        engine.sendline(f"position fen {fen}")

        engine.sendline(f"go depth {depth}")

        engine.expect("bestmove")
        output = engine.before

        engine.close()

        pvs = []

        for line in output.split("\n"):
            line = line.strip()
            if "multipv" in line and " pv " in line:
                parts = line.split(" pv ")
                moves = parts[1].split()

                score = None
                if "score cp" in line:
                    score = int(line.split("score cp")[1].split()[1])
                elif "score mate" in line:
                    score = "mate " + line.split("score mate")[1].split()[1]

                pvs.append({
                    "moves": moves,
                    "score": score
                })

        return {"pv": pvs}

    except Exception as e:
        return {"error": str(e)}

@app.post("/eval")
async def eval_post(req: EvalRequest):
    return run_stockfish_uci(req.fen, req.depth, req.lines)

if __name__ == "__main__":
    uvicorn.run("stockfish:app", host="0.0.0.0", port=8000)
