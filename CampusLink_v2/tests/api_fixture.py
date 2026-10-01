"""Run the existing app for browser tests; stop cooperatively via a sentinel file."""
import sys
import threading
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"backend"))
import uvicorn
from app.database import engine

stop_file=Path(sys.argv[1])
server=uvicorn.Server(uvicorn.Config("app.main:app",host="127.0.0.1",port=int(sys.argv[2]),log_level="warning"))
finished=threading.Event()
def watch():
    while not finished.wait(0.1):
        if stop_file.exists():
            server.should_exit=True
            return
threading.Thread(target=watch,daemon=True).start()
try:
    server.run()
finally:
    finished.set()
    engine.dispose()
