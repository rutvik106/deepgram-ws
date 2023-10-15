from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Callable
from deepgram import Deepgram
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

dg_client = Deepgram("52e4f60fd0fcc7c5884024eeacea9c5281b3b8cd")

templates = Jinja2Templates(directory="templates")


async def process_audio(fast_socket: WebSocket):
    async def get_transcript(data: Dict) -> None:
        if 'channel' in data:
            transcript = data['channel']['alternatives'][0]['transcript']

            if transcript:
                await fast_socket.send_text(transcript)

    deepgram_socket = await connect_to_deepgram(get_transcript)

    return deepgram_socket


async def connect_to_deepgram(transcript_received_handler: Callable[[Dict], None]):
    try:
        socket = await dg_client.transcription.live(
            {
                'language': "en",
                'punctuate': True,
                'smart_format': True,
                'model': "nova",
            }
        )
        socket.registerHandler(socket.event.CLOSE, lambda c: print(f'Connection closed with code {c}.'))
        socket.registerHandler(socket.event.TRANSCRIPT_RECEIVED, transcript_received_handler)

        if not socket:
            raise Exception("Failed to connect to Deepgram.")

        return socket
    except Exception as e:
        raise Exception(f'Could not open socket: {e}')

@app.get("/", response_class=HTMLResponse)
def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.websocket("/listen")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    deepgram_socket = None
    try:
        deepgram_socket = await process_audio(websocket)
        if not deepgram_socket:
            raise Exception("Failed to process audio due to socket issues.")

        while True:
            data = await websocket.receive_bytes()
            deepgram_socket.send(data)
    except Exception as e:
        raise Exception(f'Could not process audio: {e}')
    finally:
        await websocket.close()