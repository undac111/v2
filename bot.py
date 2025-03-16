import discord
from discord.ext import commands
import asyncio
from MusicaBot.buscar import search_youtube
from MusicaBot.audio import get_youtube_audio_url
from youtube_search import YoutubeSearch
import json
import imageio_ffmpeg

ffmpeg_path = imageio_ffmpeg.get_ffmpeg_binary()

class MusicBot(commands.Bot):
    def __init__(self, token):
        super().__init__(command_prefix="!", intents=discord.Intents().all())
        self.token = token
        self.music_queues = {}  # Colas de música por servidor
        self.is_playing = {}  # Estado de reproducción por servidor
        self.is_paused = {}  # Estado de pausa por servidor
        self.loop_queue = {}  # Estado de loop por servidor
        self.ready_event = asyncio.Event()
        self.guild_voice_clients = {}  # Diccionario para manejar clientes de voz por servidor

    async def on_ready(self):
        print(f"[{self.token}] Bot conectado y listo.")
        self.ready_event.set()

    async def play_music(self, user_id, channel_id, guild_id, query):
        await self.ready_event.wait()
        guild = self.get_guild(int(guild_id))
        if not guild:
            return {"status": 401, "message": f"El bot no está en el servidor {guild_id}."}

        member = guild.get_member(int(user_id))
        if not member or not member.voice or member.voice.channel.id != int(channel_id):
            return {"status": 402, "message": f"El usuario {user_id} no está en el canal de voz correcto."}

        extract = search_youtube(query)
        results = YoutubeSearch(extract, max_results=1).to_json()
        data_url = json.loads(results)

        if "videos" in data_url and len(data_url["videos"]) > 0:
            video = data_url["videos"][0]
            title = video["title"]
            duration = video["duration"]
            video_url = f"https://www.youtube.com/watch?v={video['id']}"

            if guild_id not in self.music_queues:
                self.music_queues[guild_id] = []
                self.is_playing[guild_id] = False
                self.is_paused[guild_id] = False
                self.loop_queue[guild_id] = False
        
            self.music_queues[guild_id].append({"title": title, "url": video_url, "duration": duration})

            if not self.is_playing.get(guild_id, False) and not self.is_paused.get(guild_id, False):
                asyncio.create_task(self.start_playing(int(channel_id), guild_id))

            return {"status": 200, "message": "Canción agregada", "queue": self.music_queues[guild_id], "info_music": data_url}

        return {"status": 403, "message": "No se encontraron resultados."}

    async def start_playing(self, channel_id, guild_id):
        if self.is_playing.get(guild_id, False) or not self.music_queues.get(guild_id):
            return

        while self.music_queues[guild_id]:
            query = self.music_queues[guild_id][0]
            url = get_youtube_audio_url(query["url"])
            ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

            self.is_playing[guild_id] = True
            self.is_paused[guild_id] = False

            if guild_id not in self.guild_voice_clients or not self.guild_voice_clients[guild_id].is_connected():
                channel = self.get_channel(channel_id)
                if channel is None:
                    print(f"[{self.token}] No se pudo encontrar el canal con ID {channel_id}")
                    return
            
                self.guild_voice_clients[guild_id] = await channel.connect()

            self.guild_voice_clients[guild_id].play(discord.FFmpegPCMAudio(url, **ffmpeg_options), after=lambda e: self.check_queue(guild_id))

            while self.guild_voice_clients[guild_id].is_playing() or self.is_paused[guild_id]:
                await asyncio.sleep(1)

        if not self.is_paused.get(guild_id, False):
            await self.disconnect_voice(guild_id)

    def check_queue(self, guild_id):
        if self.music_queues.get(guild_id):
            if self.loop_queue.get(guild_id, False):
                self.music_queues[guild_id].append(self.music_queues[guild_id].pop(0))  
            else:
                self.music_queues[guild_id].pop(0)  

            asyncio.create_task(self.start_playing(self.guild_voice_clients[guild_id].channel.id, guild_id))
        else:
            self.is_playing[guild_id] = False

    async def disconnect_voice(self, guild_id):
        if guild_id in self.guild_voice_clients and not self.is_paused.get(guild_id, False):
            await self.guild_voice_clients[guild_id].disconnect()
            del self.guild_voice_clients[guild_id]
            self.is_playing[guild_id] = False
            print(f"[{self.token}] Bot desconectado del canal de voz en el servidor {guild_id}.")

    async def set_loop_queue(self, guild_id: int, enable: bool):
        self.loop_queue[guild_id] = enable
        return {"status": 200, "message": f"Loop del queue {'activado' if enable else 'desactivado'}."}

    async def pause_music(self, guild_id: int):
        voice_client = self.guild_voice_clients.get(guild_id)

        if voice_client and voice_client.is_playing():
            voice_client.pause()
            self.is_paused[guild_id] = True
            self.is_playing[guild_id] = False
            return {"status": 200, "message": "Música pausada."}
        return {"status": 404, "message": "No hay música reproduciéndose."}

    async def resume_music(self, guild_id: int):
        voice_client = self.guild_voice_clients.get(guild_id)

        if voice_client and self.is_paused.get(guild_id, False):
            voice_client.resume()
            self.is_paused[guild_id] = False
            self.is_playing[guild_id] = True
            return {"status": 200, "message": "Música reanudada."}
        return {"status": 404, "message": "No hay música pausada."}

    async def skip_music(self, guild_id: int):
        voice_client = self.guild_voice_clients.get(guild_id)

        if voice_client and voice_client.is_playing():
            if len(self.music_queues[guild_id]) > 1:
                voice_client.stop()
                return {"status": 200, "message": "Saltando a la siguiente canción."}
            return {"status": 404, "message": "No hay más canciones en la cola."}
        return {"status": 404, "message": "No hay música reproduciéndose."}

    async def get_queue(self, guild_id: int, page: int = 1):
        """Devuelve la lista de canciones en la cola con paginación."""
        music_queue = self.music_queues.get(guild_id, [])

        if not music_queue:
            return {"status": 404, "message": "La cola está vacía."}

        items_per_page = 10  # Número de canciones por página
        total_pages = (len(music_queue) + items_per_page - 1) // items_per_page  # Cálculo del total de páginas

        # Validar que la página solicitada esté dentro del rango
        if page < 1 or page > total_pages:
            return {"status": 400, "message": f"Página inválida. Elige entre 1 y {total_pages}."}

        # Calcular los índices de inicio y fin para la paginación
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page

        # Crear la lista de canciones para la página actual
        queue_list = [
            {"position": i + 1, "title": song["title"], "url": song["url"], "time": song["duration"]}
            for i, song in enumerate(music_queue[start_idx:end_idx], start=start_idx)
        ]

        # Devolver la respuesta con la información de paginación
        return {
            "status": 200,
            "queue": queue_list,
            "current_page": page,
            "total_pages": total_pages
        }

    async def move_queue(self, guild_id: int, old_pos: int, new_pos: int):
        """Mueve una canción de una posición a otra en la cola."""
        music_queue = self.music_queues.get(guild_id, [])

        if not music_queue:
            return {"status": 405, "message": "La cola está vacía."}
    
        if old_pos < 1 or old_pos > len(music_queue) or new_pos < 1 or new_pos > len(music_queue):
            return {"status": 406, "message": "Posiciones fuera de rango."}
    
        song = music_queue.pop(old_pos - 1)  # Eliminamos la canción de la posición antigua
        music_queue.insert(new_pos - 1, song)  # Insertamos en la nueva posición
    
        return {"status": 200, "message": f"Canción movida a la posición {new_pos}."}

    async def remove_queue(self, guild_id: int, position: int):
        """Elimina una canción de la cola en una posición específica."""
        music_queue = self.music_queues.get(guild_id, [])

        if not music_queue:
            return {"status": 405, "message": "La cola está vacía."}

        if position < 1 or position > len(music_queue):
            return {"status": 406, "message": "Posición fuera de rango."}

        removed_song = music_queue.pop(position - 1)
        return {"status": 200, "message": f"'{removed_song['title']}' eliminada de la cola."}


    async def start_bot(self):
        try:
            await self.start(self.token)
        except Exception as e:
            print(f"Error al iniciar el bot: {e}")
