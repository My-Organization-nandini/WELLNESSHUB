# FastAPI backend
from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from groq import Groq
import os
import logging
from dotenv import load_dotenv

# -------------------------
# Database setup
# -------------------------
from sqlalchemy import Column, Integer, String, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext

DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# User model
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    theme = Column(String, default="light")
    notifications_enabled = Column(Boolean, default=True)
    language = Column(String, default="en")
    incognito = Column(Boolean, default=False)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -------------------------
# App & Logging setup
# -------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates directory
templates = Jinja2Templates(directory="templates")

# Load environment vars
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# -------------------------
# System prompt for AI
# -------------------------
SYSTEM_PROMPT = """
You are WellnessHub, an AI-powered assistant for medical and emotional support. 
Provide empathetic, accurate responses. For medical queries, advise consulting a doctor. 
For emotional support, be supportive and suggest coping strategies. Keep responses concise and helpful.
"""

# -------------------------
# Routes
# -------------------------

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# --- Signup & Login (DB-based) ---
@app.post("/signup")
async def signup(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed_password = pwd_context.hash(password)
    new_user = User(username=username, password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return JSONResponse({"success": True, "message": "Account created successfully"})

@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user or not pwd_context.verify(password, user.password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    return JSONResponse({"success": True, "message": "Login successful", "user_id": user.id})

# --- Chatbot ---
@app.get("/chatbot", response_class=HTMLResponse)
async def test_page(request: Request):
    return templates.TemplateResponse("chatbot.html", {"request": request})

@app.post("/chat")
async def chat(query: str = Form(...)):
    try:
        logger.info(f"Processing chat query: {query}")
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": query}
            ],
            model="mixtral-8x7b-32768",
            temperature=0.7,
            max_tokens=500,
        )
        response = chat_completion.choices[0].message.content
        return JSONResponse({"response": response})
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

# --- Profile & Settings Pages ---
@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    return templates.TemplateResponse("profile.html", {"request": request})

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})

# --- Feature Routes (Settings stored in DB) ---
@app.post("/personalize")
async def personalize(user_id: int = Form(...), theme: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).get(user_id)
    user.theme = theme
    db.commit()
    return JSONResponse({"success": True, "theme": user.theme})

@app.post("/notifications")
async def notifications(user_id: int = Form(...), enabled: bool = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).get(user_id)
    user.notifications_enabled = enabled
    db.commit()
    return JSONResponse({"success": True, "notifications_enabled": user.notifications_enabled})

@app.post("/language")
async def change_language(user_id: int = Form(...), language: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).get(user_id)
    user.language = language
    db.commit()
    return JSONResponse({"success": True, "language": user.language})

@app.post("/incognito")
async def toggle_incognito(user_id: int = Form(...), enabled: bool = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).get(user_id)
    user.incognito = enabled
    db.commit()
    return JSONResponse({"success": True, "incognito": user.incognito})

# --- Other Options ---
@app.post("/appearance")
async def appearance(mode: str = Form(...)):
    return JSONResponse({"success": True, "appearance": mode})

@app.get("/purchases", response_class=HTMLResponse)
async def purchases_page(request: Request):
    return templates.TemplateResponse("purchases.html", {"request": request})

@app.post("/purchase")
async def purchase_item(item_id: str = Form(...), price: float = Form(...)):
    return JSONResponse({"success": True, "item": item_id, "price": price})

@app.post("/voice_support")
async def voice_support(language: str = Form(...)):
    return JSONResponse({"success": True, "voice_language": language})

@app.post("/logout")
async def logout():
    return JSONResponse({"success": True, "message": "Logged out successfully"})

# --- Dark mode toggle ---
@app.post("/toggle_darkmode")
async def toggle_darkmode(mode: str = Form(...)):
    return JSONResponse({"success": True, "mode": mode})
