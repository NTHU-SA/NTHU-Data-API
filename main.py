import os
import uvicorn
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    ssl_path = "src/utils/openssl/"
    if os.getenv("ENV") == "development":
        # Development
        # Run the server
        uvicorn.run(
            "src:app",
            host="0.0.0.0",
            port=int(os.getenv("PORT") or 5000),
            log_level="debug",
            reload=True,  #  reload the server every time code changes
            ssl_keyfile="src/utils/openssl/key.pem",
            ssl_certfile="src/utils/openssl/cert.pem",
        )
    else:
        # Production
        # Run the server
        uvicorn.run(
            "src:app",
            host="0.0.0.0",
            port=int(os.getenv("PORT") or 5000),
            log_level="error",
            workers=2,
            ssl_keyfile="src/utils/openssl/key.pem",
            ssl_certfile="src/utils/openssl/cert.pem",
        )
