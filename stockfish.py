from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import chess
import chess.engine

app = FastAPI()

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request, exc):
    return PlainTextResponse("Rate limit exceeded", status_code=429)


STOCKFISH_PATH = "/usr/games/stockfish"
engine = chess.engine.SimpleEngine.popen_uci(
    "/usr/games/stockfish",
    options={
        "Threads": 1,
        "Hash": 32
    }
)

@app.get("/eval")
@limiter.limit("20/minute")
async def evaluate(request: Request, fen: str, lines: int = 1, depth: int = 18):
    board = chess.Board(fen)

    # safety: avoid OOM
    safe_lines = min(lines, 2)
    safe_depth = min(depth, 18)

    info = engine.analyse(
        board,
        chess.engine.Limit(depth=safe_depth),
        multipv=safe_lines
    )

    results = []
    for pv in info:
        uci_moves = [m.uci() for m in pv["pv"]]

        san_moves = []
        tmp = board.copy()
        for move in pv["pv"]:
            san_moves.append(tmp.san(move))
            tmp.push(move)

        score = pv["score"].white()

        results.append({
            "uci": uci_moves,
            "san": san_moves,
            "cp": score.score(mate_score=99999),
            "mate": score.mate()
        })

    return {
        "fen": fen,
        "lines": lines,
        "depth": depth,
        "results": results
    }




