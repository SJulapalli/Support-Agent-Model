from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import chat, admin

app = FastAPI(title="NorthShop Support Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api")
app.include_router(admin.router, prefix="/admin/api")


@app.get("/health")
async def health():
    return {"status": "ok"}
