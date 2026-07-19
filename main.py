# ==========================================
# 1. IMPORTING TOOLS (Getting our toolbox ready)
# ==========================================
import logging      # Works like the server's "diary" or black box. It records everything that happens (error messages, completed tasks) so you can review it later.
import uuid         # Generates universally unique identifiers (random alphanumeric codes that never repeat). It acts like a unique "ticket" for each user.
import asyncio      # Allows the server to multitask. It prevents the server from "freezing" while it processes heavy video files.
from typing import Dict, Any, Optional # Helps us label the exact type of data we are working with (e.g., dictionaries, text). This prevents code errors.

# Importing tools specifically from the FastAPI library:
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
# FastAPI: The main engine, the framework that builds the web server.
# HTTPException: A tool to send official error messages to the user (e.g., "Error 404 Not Found" or "Error 500").

from fastapi.middleware.cors import CORSMiddleware
# CORS: The security guard at the front door. Browsers block connections from other websites by default. CORS decides which websites (like your React frontend) are allowed to talk to this server.

from pydantic import BaseModel, Field
# Pydantic: The "bouncers" at the club. They check that the information the user sends has the exact shape and data we demand before letting it in.

from dotenv import load_dotenv
# This tool reads a hidden file called '.env' so the server can find secret passwords (like your OpenAI API key) without exposing them in public code.

# --- Your AI scripts (The brain of the app) ---
from utils.audio_processor import process_input
from core.transcriber import transcribe_all
from core.summarizer import summarize, generate_title
from core.extractor import extract_action_items, extract_key_decisions, extract_questions
from core.rag_engine import build_rag_chain, ask_question

# ==========================================
# 2. SETUP (Turning things on and configuring)
# ==========================================

# Turn on the tool that loads your secret passwords from the .env file into memory
load_dotenv()

# Set up our "diary" (logger) so we can see what the server is doing in the command terminal
logging.basicConfig(
    level=logging.INFO, # Tell it to log standard info, not just critical emergencies.
    format="%(asctime)s [%(levelname)s] %(message)s", # Diary format: Shows Date/Time, Message Type (Info/Error), and the Message itself.
    handlers=[logging.StreamHandler()] # Print this diary directly on your terminal screen.
)
logger = logging.getLogger("VideoAssistantAPI") # Give our diary writer a name

# Create the actual web server and name it "app"
app = FastAPI(
    title="AI Video Assistant API", 
    description="API for transcribing, summarizing, and chatting with video/audio content.",
    version="1.0.0"
)

# Tell the security guard (CORS) to let your frontend (e.g., React) talk to this backend (Python)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # The "*" means "allow ANY website to connect". (In the real world, you'd put only your React URL here for security).
    allow_credentials=True, # Allows cookies or passwords to be sent.
    allow_methods=["*"], # Allows any type of request (GET to ask for data, POST to send, DELETE to remove, etc.).
    allow_headers=["*"], # Allows any type of hidden header in the request.
)

# ==========================================
# 3. SERVER MEMORY (Remembering the user)
# ==========================================

# A simple dictionary. Think of this like a wall of lockers at a gym.
# We will store the AI "chat bots" (RAG chains) for each user here so they can chat with their specific video later.
ACTIVE_SESSIONS: Dict[str, Any] = {}


# ==========================================
# 4. THE BOUNCERS (Validating user data)
# ==========================================

# When a user asks to process a video, they MUST send data that exactly matches these rules:
class ProcessRequest(BaseModel):
    source: str = Field(..., description="YouTube URL or local file path") # It's mandatory to send text called "source" (the URL or file).
    language: str = Field(default="english", description="Language of the audio") # If they forget to send the language, we assume it's English by default.

# When the server finishes processing, it solemnly swears to return the data in exactly this structure:
class ProcessResponse(BaseModel):
    session_id: str
    title: str
    transcript_preview: str
    summary: str
    action_items: Any
    key_decisions: Any
    open_questions: Any

# When a user wants to send a chat message, they MUST send data shaped like this:
class ChatRequest(BaseModel):
    session_id: str = Field(..., description="The ID ticket we gave them earlier") # The locker ticket/key we gave them earlier.
    question: str = Field(..., description="The text of their question") # The actual text of the question they are asking the AI.

# When the server replies in the chat, it will send this:
class ChatResponse(BaseModel):
    answer: str


# ==========================================
# 5. THE HEAVY LIFTER (Running your AI code)
# ==========================================

# This function is the orchestra conductor. It runs all your code step by step.
def run_pipeline_sync(source: str, language: str) -> dict:
    try: # "Try to do all this, but if something fails, don't crash the whole server, just let me know"
        logger.info(f"Processing source: {source}") # Write in the diary which video is being processed
        chunks = process_input(source) # Cut the audio/video using your code

        logger.info("Transcribing audio...")
        transcript = transcribe_all(chunks, language) # Transcribe the audio to text using your code
        
        logger.info("Generating insights...")
        title = generate_title(transcript) # Generate the title
        summary = summarize(transcript) # Generate the summary
        action_items = extract_action_items(transcript) # Extract tasks
        decisions = extract_key_decisions(transcript) # Extract decisions
        questions = extract_questions(transcript) # Extract questions
        
        logger.info("Building RAG chain...")
        rag_chain = build_rag_chain(transcript) # Build the chat brain (RAG) so it can answer questions based on the text

        # Package all the finished answers into a dictionary and return them to the server
        return {
            "title": title,
            "transcript": transcript,
            "summary": summary,
            "action_items": action_items,
            "key_decisions": decisions,
            "open_questions": questions,
            "rag_chain": rag_chain,
        }
    except Exception as e: # If ANY line of code above fails (e.g., internet drops, corrupt video)...
        logger.error(f"Pipeline failure: {str(e)}") # Write the exact error in the diary
        raise RuntimeError(f"Pipeline processing failed: {str(e)}") # Shout the error so the Endpoint knows


# ==========================================
# 6. THE DOORS (API Endpoints / URLs)
# ==========================================

# DOOR 1: A simple health check to see if the server is awake.
# When someone goes to "http://127.0.0.1:8000/health" in their browser...
@app.get("/health", tags=["System"])
async def health_check():
    # ...we simply reply with this message to confirm everything is fine and say how many active chats there are.
    return {"status": "healthy", "active_sessions": len(ACTIVE_SESSIONS)}


# DOOR 2: The main door to send and process a video.
# When the frontend sends video data to "http://127.0.0.1:8000/api/v1/process"...
@app.post("/api/v1/process", response_model=ProcessResponse, tags=["Processing"])
async def process_video(request: ProcessRequest):
    try:
        # Pure magic here! Since AI processing takes minutes, we send it to a background "thread" (asyncio.to_thread).
        # This way, the main server stays free to help other users while waiting for the heavy lifter to finish.
        result = await asyncio.to_thread(run_pipeline_sync, request.source, request.language)
        
        # We generate a completely random and unique alphanumeric text string (e.g., "f47ac10b-58cc...")
        session_id = str(uuid.uuid4())
        
        # We save this video's specific "Chat Bot" (RAG) in our locker dictionary, using the random text as the key.
        ACTIVE_SESSIONS[session_id] = result["rag_chain"]
        logger.info(f"Session created: {session_id}")

        # We send all the generated summaries back to the frontend (React) and, very importantly, the locker key (session_id).
        return ProcessResponse(
            session_id=session_id,
            title=result["title"],
            transcript_preview=result["transcript"][:300] + "...", # We only send the first 300 characters so we don't clutter the screen.
            summary=result["summary"],
            action_items=result["action_items"],
            key_decisions=result["key_decisions"],
            open_questions=result["open_questions"]
        )

    # If the "heavy lifter" function above shouted that there was an error...
    except RuntimeError as e:
        # ...We officially tell the user their request failed by sending a 500 Error
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e: # For any other weird, unknown error
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred during processing.")


# DOOR 3: The Chat Door.
# When the React frontend sends a chat message to "http://127.0.0.1:8000/api/v1/chat"...
@app.post("/api/v1/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_with_meeting(request: ChatRequest):
    
    # 1. We check our wall of lockers to see if the key the user sent (session_id) actually exists
    rag_chain = ACTIVE_SESSIONS.get(request.session_id)
    
    # If the locker is empty or the key doesn't exist (maybe the server restarted)...
    if not rag_chain:
        # We tell them Error 404 (Not found)
        raise HTTPException(
            status_code=404, 
            detail="Session not found or expired. Please process the video again."
        )

    try:
        # 2. We ask the AI model the user's question. (Again, we use asyncio so we don't freeze the server while the AI "thinks" of the answer)
        logger.info(f"Answering question for session {request.session_id}")
        answer = await asyncio.to_thread(ask_question, rag_chain, request.question)
        
        # 3. We send the AI's text answer back to the user's screen in React
        return ChatResponse(answer=answer)
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate an answer.")


# DOOR 4: The Cleanup Door.
# AI models take up a lot of RAM. When a user closes the webpage, we need them to let us know so we can delete their data.
@app.delete("/api/v1/sessions/{session_id}", tags=["System"])
async def end_session(session_id: str):
    
    # If the user's key matches a valid locker in our memory...
    if session_id in ACTIVE_SESSIONS:
        # ...We use 'del' to delete the contents of that locker and free up space in the computer's RAM.
        del ACTIVE_SESSIONS[session_id]
        logger.info(f"Session deleted: {session_id}")
        return {"status": "success", "message": f"Session {session_id} deleted."}
    
    # If for some reason they try to delete a locker that doesn't exist...
    raise HTTPException(status_code=404, detail="Session not found.")