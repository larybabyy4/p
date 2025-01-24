import os
import asyncio
from telethon import TelegramClient
from datetime import datetime
import subprocess
from collections import defaultdict

# Telegram configuration
API_ID = 26968169  # Coloque seu API_ID aqui
API_HASH = '5768aedba5732b11a1288965b57472e7'  # Coloque seu API_HASH aqui
PHONE_NUMBER = +5516982194939  # Coloque seu número de telefone aqui
CHAT_ID = -1002441869048  # Coloque o ID do chat de destino aqui

# Texto para sobrepor nas mídias
TEXT_LINE1 = "Linha 1"
TEXT_LINE2 = "Linha 2"

# Buffer mínimo de mídias
MIN_VIDEOS = 20
MIN_PHOTOS = 5

# Diretórios para armazenar mídias processadas
PROCESSED_DIR = "processed_media"
VIDEOS_DIR = os.path.join(PROCESSED_DIR, "videos")
PHOTOS_DIR = os.path.join(PROCESSED_DIR, "photos")

# Initialize Telegram client
client = None

# Buffer de mídias processadas
processed_media = defaultdict(list)  # 'videos' e 'photos'

def setup_directories():
    """Cria diretórios necessários"""
    os.makedirs(VIDEOS_DIR, exist_ok=True)
    os.makedirs(PHOTOS_DIR, exist_ok=True)

def count_processed_media():
    """Conta quantas mídias processadas temos em cada categoria"""
    videos = len([f for f in os.listdir(VIDEOS_DIR) if os.path.isfile(os.path.join(VIDEOS_DIR, f))])
    photos = len([f for f in os.listdir(PHOTOS_DIR) if os.path.isfile(os.path.join(PHOTOS_DIR, f))])
    return {'videos': videos, 'photos': photos}

async def add_text_to_media(input_path):
    """Adiciona texto à mídia usando FFmpeg"""
    try:
        is_video = input_path.lower().endswith(('.mp4', '.gif'))
        output_dir = VIDEOS_DIR if is_video else PHOTOS_DIR
        output_path = os.path.join(output_dir, f"processed_{os.path.basename(input_path)}")
        
        # Comando FFmpeg para adicionar texto centralizado
        command = [
            'ffmpeg', '-i', input_path,
            '-vf', f"drawtext=text='{TEXT_LINE1}':fontcolor=white:fontsize=24:x=(w-text_w)/2:y=(h-text_h)/2-30,"
                   f"drawtext=text='{TEXT_LINE2}':fontcolor=white:fontsize=24:x=(w-text_w)/2:y=(h-text_h)/2+10",
            '-y', output_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        await process.communicate()
        
        if process.returncode == 0 and os.path.exists(output_path):
            os.remove(input_path)  # Remove arquivo original
            return output_path
        return input_path
    except Exception as e:
        print(f"Erro ao adicionar texto: {e}")
        return input_path

async def init_telegram():
    """Inicializa o cliente do Telegram"""
    global client
    if not all([API_ID, API_HASH, PHONE_NUMBER, CHAT_ID]):
        print("Por favor, configure API_ID, API_HASH, PHONE_NUMBER e CHAT_ID no script")
        return False
    
    try:
        client = TelegramClient('bot_session', API_ID, API_HASH)
        await client.start(phone=PHONE_NUMBER)
        print("Conectado ao Telegram com sucesso!")
        return True
    except Exception as e:
        print(f"Erro ao conectar ao Telegram: {e}")
        return False

async def process_media():
    """Processa links e mantém buffer de mídias"""
    print("Processador de mídia iniciado!")
    
    while True:
        try:
            media_count = count_processed_media()
            need_videos = MIN_VIDEOS - media_count['videos']
            need_photos = MIN_PHOTOS - media_count['photos']
            
            if need_videos > 0 or need_photos > 0:
                print(f"\nProcessando mais mídias... Precisamos de:")
                if need_videos > 0:
                    print(f"- {need_videos} vídeos")
                if need_photos > 0:
                    print(f"- {need_photos} fotos")
                
                if os.path.exists('links.txt'):
                    with open('links.txt', 'r') as file:
                        links = file.readlines()
                    
                    # Mantém links não processados no arquivo
                    with open('links.txt', 'w') as file:
                        file.writelines(links[1:])  # Remove apenas o primeiro link
                    
                    if links:
                        link = links[0].strip()
                        if link:
                            try:
                                print(f"\nBaixando: {link}")
                                process = await asyncio.create_subprocess_shell(
                                    f'gallery-dl {link}',
                                    stdout=asyncio.subprocess.PIPE,
                                    stderr=asyncio.subprocess.PIPE
                                )
                                await process.communicate()
                                
                                # Processa arquivos baixados
                                for root, _, files in os.walk('.'):
                                    for file in files:
                                        if file.endswith(('.jpg', '.jpeg', '.png', '.mp4', '.gif')):
                                            file_path = os.path.join(root, file)
                                            try:
                                                print(f"Processando: {file_path}")
                                                processed_path = await add_text_to_media(file_path)
                                                print(f"Processado com sucesso: {processed_path}")
                                            except Exception as e:
                                                print(f"Erro ao processar {file_path}: {e}")
                                                if os.path.exists(file_path):
                                                    os.remove(file_path)
                            except Exception as e:
                                print(f"Erro ao processar {link}: {e}")
            
            # Espera antes de verificar novamente
            await asyncio.sleep(5)
            
        except Exception as e:
            print(f"Erro no loop de processamento: {e}")
            await asyncio.sleep(5)

async def send_media():
    """Envia mídias processadas para o Telegram"""
    while True:
        try:
            media_count = count_processed_media()
            
            # Envia vídeos
            for video in os.listdir(VIDEOS_DIR):
                video_path = os.path.join(VIDEOS_DIR, video)
                try:
                    print(f"Enviando vídeo: {video}")
                    await client.send_file(CHAT_ID, video_path)
                    print(f"Vídeo enviado com sucesso: {video}")
                    os.remove(video_path)
                    await asyncio.sleep(30)  # Espera entre envios
                except Exception as e:
                    print(f"Erro ao enviar vídeo {video}: {e}")
            
            # Envia fotos
            for photo in os.listdir(PHOTOS_DIR):
                photo_path = os.path.join(PHOTOS_DIR, photo)
                try:
                    print(f"Enviando foto: {photo}")
                    await client.send_file(CHAT_ID, photo_path)
                    print(f"Foto enviada com sucesso: {photo}")
                    os.remove(photo_path)
                    await asyncio.sleep(30)  # Espera entre envios
                except Exception as e:
                    print(f"Erro ao enviar foto {photo}: {e}")
            
            await asyncio.sleep(5)
            
        except Exception as e:
            print(f"Erro no loop de envio: {e}")
            await asyncio.sleep(5)

async def main():
    print("=== Processador de Mídia com Buffer ===")
    print("1. Conectando ao Telegram...")
    
    if not await init_telegram():
        print("Falha ao inicializar Telegram. Saindo...")
        return
    
    setup_directories()
    
    print(f"2. Mantendo buffer mínimo de {MIN_VIDEOS} vídeos e {MIN_PHOTOS} fotos")
    print("3. Monitorando 'links.txt' para novos links")
    print("4. Pressione Ctrl+C para parar o programa")
    print("\nIniciando processador...")
    
    try:
        # Executa processamento e envio em paralelo
        await asyncio.gather(
            process_media(),
            send_media()
        )
    except KeyboardInterrupt:
        print("\nPrograma interrompido pelo usuário")
    except Exception as e:
        print(f"\nErro no programa: {str(e)}")
    finally:
        if client:
            await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
