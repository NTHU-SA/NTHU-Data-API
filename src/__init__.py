from fastapi import FastAPI

app = FastAPI()

# 載入 API (遷移至新 API)
from .api import *


@app.get(
    "/",
    responses={
        200: {
            "description": "測試 API 是否正常運作",
            "content": {
                "application/json": {"example": {"message": "Hello World!"}},
            },
        },
    },
)
def home():
    return {"message": "Hello World!"}


@app.get(
    "/ping",
    responses={
        200: {
            "description": "測試 API 是否正常運作",
            "content": {
                "application/json": {"example": {"message": "pong"}},
            },
        },
    },
)
def ping():
    return {"message": "pong"}
