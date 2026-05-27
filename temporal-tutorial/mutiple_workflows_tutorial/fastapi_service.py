import uvicorn
from fastapi import FastAPI

app = FastAPI()

@app.get("/greet")
async def greeting_api(name: str) -> str:
    return f"Hello {name}"

@app.get("/farewell")
async def farewell_api(name: str) -> str:
    return f"Bye {name}"

if __name__ == "__main__":
    uvicorn.run(
        "fastapi_service:app",
        host="localhost",
        port=9999,
        reload=True
    )