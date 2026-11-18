from fastapi import FastAPI

from . import activities, ardi, auth, points

app = FastAPI(title="Wallnut", version="0.1.0")

for module in (auth, activities, points, ardi):
    app.include_router(module.router, prefix="/v1")


@app.get("/health")
def health():
    return {"status": "ok"}

