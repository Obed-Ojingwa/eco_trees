# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel




app = FastAPI()


# 1. Configure CORS origins (React's default Vite port is 5173)
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],
)

# 2. Define data schemas (matches TypeScript interfaces)
class MessageResponse(BaseModel):
    message: str
    status: str

# 3. Create endpoints
@app.get("/api/data", response_model=MessageResponse)
async def get_data():
    return {"message": "Hello from the FastAPI backend!", "status": "success"}
