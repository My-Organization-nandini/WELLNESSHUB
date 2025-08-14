# FastAPI backend
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from groq import Groq
import os

app = FastAPI()

# Mount static files (CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates directory
templates = Jinja2Templates(directory="templates")

# Groq API key (replace with your key; better to use os.getenv("GROQ_API_KEY") in production)
GROQ_API_KEY = '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' # Replace this!
client = Groq(api_key=GROQ_API_KEY)

# System prompt for AI to act as a wellness assistant
SYSTEM_PROMPT = """
You are WellnessHub, an AI-powered assistant for medical and emotional support. 
Provide empathetic, accurate responses. For medical queries, advise consulting a doctor. 
For emotional support, be supportive and suggest coping strategies. Keep responses concise and helpful.
"""

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/chat")
async def chat(query: str = Form(...), category: str = Form(...)):
    try:
        # Customize prompt based on category
        full_prompt = f"{SYSTEM_PROMPT}\nCategory: {category}\nUser: {query}\nAssistant:"
        
        # Call Groq API
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": query}
            ],
            model="mixtral-8x7b-32768",  # You can change to other Groq models like "llama2-70b-4096"
            temperature=0.7,
            max_tokens=500,
        )
        
        response = chat_completion.choices[0].message.content
        return JSONResponse({"response": response})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)