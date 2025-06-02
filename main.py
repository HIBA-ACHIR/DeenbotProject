from fastapi import FastAPI, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
import os
import logging
from api.v1.moufti_routes import router as moufti_router
from api.v1.media_routes import router as media_router
from api.v1.youtube_routes import router as youtube_router
from api.v1.chat_routes import router as chat_router
from dependencies.fatwallm_rag import ask_question_with_video_auto

# Import database and models for initialization
from database import engine, Base
from models.conversation import Conversation
from models.message import Message

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app with increased limits for file uploads
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
import uvicorn

# Increase file size limit to 1GB
app = FastAPI(
    title="DeenBot API",
    # Increase maximum upload size for large audio files
    docs_url=None,  # Disable docs for production
    redoc_url=None  # Disable redoc for production
)

# Configure upload directory
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Configure maximum request body size for file uploads (increase from default 1MB to 1GB)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class LargeRequestMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Increase the maximum size limit for the request body
        # Default is around 1MB, we're setting it to 1GB for large audio files
        request._body_size_limit = 1024 * 1024 * 1024  # 1GB
        response = await call_next(request)
        return response

# Add the custom middleware for large requests FIRST
app.add_middleware(LargeRequestMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://localhost:8081",
        "http://localhost:8082",  # Add the current Vite dev server port
        "http://localhost:5173",  # Vite default port
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8081",
        "http://127.0.0.1:8082",  # Add the current Vite dev server port
        "http://127.0.0.1:5173",  # Vite default port
        "http://192.168.56.1:8080",
        "http://192.168.56.1:8081",
        "http://192.168.56.1:8082",  # Add the current Vite dev server port
        "http://192.168.56.1:5173",  # Vite default port
        "http://192.168.184.25:8080",
        "http://192.168.184.25:8081",
        "http://192.168.184.25:8082",  # Add the current Vite dev server port
        "http://192.168.184.25:5173",  # Vite default port
        "http://192.168.100.63:8080",  # Votre adresse IP
        "http://192.168.100.63:8081",  # Votre adresse IP
        "http://192.168.100.63:8082",  # Votre adresse IP
        "http://192.168.100.63:5173",  # Votre adresse IP avec le port Vite par défaut
        "*"  # Allow all origins for development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "X-Requested-With", "Accept", "Authorization", "Origin"]
)

# Mount static files
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Include routers
app.include_router(moufti_router)
app.include_router(media_router)
app.include_router(youtube_router, prefix="/api/youtube")
app.include_router(chat_router)

# Startup event to create database tables if they don't exist
@app.on_event("startup")
async def startup_db_client():
    """Create database tables on startup if they don't exist."""
    try:
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")

# Add direct fatwaask endpoint for backward compatibility
@app.post("/fatwaask")
async def fatwaask_endpoint(
    request: Request,
    question: str = Body(...),
    video_id: str = Body(...)
):
    """
    Process a fatwa question and return an answer.
    Direct endpoint for backward compatibility with frontend.
    """
    try:
        # Log the incoming request
        logger.info(f"Received question: {question}")
        logger.info("simplified_main:Received question: {0}".format(question))
        
        # Call the question answering function
        answer = ask_question_with_video_auto(question)
        
        # Log the answer for debugging
        logger.info(f"Generated answer (first 1000 chars): {answer[:100] if answer else 'None'}")
        
        # Make sure we return a valid answer
        if not answer or len(answer.strip()) < 5:
            answer = "عذراً، لم أتمكن من الإجابة على سؤالك. يرجى إعادة صياغة السؤال أو طرح سؤال آخر."
            
        return {"answer": answer}
    except Exception as e:
        # Log the full error
        logger.error(f"Error in fatwaask_endpoint: {str(e)}")
        
        # Return a friendly error message
        return {"answer": "عذراً، حدث خطأ أثناء معالجة سؤالك. يرجى المحاولة مرة أخرى بعد قليل."}

# Custom middleware for proper UTF-8 encoding of Arabic text responses
@app.middleware("http")
async def arabic_encoding_middleware(request, call_next):
    response = await call_next(request)
    # Only process non-streaming responses
    if not isinstance(response, StreamingResponse):
        # If the response has a .body attribute, re-encode it
        if hasattr(response, 'body') and response.body:
            try:
                body = response.body.decode('utf-8') if isinstance(response.body, bytes) else response.body
                response = Response(content=body, media_type="application/json; charset=utf-8")
            except Exception as e:
                logger.error(f"Encoding middleware error: {e}")
    return response

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to DeenBot API", "status": "running"}

if __name__ == "__main__":
    import uvicorn
    # Configure Uvicorn with increased limits for file uploads
    # Default limit is 1MB, we're increasing it to handle large audio files (up to 1GB)
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8006, 
        reload=True,
        limit_concurrency=10,
        limit_max_requests=10,
        timeout_keep_alive=120,
        # These settings help with large file uploads
        h11_max_incomplete_event_size=1024*1024*1024  # 1GB max request size
    )