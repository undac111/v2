import subprocess

# Ruta del archivo de cookies
COOKIES_PATH = "cookies.txt"

def get_youtube_audio_url(video_url):
    try:
        # Construir el comando yt-dlp para obtener la URL del stream de audio
        command = [
            "yt-dlp", "-g", "-f", "bestaudio[ext=m4a]/best",
            "--cookies", COOKIES_PATH, video_url
        ]
        
        # Ejecutar el comando y capturar la salida
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        # Obtener la URL del audio
        audio_url = result.stdout.strip()
        
        if audio_url:
            return audio_url
        else:
            print("No se encontró la URL del audio.")
            return None
    except subprocess.CalledProcessError as e:
        print(f"Error al ejecutar yt-dlp: {e}")
        return None
    except Exception as e:
        print(f"Error inesperado: {e}")
        return None


