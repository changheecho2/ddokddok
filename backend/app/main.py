from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import members, journals, meetings, band, deposit, refresh, notify

app = FastAPI(title="똑똑 디파짓 관리 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "https://changheecho2.github.io"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(members.router)
app.include_router(journals.router)
app.include_router(meetings.router)
app.include_router(band.router)
app.include_router(deposit.router)
app.include_router(refresh.router)
app.include_router(notify.router)


@app.get("/")
def root():
    return {"message": "ddokddok API is running"}
