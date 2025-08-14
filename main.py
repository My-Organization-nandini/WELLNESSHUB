# FastAPI backend
from fastapi import FastAPI, Request, Form, File, UploadFile, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from groq import Groq
import os
import tempfile

app = FastAPI()

# Mount static files (CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates directory
templates = Jinja2Templates(directory="templates")

# Use environment variable for Groq API key for security
# It is recommended to set this in your environment: export GROQ_API_KEY='your_key_here'
GROQ_API_KEY = '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'
client = Groq(api_key='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')

# System prompt for AI to act as a wellness assistant
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

@app.post("/login")
async def login_post(username: str = Form(...), password: str = Form(...)):
    # Dummy authentication - replace with real auth logic
    if username == "user" and password == "pass":
        return JSONResponse({"success": True})
    else:
        return JSONResponse({"error": "Invalid credentials"}, status_code=400)

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    # Assuming you have profile.html in templates
    return templates.TemplateResponse("profile.html", {"request": request})

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    # Assuming you have settings.html in templates
    return templates.TemplateResponse("settings.html", {"request": request})

@app.post("/chat")
async def chat(query: str = Form(...)):
    try:
        # Call Groq API with the user's query and the system prompt
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": query}
            ],
            model="mixtral-8x7b-32768",  # Or other Groq models like "llama3-8b-8192"
            temperature=0.7,
            max_tokens=500,
        )
        
        response = chat_completion.choices[0].message.content
        return JSONResponse({"response": response})
    except Exception as e:
        # Return a more descriptive error message
        return JSONResponse({"error": f"An error occurred: {str(e)}"}, status_code=500)

# For mic (speech-to-text) and speaker (text-to-speech) integration in chat
@app.post("/chat_voice")
async def chat_voice(background_tasks: BackgroundTasks, audio: UploadFile = File(...)):
    try:
        # Transcribe audio using Groq's Whisper model
        content = await audio.read()
        transcription = client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=(audio.filename, content, audio.content_type),
            response_format="text"
        )
        query = transcription.text

        # Get chat response
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

        # Text-to-speech using gTTS (install with pip install gtts)
        from gtts import gTTS
        tts = gTTS(response)
        temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tts.save(temp_file.name)
        temp_file.close()

        # Clean up the file after response
        background_tasks.add_task(os.remove, temp_file.name)

        return FileResponse(temp_file.name, media_type="audio/mp3", filename="response.mp3")
    except Exception as e:
        return JSONResponse({"error": f"An error occurred: {str(e)}"}, status_code=500)

# Example for dark mode toggle - assuming client-side handles UI, backend saves preference (dummy)
@app.post("/toggle_darkmode")
async def toggle_darkmode(mode: str = Form(...)):
    # Dummy - in real app, save to user profile/db
    return JSONResponse({"success": True, "mode": mode})