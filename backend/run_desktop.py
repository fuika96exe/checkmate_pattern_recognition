"""Start the API server from the packaged desktop application."""

import uvicorn

from app.main import app


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
