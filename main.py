# FastAPI backend
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from groq import Groq
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Mount static files (CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates directory
templates = Jinja2Templates(directory="templates")

# Use environment variable for Groq API key

client = Groq(api_key="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")

# System prompt for AI
SYSTEM_PROMPT = """
You are WellnessHub, an AI-powered assistant for medical and emotional support. 
Provide empathetic, accurate responses. For medical queries, advise consulting a doctor. 
For emotional support, be supportive and suggest coping strategies. Keep responses concise and helpful.
"""

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})



@app.get("/chatbot", response_class=HTMLResponse)
async def test_page(request: Request):
    return templates.TemplateResponse("chatbot.html", {"request": request})


@app.post("/login")
async def login_post(username: str = Form(...), password: str = Form(...)):
    try:
        # Dummy authentication - replace with real auth logic
        if username == "user" and password == "pass":
            logger.info(f"Successful login for username: {username}")
            return JSONResponse({"success": True})
        else:
            logger.warning(f"Failed login attempt for username: {username}")
            raise HTTPException(status_code=400, detail="Invalid credentials")
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Login failed: {str(e)}")

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    return templates.TemplateResponse("profile.html", {"request": request})

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})

@app.post("/chat")
async def chat(query: str = Form(...)):
    try:
        logger.info(f"Processing chat query: {query}")
        # Call Groq API
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
        logger.info("Chat response generated successfully")
        return JSONResponse({"response": response})
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@app.post("/toggle_darkmode")
async def toggle_darkmode(mode: str = Form(...)):
    try:
        logger.info(f"Dark mode toggled: {mode}")
        return JSONResponse({"success": True, "mode": mode})
    except Exception as e:
        logger.error(f"Dark mode toggle error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Dark mode toggle error: {str(e)}")
    








