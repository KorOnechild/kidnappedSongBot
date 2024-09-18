import discord
import yt_dlp as youtube_dl
from discord.ext import commands
import asyncio
import os  # To use environment variables for token security

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

queue = []  # Queue to store the URLs
is_playing = False  # To track if the bot is currently playing a song
current_song = None  # Variable to track the currently playing song
current_song_title = None
play_list = []

@bot.command(name='재생')
async def play(ctx, url):
    global is_playing

    channel = ctx.author.voice.channel
    if not bot.voice_clients:
        await channel.connect()
        await ctx.send("Connected to the voice channel.")

    # Add the song to the queue
    queue.append(url)
    await ctx.send(f"Added to queue: {url}")
    if not is_playing:
        # If no song is currently playing, start playing
        await play_next_song(ctx)

@bot.command(name='넘기기')
async def skip(ctx):
    global is_playing
    voice = bot.voice_clients[0]
    
    if voice.is_playing():
        voice.stop()  # Stop the current song
        await ctx.send("Skipping current track...")
        await play_next_song(ctx)  # Play the next song in the queue
    else:
        await ctx.send("No track is currently playing.")

async def play_next_song(ctx):
    global is_playing, current_song
    if queue:
        is_playing = True
        current_song = queue.pop(0)

        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'noplaylist': True,
            'extract_flat': True,  # Only get the URL of the stream
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(current_song, download=False)
            current_song_title = info['fulltitle']
            play_info = {'url': {current_song}, 'title': {info['fulltitle']}}
            play_list.append(play_info) 

            URL = info['url']
        FFMPEG_OPTIONS = {
            'executable': 'D:\\ffmpeg\\bin\\ffmpeg.exe',
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }

        voice = bot.voice_clients[0]
        voice.play(discord.FFmpegPCMAudio(URL, **FFMPEG_OPTIONS), after=lambda e: asyncio.run_coroutine_threadsafe(play_next_song(ctx), bot.loop).result())
        await ctx.send(f"Now playing: {current_song}")
    else:
        is_playing = False
        current_song = None

@bot.command(name='재생목록')
async def playList(ctx):
    if current_song or queue:
        playlist = ""
        if current_song:
            playlist += f"현재 재생 중: {current_song_title}\n"
        if queue:
            playlist += "\n".join([f"{i+1}. {info['title']}" for i, info in enumerate(play_list)])
        await ctx.send(f"현재 재생 목록:\n{playlist}")
    else:
        await ctx.send("재생 목록이 비어 있습니다.")

@bot.command()
async def leave(ctx):
    if bot.voice_clients:
        await bot.voice_clients[0].disconnect()
        await ctx.send("Disconnected from the voice channel.")
    else:
        await ctx.send("The bot is not connected to any voice channel.")

bot.run('MTI4NTYzMzI2OTgyNzg5NTMzNw.GY5_IJ.ss7v3FVZJfnzCJbFEqDeUWMpaQXas9XRqfRYOc')