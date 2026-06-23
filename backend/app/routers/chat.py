from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.agent.loop import run_agent

router = APIRouter()


class ChatRequest(BaseModel):
    conversation_id: str
    message: str


@router.post("/chat")
async def chat(req: ChatRequest):
    return StreamingResponse(
        run_agent(req.conversation_id, req.message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
