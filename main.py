from fastapi import FastAPI
from routers.predict import predict_router
import uvicorn

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello world!"}


app.include_router(predict_router, prefix="/predict")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
