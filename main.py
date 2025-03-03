import os

import uvicorn
from dotenv import load_dotenv

from scripts.ssl.generate_ssl import generate_certificate

load_dotenv()

if __name__ == "__main__":
    if os.getenv("DEV_MODE") == "True":
        # Development
        uvicorn.run(
            app="src:app",
            host="0.0.0.0",
            port=int(os.getenv("PORT", 5000)),
            log_level="debug",
            reload=True,  # reload the server every time code changes
        )
    else:
        # Production
        ssl_path = "scripts/ssl/"
        generate_certificate(path=ssl_path)
        ssl_keyfile = ssl_path + "key.pem"
        ssl_certfile = ssl_path + "cert.pem"
        uvicorn.run(
            app="src:app",
            host="0.0.0.0",
            port=int(os.getenv("PORT", 5000)),
            log_level="error",
            workers=2,
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile,
        )
