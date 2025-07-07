from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any
from agent.agent import CalendarBookingAgent
import uvicorn

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Calendar Booking AI Assistant Backend",
    description="Handles chat interactions and calendar operations.",
    version="1.0.0",
)

# --- Pydantic Models for API ---
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, Any]]

class ChatResponse(BaseModel):
    response: str

# --- Agent Initialization ---
# We create the agent once when the server starts
booking_agent = CalendarBookingAgent()

# --- API Endpoints ---

@app.get("/", tags=["Status"])
def read_root():
    """Root endpoint to check if the server is running."""
    return {"status": "Backend is running"}

@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_with_agent(request: ChatRequest):
    """
    Endpoint to handle chat messages from the frontend.
    It receives the user's message and chat history,
    gets a response from the Langchain agent, and returns it.
    """
    print(f"Received message: {request.message}")
    print(f"Chat history: {request.history}")

    # Format history for the agent (simplified since new agent handles this better)
    formatted_history = []
    for msg in request.history:
        if msg['role'] == 'user':
            formatted_history.append(f"Human: {msg['content']}")
        elif msg['role'] == 'assistant':
            formatted_history.append(f"AI: {msg['content']}")

    # Get response from the agent using the new method
    agent_response = booking_agent.process_user_request(
        user_input=request.message,
        chat_history=formatted_history
    )

    print(f"Agent response: {agent_response}")
    return ChatResponse(response=agent_response)

@app.get("/health", tags=["Status"])
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "agent_status": "ready"}

@app.get("/agent-status", tags=["Status"])
def get_agent_status():
    """Get the current status of the booking agent."""
    return {
        "agent_ready": True,
        "conversation_state": {
            "has_pending_booking": booking_agent.conversation_state.get("pending_booking") is not None,
            "waiting_for_confirmation": booking_agent.conversation_state.get("waiting_for_confirmation", False),
            "waiting_for_title": booking_agent.conversation_state.get("waiting_for_title", False)
        },
        "current_date": booking_agent.get_current_date()
    }

@app.post("/reset-agent", tags=["Agent"])
def reset_agent():
    """Reset the agent's conversation state."""
    booking_agent.conversation_state = {
        "pending_booking": None,
        "waiting_for_confirmation": False,
        "waiting_for_title": False
    }
    return {"status": "Agent state reset successfully"}

# --- CORS middleware (if needed for frontend) ---
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Main execution ---
if __name__ == "__main__":
    # This allows running the backend directly for testing
    # Use `uvicorn backend.main:app --reload` for development
    uvicorn.run(app, host="0.0.0.0", port=8000)