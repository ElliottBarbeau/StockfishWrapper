import pexpect
import chess
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

def run_stockfish_uci(fen: str, depth: int, lines: int):
    engine = pexpect.spawn(STOCKFISH_PATH, encoding='utf-8', timeout=5)

    engine.expect("uci")
    engine.sendline("uci")
    engine.expect("uciok")

    engine.sendline("isready")
    engine.expect("readyok")

    engine.sendline(f"setoption name MultiPV value {lines}")
    engine.sendline(f"position fen {fen}")
    engine.sendline(f"go depth {depth}")

    output = ""
    try:
        engine.expect("bestmove")
        output = engine.before
    except Exception as e:
        engine.close()
        return {"error": f"Engine timeout or crash: {e}"}

    engine.close()

    pvs = []
    for line in output.split("\n"):
        line = line.strip()
        if "multipv" in line and " pv " in line:
            parts = line.split(" pv ")
            moves = parts[1].split()

            if "score cp" in line:
                score = int(line.split("score cp")[1].split()[1])
            elif "score mate" in line:
                score = "mate " + line.split("score mate")[1].split()[1]
            else:
                score = None

            pvs.append({"moves": moves, "score": score})

    return {"pv": pvs}


@app.post("/eval")
async def eval_post(request: Request):
    data = await request.json()
    fen = data["fen"]
    depth = int(data.get("depth", 14))
    lines = int(data.get("lines", 3))

    return run_stockfish_uci(fen, depth, lines)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("stockfish:app", host="0.0.0.0", port=8000)
