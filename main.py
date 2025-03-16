from fastapi import FastAPI
import asyncio
from pydantic import BaseModel
from bot import MusicBot

app = FastAPI()
bots = {}  # Diccionario de bots basado en tokens

class MusicRequest(BaseModel):
    token: str
    user_id: str
    channel_id: str
    guild_id: int
    query: str

class GuildRequest(BaseModel):
    token: str
    guild_id: int  # Se cambia a int para evitar errores

class MoveQueueRequest(BaseModel):
    token: str
    guild_id: int
    old_position: int
    new_position: int

class RemoveQueueRequest(BaseModel):
    token: str
    guild_id: int
    position: int

class LoopQueueRequest(BaseModel):
    token: str
    guild_id: int
    enable: bool

@app.post("/play-music")
async def play_music(request: MusicRequest):
    if request.token not in bots:
        bot = MusicBot(request.token)  # Se pasa el token al constructor
        bots[request.token] = bot
        asyncio.create_task(bot.start_bot())

    bot = bots[request.token]
    result = await bot.play_music(request.user_id, request.channel_id, request.guild_id, request.query)  # Corregir el orden
    return result

@app.post("/pause-music")
async def pause_music(request: GuildRequest):
    if request.token in bots:
        return await bots[request.token].pause_music(request.guild_id)
    return {"status": 404, "message": "Bot no encontrado."}

@app.post("/resume-music")
async def resume_music(request: GuildRequest):
    if request.token in bots:
        return await bots[request.token].resume_music(request.guild_id)
    return {"status": 404, "message": "Bot no encontrado."}

@app.post("/skip-music")
async def skip_music(request: GuildRequest):
    if request.token in bots:
        return await bots[request.token].skip_music(request.guild_id)
    return {"status": 404, "message": "Bot no encontrado."}

@app.get("/queue")
async def get_queue(token: str, guild_id: int, page: int = 1):
    if token in bots:
        return await bots[token].get_queue(guild_id, page)
    return {"status": 404, "message": "Bot no encontrado."}

@app.post("/move-queue")
async def move_queue(request: MoveQueueRequest):
    if request.token in bots:
        return await bots[request.token].move_queue(request.guild_id, request.old_position, request.new_position)
    return {"status": 404, "message": "Bot no encontrado."}

@app.post("/remove-queue")
async def remove_queue(request: RemoveQueueRequest):
    if request.token in bots:
        return await bots[request.token].remove_queue(request.guild_id, request.position)
    return {"status": 404, "message": "Bot no encontrado."}

@app.post("/loop-queue")
async def loop_queue(request: LoopQueueRequest):
    if request.token in bots:
        return await bots[request.token].set_loop_queue(request.guild_id, request.enable)
    return {"status": 404, "message": "Bot no encontrado."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
