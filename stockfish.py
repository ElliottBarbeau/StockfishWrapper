import subprocess
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

def run_engine(commands, timeout=3.0):
    p = subprocess.Popen(
        [STOCKFISH_PATH],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )

    def send(cmd):
        p.stdin.write(cmd + "\n")
        p.stdin.flush()

    lines = []

    send("uci")
    start = time.time()
    while True:
        line = p.stdout.readline().strip()
        if "uciok" in line:
            break
        if time.time() - start > timeout:
            p.kill()
            return None
        if line:
            lines.append(line)

    send("isready")
    start = time.time()
    while True:
        line = p.stdout.readline().strip()
        if "readyok" in line:
            break
        if time.time() - start > timeout:
            p.kill()
            return None

    for c in commands:
        send(c)

    start = time.time()
    output = []
    while True:
        line = p.stdout.readline().strip()
        if line:
            output.append(line)
        if "bestmove" in line:
            break
        if time.time() - start > timeout:
            break

    p.kill()
    return output


def analyse_fen(fen, depth, lines):
    cmds = [
        f"setoption name MultiPV value {lines}",
        f"position fen {fen}",
        f"go depth {depth}"
    ]

    output = run_engine(cmds, timeout=6.0)
    if not output:
        return {"error": "Engine did not respond"}

    results = []
    for line in output:
        if "multipv" in line and " pv " in line:
            parts = line.split(" pv ")
            moves = parts[1].split()

            score = None
            if " score cp " in line:
                score = int(line.split(" score cp ")[1].split()[0])
            elif " score mate " in line:
                score = "mate " + line.split(" score mate ")[1].split()[0]

            results.append({
                "moves": moves,
                "score": score
            })

    return {"pv": results}


@app.post("/eval")
async def eval_post(request: Request):
    data = await request.json()
    fen = data["fen"]
    depth = int(data.get("depth", 14))
    lines = int(data.get("lines", 3))

    return analyse_fen(fen, depth, lines)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("stockfish:app", host="0.0.0.0", port=8000)
