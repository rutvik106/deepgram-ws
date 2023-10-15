from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Callable
from deepgram import Deepgram
from dotenv import load_dotenv
import os
import time

# load_dotenv()

app = FastAPI()

dg_client = Deepgram("17a9ed37235d276fb11dd3200e402a28f6eab5e1")

templates = Jinja2Templates(directory="templates")

silence_was_detected = False
window_time = 0


async def process_audio(fast_socket: WebSocket):
    async def get_transcript(data: Dict) -> None:
        if 'channel' in data:
            transcript = data["channel"]["alternatives"][0]["transcript"] 
        print("socket: transcript sent to client")
        print(transcript)

        if transcript == "":
            print("transcription is empty; this could be silence")

            global silence_was_detected
            global window_time

            if not silence_was_detected:
                silence_was_detected = True
                window_time = time.time() + 2  # 0.5 seconds
                print("silence was detected (true)")
                print("created 2-second window")
            elif time.time() > window_time:
                print("silence was more than 2 seconds; closing the mic")
                await fast_socket.send_json({'transcript':transcript , 'silence detected': True , 'response': 400})
        else:
            if silence_was_detected:
                print("silence was already detected")
                print("transcription was not empty, so resetting silence flag")
                await fast_socket.send_json({'response' : 200 , "silence detected" : False , "transcript" : transcript})
        
            silence_was_detected = False

                

    deepgram_socket = await connect_to_deepgram(get_transcript)

    return deepgram_socket

async def connect_to_deepgram(transcript_received_handler: Callable[[Dict], None]):
    try:
        socket = await dg_client.transcription.live({
            'language': "en",
            'punctuate': True,
            'smart_format': True,
            'model': "nova",
            # 'endpointing': 500,
            # 'utterence_end_ms': 2000
        })
        socket.registerHandler(socket.event.CLOSE, lambda c: print(f'Connection closed with code {c}.'))
        socket.registerHandler(socket.event.TRANSCRIPT_RECEIVED , transcript_received_handler)
        # socket.registerHandler(socket.event.TRANSCRIPT_COMPLETED , lambda e: print(f'Silence was detected {e}.'))
        
        return socket
    except Exception as e:
        raise Exception(f'Could not open socket: {e}')
 
@app.get("/", response_class=HTMLResponse)
def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/listen")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        deepgram_socket = await process_audio(websocket) 

        while True:
            data = await websocket.receive_bytes()
            print(data)
            deepgram_socket.send(data)

    except Exception as e:
        raise Exception(f'Could not process audio: {e}')
    finally:
        await websocket.close()