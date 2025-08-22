import os
import logging
from fastapi import FastAPI, Request, Form, HTTPException, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer
from groq import Groq
from dotenv import load_dotenv
from typing import Annotated
from datetime import datetime, timedelta
from jose import JWTError, jwt
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from passlib.context import CryptContext

# Load environment variables from .env file
load_dotenv()

# --- Security and Authentication Configuration ---
# For a real production application, ensure SECRET_KEY is a strong, randomly generated string
# and stored securely (e.g., in environment variables).
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-that-no-one-can-guess-replace-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # Token valid for 60 minutes

# OAuth2PasswordBearer is used for handling token-based authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
# CryptContext for hashing and verifying passwords securely
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Database Setup ---
# SQLite database file; connect_args for SQLite threading safety in FastAPI
DATABASE_URL = "sqlite:///./app.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
# SessionLocal is a factory for database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Base class for declarative models
Base = declarative_base()

# User database model
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    theme = Column(String, default="light")
    notifications_enabled = Column(Boolean, default=True)
    language = Column(String, default="en")
    incognito = Column(Boolean, default=False)

# Create database tables if they don't exist
Base.metadata.create_all(bind=engine)

# Dependency to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Function to create a JWT access token
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Dependency to get the current authenticated user from the token
def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decode the JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    # Retrieve the user from the database
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user

# --- Groq API Client Setup ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    logging.error("GROQ_API_KEY environment variable not set. Please set it in your .env file.")
    raise ValueError("GROQ_API_KEY environment variable not set.")

groq_client = Groq(api_key=GROQ_API_KEY)

# --- FastAPI Application Setup ---
app = FastAPI()

# Mount static files (CSS, JS, images, etc.)
# Ensure your static files are in a directory named 'static' at the same level as main.py
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure Jinja2Templates for serving HTML files
# Ensure your HTML template files are in a directory named 'templates'
templates = Jinja2Templates(directory="templates")

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- System Prompt for AI Chatbot ---
SYSTEM_PROMPT = """
You are WellnessHub, an AI-powered assistant for medical and emotional support.
Provide empathetic, accurate responses. For medical queries, advise consulting a doctor.
For emotional support, be supportive and suggest coping strategies. Keep responses concise and helpful.
"""

# --- Routes ---

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serves the main landing page (index.html)."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Serves the login/signup page (login.html)."""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/chatbot", response_class=HTMLResponse)
async def chatbot_html(request: Request):
    """Serves the chatbot interface page (chatbot.html)."""
    return templates.TemplateResponse("chatbot.html", {"request": request})

@app.post("/login", response_class=JSONResponse)
async def login_user(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    """
    Handles user login requests.
    Expects username and password as form data.
    Returns a JWT token and user ID upon successful login.
    """
    user = db.query(User).filter(User.username == username).first()
    if not user or not pwd_context.verify(password, user.password):
        raise HTTPException(status_code=400, detail="Invalid username or password")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    return JSONResponse({"success": True, "user_id": user.id, "token": access_token})

@app.post("/register", response_class=JSONResponse)
async def register_user(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    """
    Handles user registration requests.
    Expects username and password as form data (from login.html's signup form).
    Returns a JWT token and user ID upon successful registration.
    """
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_password = pwd_context.hash(password)
    new_user = User(username=username, password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(new_user.id)}, expires_delta=access_token_expires
    )
    return JSONResponse({"success": True, "message": "User registered successfully", "user_id": new_user.id, "token": access_token})

@app.post("/api/emotional-chat", response_class=JSONResponse)
async def chat_with_ai(
    # Ensure user is authenticated using the JWT token
    user: Annotated[User, Depends(get_current_user)],
    # Expect 'input' as form data for the user's message
    input: str = Form(...),
    # Optional image file upload
    image: UploadFile | None = File(None),
    chatId: str = Form(...) # The frontend also sends a chatId
):
    """
    Handles chat messages from the frontend.
    Authenticates the user, processes the message using Groq AI, and returns a response.
    Can optionally receive an image file (though Groq's Llama 3 currently only processes text).
    """
    logger.info(f"Received chat request from user {user.id} for chatId: {chatId}")
    logger.info(f"User message: {input}")
    if image:
        logger.info(f"Image received: {image.filename}, Content-Type: {image.content_type}")
        # In a real application, you would save the image and/or process it
        # with a multimodal model. For now, we just log its presence.

    if not input:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        # Call Groq API for AI response
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": input}
            ],
            model="llama3-8b-8192", # Using a common Groq model
            temperature=0.7, # Controls randomness of response
            max_tokens=500,  # Max length of AI response
        )
        ai_response = chat_completion.choices[0].message.content
        logger.info(f"AI Response: {ai_response}")

        # Frontend expects 'response' key for the AI message
        return JSONResponse({"response": ai_response, "chatId": chatId})
    except Exception as e:
        logger.error(f"Groq API error or general chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/logout", response_class=RedirectResponse)
async def logout():
    """
    Handles user logout.
    Redirects to the login page. Client-side JS is responsible for clearing the token.
    """
    return RedirectResponse(url="/login", status_code=303)

# --- Profile & Settings Pages (placeholders for now) ---
# These would typically require authentication too.
@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    return templates.TemplateResponse("profile.html", {"request": request})

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})

# --- Feature Routes (Settings stored in DB) ---
# These endpoints are present in the original file and are included for completeness.
# They are assumed to be accessible only by authenticated users (via frontend handling of user_id).
# For full security, you'd add `user: Annotated[User, Depends(get_current_user)]` here too.

@app.post("/personalize")
async def personalize(user_id: int = Form(...), theme: str = Form(...), db: Session = Depends(get_db)):
    """Updates user's theme preference."""
    user = db.query(User).get(user_id)
    if user:
        user.theme = theme
        db.commit()
        db.refresh(user)
        return JSONResponse({"success": True, "theme": user.theme})
    raise HTTPException(status_code=404, detail="User not found")

@app.post("/notifications")
async def notifications(user_id: int = Form(...), enabled: bool = Form(...), db: Session = Depends(get_db)):
    """Toggles user's notification preference."""
    user = db.query(User).get(user_id)
    if user:
        user.notifications_enabled = enabled
        db.commit()
        db.refresh(user)
        return JSONResponse({"success": True, "notifications_enabled": user.notifications_enabled})
    raise HTTPException(status_code=404, detail="User not found")

@app.post("/language")
async def change_language(user_id: int = Form(...), language: str = Form(...), db: Session = Depends(get_db)):
    """Updates user's language preference."""
    user = db.query(User).get(user_id)
    if user:
        user.language = language
        db.commit()
        db.refresh(user)
        return JSONResponse({"success": True, "language": user.language})
    raise HTTPException(status_code=404, detail="User not found")

@app.post("/incognito")
async def toggle_incognito(user_id: int = Form(...), enabled: bool = Form(...), db: Session = Depends(get_db)):
    """Toggles user's incognito mode preference."""
    user = db.query(User).get(user_id)
    if user:
        user.incognito = enabled
        db.commit()
        db.refresh(user)
        return JSONResponse({"success": True, "incognito": user.incognito})
    raise HTTPException(status_code=404, detail="User not found")

@app.post("/appearance")
async def appearance(mode: str = Form(...)):
    """Updates general appearance mode (not tied to a specific user in DB)."""
    return JSONResponse({"success": True, "appearance": mode})

@app.get("/purchases", response_class=HTMLResponse)
async def purchases_page(request: Request):
    """Serves the purchases page (purchases.html)."""
    return templates.TemplateResponse("purchases.html", {"request": request})

@app.post("/purchase")
async def purchase_item(item_id: str = Form(...), price: float = Form(...)):
    """Handles a purchase action (placeholder)."""
    return JSONResponse({"success": True, "item": item_id, "price": price})

@app.post("/voice_support")
async def voice_support(language: str = Form(...)):
    """Sets voice support language (placeholder)."""
    return JSONResponse({"success": True, "voice_language": language})