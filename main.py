import os

import uvicorn
from dotenv import load_dotenv

load_dotenv()

PORT = int(os.getenv("PORT", 5000))

if __name__ == "__main__":
    if os.getenv("DEV_MODE") == "True":
        # Development
        uvicorn.run(
            app="src:app",
            host="0.0.0.0",
            port=PORT,
            log_level="debug",
            reload=True,  # reload the server every time code changes
        )
    else:
        # Production
        uvicorn.run(
            app="src:app",
            host="0.0.0.0",
            port=PORT,
            log_level="error",
            workers=2,
        )
