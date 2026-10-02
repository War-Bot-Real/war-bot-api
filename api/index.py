from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.controllers.game import router as gameRouter
from api.controllers.admin import router as adminRouter

app = FastAPI(title="War Bot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://war-bot-web.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(gameRouter)
app.include_router(adminRouter)