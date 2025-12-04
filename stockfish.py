from fastapi import FastAPI, HTTPException
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
engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)


@app.get("/eval")
@limiter.limit("20/minute")
async def evaluate(fen: str, lines: int = 3, depth: int = 20):
    try:
        board = chess.Board(fen)
    except:
        raise HTTPException(status_code=400, detail="Invalid FEN")

    info = engine.analyse(board, chess.engine.Limit(depth=depth), multipv=lines)

    results = []

    for pv in info:
        uci_moves = [m.uci() for m in pv["pv"]]

        # Convert UCI → SAN
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

