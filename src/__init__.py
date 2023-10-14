from fastapi import FastAPI

app = FastAPI()

# 載入 API (遷移至新 API)
from .api import *


@app.get("/")
def home():
    return {"message": "Hello World!"}


@app.get("/ping")
def ping():
    return {"message": "pong"}
