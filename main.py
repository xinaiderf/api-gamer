import os
import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from moviepy import *

app = FastAPI()

def download_file(url, filename):
    response = requests.get(url, stream=True)
    response.raise_for_status()  # Verifica se houve erro na requisição
    with open(filename, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    return filename

@app.post("/process")
async def process_videos(request: Request):
    data = await request.json()
    video_urls = data.get('video_urls', [])
    audio_url = data.get('audio_url')

    if not video_urls or not audio_url:
        raise HTTPException(status_code=400, detail="É necessário fornecer 'video_urls' e 'audio_url'.")

    temp_files = []
    video_clips = []
    audio_clip = None
    final_clip = None
    output_filename = "output_video.mp4"

    try:
        # Baixa os vídeos e cria os clipes
        for idx, url in enumerate(video_urls):
            temp_video = f"temp_video_{idx}.mp4"
            download_file(url, temp_video)
            temp_files.append(temp_video)
            clip = VideoFileClip(temp_video)
            video_clips.append(clip)
        
        # Concatena os vídeos
        final_clip = concatenate_videoclips(video_clips)
        
        # Baixa o áudio e cria o clipe de áudio
        temp_audio = "temp_audio.mp3"
        download_file(audio_url, temp_audio)
        temp_files.append(temp_audio)
        audio_clip = AudioFileClip(temp_audio)
        
        # Atribui o áudio ao vídeo
        final_clip.audio = audio_clip
        
        # Salva o vídeo final
        final_clip.write_videofile(output_filename, codec="libx264", audio_codec="aac")
        
        return FileResponse(path=output_filename, filename=output_filename, media_type='video/mp4')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Fecha os clipes para liberar os arquivos
        try:
            if final_clip:
                if hasattr(final_clip, "reader") and final_clip.reader:
                    final_clip.reader.close()
                if hasattr(final_clip, "audio") and final_clip.audio and hasattr(final_clip.audio, "reader") and final_clip.audio.reader:
                    try:
                        final_clip.audio.reader.close_proc()
                    except Exception:
                        pass
                final_clip.close()
        except Exception as e:
            print("Erro ao fechar final_clip:", e)
        for clip in video_clips:
            try:
                clip.close()
            except Exception as e:
                print("Erro ao fechar um video clip:", e)
        try:
            if audio_clip:
                audio_clip.close()
        except Exception as e:
            print("Erro ao fechar audio_clip:", e)

        # Limpa os arquivos temporários (exceto o arquivo de saída)
        for file in temp_files:
            if os.path.exists(file):
                try:
                    os.remove(file)
                except Exception as ex:
                    print(f"Erro ao remover {file}: {ex}")
        # Não remove output_filename para que ele possa ser entregue

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8015)
