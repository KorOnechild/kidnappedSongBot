import discord
import yt_dlp as youtube_dl
from discord.ext import commands
from youtubesearchpython import VideosSearch
import asyncio
import os  # To use environment variables for token security

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

queue = []  # Queue to store the URLs
titles = []  # Queue to store the song titles
is_playing = False  # To track if the bot is currently playing a song
current_song = None  # Variable to track the currently playing song
current_title = None  # Variable to track the title of the currently playing song

@bot.command(name='재생')
async def play(ctx, *, search: str):
    global is_playing

    channel = ctx.author.voice.channel
    if not bot.voice_clients:
        await channel.connect()
        await ctx.send("음성 채널에 연결되었습니다.")

    # 검색을 통해 YouTube URL 찾기
    video_url = search_song(search)  # await 제거

    if video_url:
        queue.append(video_url)  # URL 추가
        await ctx.send(f"재생목록에 추가합니다: {video_url}")

        if not is_playing:
            # If no song is currently playing, start playing
            await play_next_song(ctx)
    else:
        await ctx.send(f"해당 노래에 대한 검색결과가 없습니다. '{video_url}'.")

def search_song(query):
    """주어진 검색어로 YouTube에서 영상을 검색하고 첫 번째 결과의 URL을 반환합니다."""
    videos_search = VideosSearch(query, limit=1)
    result = videos_search.result()  # await 제거
    if result['result']:
        return result['result'][0]['link']  # 첫 번째 검색 결과의 URL 반환
    return None

@bot.command(name='넘기기')
async def skip(ctx):
    global is_playing
    voice = bot.voice_clients[0]
    
    if voice.is_playing():
        voice.stop()  # Stop the current song
        await ctx.send("현재 재생중인 노래를 스킵합니다...")
        await play_next_song(ctx)  # Play the next song in the queue
    else:
        await ctx.send("현재 재생중인 노래가 없습니다.")

async def play_next_song(ctx):
    global is_playing, current_song, current_title
    if queue:
        is_playing = True
        current_song = queue.pop(0)
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'noplaylist': True,
            'extract_flat': False,  # fulltitle 사용을 위해 False로 설정
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(current_song, download=False)
            URL = info['url']
            current_title = info['fulltitle']  # 정확한 노래 제목 저장

        FFMPEG_OPTIONS = {
            'executable': 'D:\\ffmpeg\\bin\\ffmpeg.exe',
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }

        voice = bot.voice_clients[0]
        voice.play(discord.FFmpegPCMAudio(URL, **FFMPEG_OPTIONS), after=lambda e: asyncio.run_coroutine_threadsafe(play_next_song(ctx), bot.loop).result())
        await ctx.send(f"현재 재생중인 노래: {current_title}")
    else:
        is_playing = False
        current_song = None

@bot.command(name='재생목록')
async def playList(ctx):
    if current_title or titles:
        playlist = ""
        
        if current_title:
            playlist += f"현재 재생 중: {current_title}\n"
        if titles:
            playlist += "\n".join([f"{i+1}. {title}" for i, title in enumerate(titles)])
        await ctx.send(f"현재 재생 목록:\n{playlist}")
    else:
        await ctx.send("재생 목록이 비어 있습니다.")

@bot.command(name='종료')
async def leave(ctx):
    if bot.voice_clients:
        queue.clear()
        await bot.voice_clients[0].disconnect()
        await ctx.send("연결을 종료했습니다.")
    else:
        await ctx.send("채널에 연결되어 있지 않습니다.")

bot.run('MTI4NTYzMzI2OTgyNzg5NTMzNw.GY5_IJ.ss7v3FVZJfnzCJbFEqDeUWMpaQXas9XRqfRYOc')