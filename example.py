import discord
import yt_dlp as youtube_dl
from discord.ext import commands
from youtubesearchpython import VideosSearch
import os
import datetime
import requests

discord_webhook_url = 'https://discord.com/api/webhooks/1285937187145384016/qO1DKwtahaF_tBRtstq5QAdRQkOfiWg9XLZErKexSBL1DceML9LL2ngtV1WKP-eBqdhn'
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

queue = []  # URL 큐
titles = []  # 제목 큐
is_playing = False  # 현재 노래 재생 상태 추적
current_title = None  # 현재 재생 중인 노래의 제목 저장
current_song = None  # 현재 재생 중인 노래의 URL 저장
current_thumbnail = None # 현재 재생 중인 노래의 썸네일 url 저장
ydl_opts = {
    'format': 'bestaudio/best',
    'quiet': True,
    'noplaylist': True,
    'extract_flat': False,  # 스트리밍만 하기 위해 설정
    'cookiefile': '/home/ubuntu/app/cookies.txt'  # 쿠키 파일 경로
}

FFMPEG_OPTIONS = {
    'executable': '/usr/bin/ffmpeg',
    # 'executable': 'D:\\ffmpeg\\bin\\ffmpeg.exe',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

def search_song(query):
    """유튜브에서 영상을 검색해 첫 번째 결과의 URL을 반환."""
    videos_search = VideosSearch(query, limit=1)
    result = videos_search.result()
    if result['result']:
        return result['result'][0]['link']
    return None

async def play_next_song(ctx):
    """큐에서 다음 노래를 재생."""
    global is_playing, current_title, current_song, current_thumbnail
    if queue:
        is_playing = True
        current_song = queue.pop(0)
        current_title = titles.pop(0)

        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(current_song, download=False)
                URL = info['url']
                current_thumbnail = info['thumbnail']
            voice = bot.voice_clients[0]
            voice.play(discord.FFmpegPCMAudio(URL, **FFMPEG_OPTIONS), after=lambda e: bot.loop.create_task(handle_after_play(ctx, e)))

            embed = discord.Embed(colour=discord.Colour.red(), title='노래를 재생합니다.', description="노래 정보")
            embed.set_image(url=current_thumbnail)
            embed.add_field(name=current_title, value=current_song, inline=False)
            await ctx.send(embed=embed)

        except Exception as e:
            is_playing = False
            await ctx.send(f"> \n> 노래 재생 중 오류가 발생했습니다. 다음 곡으로 넘어갑니다.\n> ")
            discord_send_message(e)
            await play_next_song(ctx)  # 오류 발생 시에도 다음 노래 재생
    else:
        is_playing = False
        current_title = None  # 더 이상 재생 중인 노래가 없으므로 초기화

async def handle_after_play(ctx, error):
    """노래 재생 후 발생하는 오류 처리."""
    if error:
        await ctx.send(f"> 오류 발생: {str(error)}. 다음 곡으로 넘어갑니다.")
        discord_send_message(str(error))
    await play_next_song(ctx)


# /재생
@bot.command(name='재생')
async def play(ctx, *, search: str = None):
    """노래를 검색하고 재생 큐에 추가."""
    global is_playing

    if not search:
        await ctx.send("> 검색어를 입력해주세요.")
        return

    if not ctx.author.voice:
        await ctx.send("> 먼저 음성 채널에 들어가야 합니다.")
        return

    try:
        if not bot.voice_clients:
            await ctx.author.voice.channel.connect()
            await ctx.send(embed=help())

        # 노래 검색
        video_url = search_song(search)
        if not video_url:
            await ctx.send(f"> '{search}'에 대한 검색 결과가 없습니다.")
            return

        # 검색된 노래 재생 목록에 추가
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            current_title = info['fulltitle']
            current_thumbnail = info['thumbnail']
            queue.append(video_url)
            titles.append(current_title)
        embed = discord.Embed(colour=discord.Colour.red(), title='노래를 재생목록에 추가합니다.', description='노래 정보')
        embed.add_field(name=current_title, value=f"{video_url}", inline=False)
        embed.set_thumbnail(url=current_thumbnail)
        await ctx.send(embed=embed)

        # 재생 중이 아니면 바로 재생 시작
        if not is_playing:
            await play_next_song(ctx)
    except Exception as e:
        discord_send_message(e)


# /넘기기
@bot.command(name='넘기기')
async def skip(ctx):
    """현재 재생중인 노래를 스킵"""
    embed=discord.Embed(colour=discord.Colour.red())
    try:
        if bot.voice_clients and bot.voice_clients[0].is_playing():
            bot.voice_clients[0].stop()
            embed.title="재생중인 노래를 스킵합니다..."
            await ctx.send(embed=embed)
            await play_next_song(ctx)
        else:
            embed.title="현재 재생 중인 노래가 없습니다."
            await ctx.send(embed=embed)
    except Exception as e:
        discord_send_message(e)


# /재생목록
@bot.command(name='재생목록')
async def playlist(ctx):
    """현재 재생 목록을 출력."""
    global current_title, current_song
    try:
        embed=discord.Embed(colour=discord.Colour.red())
        if current_title or titles:
            embed.title="재생목록"
            if current_title:
                embed.add_field(name=current_title, value=current_song, inline=False)
                embed.set_thumbnail(url=current_thumbnail)
            if titles:
                embed.add_field(name="현재 재생목록입니다.", value="")
                for i, title in enumerate(titles):
                    embed.add_field(name=f"{i+1}. {title}", value=queue[i], inline=False)
            await ctx.send(embed=embed)
        else:
            embed.title="재생목록이 비어있습니다."
            await ctx.send(embed=embed)
    except Exception as e:
        discord_send_message(e)


#종료
@bot.command(name='종료')
async def leave(ctx):
    """봇이 음성 채널에서 나가고 재생 목록을 초기화."""
    global is_playing, current_title, current_song
    embed=discord.Embed(colour=discord.Colour.red())
    try:
        if bot.voice_clients:
            await bot.voice_clients[0].disconnect()
            queue.clear()
            titles.clear()
            is_playing = False
            current_song = None
            current_title = None
        else:
            embed.title="봇이 음성 채널에 연결되어 있지 않습니다."
            await ctx.send(embed=embed)
    except Exception as e:
        discord_send_message(e)

#도움말
@bot.command(name='도움말')
async def doc(ctx):
    """봇이 음성 채널에서 나가고 재생 목록을 초기화."""
    await ctx.send(embed=help())
   

def discord_send_message(text):
    now = datetime.datetime.now()
    message = {"content": f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {str(text)}"}
    requests.post(discord_webhook_url, data=message)

def help():
    embed = discord.Embed(
    title="납치된 노래봇 사용법",
    color=discord.Color.red()  # 원하는 색상으로 바꿀 수 있음
    )
    embed.add_field(name="` /재생 { 제목 or URL } `", value="노래 재생(제목 입력 시 { }는 빼고 입력)", inline=False)
    embed.add_field(name="` /재생목록 `", value="현재 재생목록을 보여줍니다.", inline=False)
    embed.add_field(name="` /종료 `", value="노래봇 종료", inline=False)
    embed.add_field(name="` /도움말 `", value="도움말을 보여줍니다.", inline=False)
    return embed

bot.run('MTI4NTYzMzI2OTgyNzg5NTMzNw.GY5_IJ.ss7v3FVZJfnzCJbFEqDeUWMpaQXas9XRqfRYOc')