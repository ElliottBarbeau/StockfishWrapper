import subprocess
import chess
import time
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

def run_stockfish_command(commands, timeout=2.0):
    p = subprocess.Popen(
        [STOCKFISH_PATH],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    for cmd in commands:
        p.stdin.write(cmd + "\n")
    p.stdin.flush()

    result_lines = []
    start = time.time()

    while True:
        line = p.stdout.readline().strip()
        if line:
            result_lines.append(line)
        if "bestmove" in line:
            break
        if time.time() - start > timeout:
            break

    p.kill()
    return result_lines


def analyse_fen(fen, depth, lines):
    commands = [
        "uci",
        "setoption name MultiPV value " + str(lines),
        "position fen " + fen,
        "go depth " + str(depth)
    ]

    output = run_stockfish_command(commands, timeout=5)

    pvs = []
    for line in output:
        if " multipv " in line and " pv " in line:
            parts = line.split(" pv ")
            moves = parts[1].split()
            score = None
            if " score cp " in line:
                score = int(line.split(" score cp ")[1].split()[0])
            elif " score mate " in line:
                score = "mate " + line.split(" score mate ")[1].split()[0]

            pvs.append({
                "moves": moves,
                "score": score
            })

    return pvs


@app.post("/eval")
async def eval_post(request: Request):
    data = await request.json()
    fen = data["fen"]
    depth = int(data.get("depth", 14))
    lines = int(data.get("lines", 3))

    result = analyse_fen(fen, depth, lines)

    return {
        "fen": fen,
        "depth": depth,
        "lines": lines,
        "results": result
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("stockfish:app", host="0.0.0.0", port=8000)
