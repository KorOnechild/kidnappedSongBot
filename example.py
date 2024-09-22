import discord
import yt_dlp as youtube_dl
from discord.ext import commands
from discord.ui import Button, View
from youtubesearchpython import VideosSearch
import os
import datetime
import requests

discord_webhook_url = "https://discord.com/api/webhooks/1285937187145384016/qO1DKwtahaF_tBRtstq5QAdRQkOfiWg9XLZErKexSBL1DceML9LL2ngtV1WKP-eBqdhn"
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)
queue = []  # URL 큐
titles = []  # 제목 큐
current_title = None  # 현재 재생 중인 노래의 제목 저장
current_song = None  # 현재 재생 중인 노래의 URL 저장
current_thumbnail = None  # 현재 재생 중인 노래의 썸네일 url 저장
current_song_message = None
is_skipped = False
client_del_delay = 0.5
bot_del_delay = 5
user = None
view = None
BOT_KEY = os.getenv("BOT_KEY")
print(BOT_KEY)
ydl_opts = {
    "format": "bestaudio/best",
    "quiet": True,
    "noplaylist": True,
    "extract_flat": False,  # 스트리밍만 하기 위해 설정
    "cookiefile": "/home/ubuntu/app/cookies.txt",
}

FFMPEG_OPTIONS = {
    "executable": "/usr/bin/ffmpeg",
    # "executable": "D:\\ffmpeg\\bin\\ffmpeg.exe",
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


class MusicControlView(View):

    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx

    @discord.ui.button(label="▶", style=discord.ButtonStyle.grey)
    async def play_button_callback(
        self, interaction: discord.Interaction, button: Button
    ):
        """재생 버튼 클릭 시 호출되는 함수"""
        if (
            interaction.guild.voice_client
            and not interaction.guild.voice_client.is_playing()
        ):
            interaction.guild.voice_client.resume()  # 음성 클라이언트에서 재생을 재개
            await interaction.response.send_message(
                "노래가 다시 재생되었습니다.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "현재 재생 중이거나, 음성 채널에 연결되어 있지 않습니다.",
                ephemeral=True,
            )

    @discord.ui.button(label="❚❚", style=discord.ButtonStyle.grey)
    async def pause_button_callback(
        self, interaction: discord.Interaction, button: Button
    ):
        if (
            interaction.guild.voice_client
            and interaction.guild.voice_client.is_playing()
        ):
            interaction.guild.voice_client.pause()  # 음성 클라이언트에서 재생을 일시정지
            await interaction.response.send_message(
                "노래가 일시정지되었습니다.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "현재 재생 중인 노래가 없거나 이미 일시정지되었습니다.", ephemeral=True
            )

    @discord.ui.button(label="▶|", style=discord.ButtonStyle.grey)
    async def skip_button_callback(
        self, interaction: discord.Interaction, button: Button
    ):
        try:
            await interaction.response.defer()
            await skip(self.ctx)
        except Exception as e:
            discord_send_message(e)

    @discord.ui.button(label="☰", style=discord.ButtonStyle.grey)
    async def playlist_button_callback(
        self, interaction: discord.Interaction, button: Button
    ):
        try:
            await interaction.response.defer()
            await playlist(self.ctx)
        except Exception as e:
            discord_send_message(e)

    @discord.ui.button(label="도움말", style=discord.ButtonStyle.red)
    async def help_button_callback(
        self, interaction: discord.Interaction, button: Button
    ):
        try:
            await interaction.response.defer()
            await help(self.ctx)
        except Exception as e:
            discord_send_message(e)


def search_song(query):
    """유튜브에서 영상을 검색해 첫 번째 결과의 URL을 반환."""
    videos_search = VideosSearch(query, limit=1)
    result = videos_search.result()
    if result["result"]:
        return result["result"][0]["link"]
    return None


async def play_next_song(ctx):
    """큐에서 다음 노래를 재생."""
    global current_title, current_song, current_thumbnail, current_song_message, view, user
    if queue:
        current_song = queue.pop(0)
        current_title = titles.pop(0)
        embed = discord.Embed(colour=discord.Colour.red())

        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(current_song, download=False)
                URL = info["url"]
                current_thumbnail = info["thumbnail"]
            voice = bot.voice_clients[0]
            voice.play(
                discord.FFmpegPCMAudio(URL, **FFMPEG_OPTIONS),
                after=lambda e: bot.loop.create_task(handle_after_play(ctx, e)),
            )

            embed.title = "노래를 재생합니다."
            embed.description = f"노래 정보 | 신청자: {user}"
            embed.set_image(url=current_thumbnail)
            embed.add_field(name=current_title, value=current_song, inline=False)

            if current_song_message:
                await current_song_message.edit(embed=embed, view=view)
            else:
                current_song_message = await ctx.send(embed=embed, view=view)

        except Exception as e:
            embed.title = "노래 재생 중 오류가 발생했습니다. 다음 곡으로 넘어갑니다."
            await ctx.send(embed=embed)
            discord_send_message(e)
            await play_next_song(ctx)  # 오류 발생 시에도 다음 노래 재생


async def handle_after_play(ctx, error):
    """노래 재생 후 발생하는 오류 처리."""
    embed = discord.Embed(colour=discord.Colour.red())
    if error:
        embed.title = f"오류 발생: {str(error)}. 다음 곡으로 넘어갑니다."
        message = await ctx.send(embed=embed)
        await message.delete(delay=bot_del_delay)
        discord_send_message(str(error))
    await play_next_song(ctx)


@bot.event
async def on_message(message):
    global user
    if message.author != bot.user and message.content.startswith("/재생 "):
        user = message.author

    await bot.process_commands(message)


# /재생
@bot.command(name="재생")
async def play(ctx, *, search: str = None):
    global view
    """노래를 검색하고 재생 큐에 추가."""
    await ctx.message.delete(delay=client_del_delay)
    view = MusicControlView(ctx)

    embed = discord.Embed(colour=discord.Colour.red())
    if not search:
        embed.title = "검색어를 입력해주세요."
        message = await ctx.send(embed=embed)
        await message.delete(delay=bot_del_delay)
        return

    if not ctx.author.voice:
        embed.title = "먼저 음성 채널에 들어가야 합니다."
        message = await ctx.send(embed=embed)
        await message.delete(delay=bot_del_delay)
        return

    try:
        if not bot.voice_clients:
            await ctx.author.voice.channel.connect()
            await help(ctx)

        # 노래 검색
        video_url = search_song(search)
        if not video_url:
            embed.title = f"{search}에 대한 검색 결과가 없습니다."
            message = await ctx.send(embed=embed)
            await message.delete(delay=bot_del_delay)
            return

        # 검색된 노래 재생 목록에 추가
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            current_title = info["fulltitle"]
            current_thumbnail = info["thumbnail"]
            queue.append(video_url)
            titles.append(current_title)

        embed = discord.Embed(
            colour=discord.Colour.red(),
            title="노래를 재생목록에 추가합니다.",
            description="노래 정보",
        )
        embed.add_field(name=current_title, value=f"{video_url}", inline=False)
        embed.set_thumbnail(url=current_thumbnail)
        message = await ctx.send(embed=embed)
        await message.delete(delay=bot_del_delay)

        # 재생 중이 아니면 바로 재생 시작
        if not bot.voice_clients[0].is_playing():
            await play_next_song(ctx)
    except Exception as e:
        discord_send_message(e)


# /넘기기
@bot.command(name="넘기기")
async def skip(ctx):
    """현재 재생중인 노래를 스킵"""
    global current_song_message

    await ctx.message.delete(delay=client_del_delay)
    embed = discord.Embed(colour=discord.Colour.red())
    try:
        if bot.voice_clients and bot.voice_clients[0].is_playing():
            bot.voice_clients[0].stop()
            embed.title = "재생중인 노래를 스킵합니다..."
            message = await ctx.send(embed=embed, silent=True)
            await message.delete(delay=bot_del_delay)
            await play_next_song(ctx)
        else:
            embed.title = "현재 재생 중인 노래가 없습니다."
            message = await ctx.send(embed=embed, silent=True)
            await message.delete(delay=bot_del_delay)
    except Exception as e:
        discord_send_message(e)


# /재생목록
@bot.command(name="재생목록")
async def playlist(ctx):
    """현재 재생 목록을 출력."""
    await ctx.message.delete(delay=client_del_delay)
    global current_title, current_song
    try:
        embed = discord.Embed(colour=discord.Colour.red())
        if current_title or titles:
            embed.title = "재생목록"
            embed.description = "이 메시지는 10초 뒤 사라집니다."
            if current_title:
                embed.add_field(
                    name=f"현재 재생중: 1. {current_title}",
                    value=current_song,
                    inline=False,
                )
                embed.set_thumbnail(url=current_thumbnail)
            if titles:
                for i, title in enumerate(titles):
                    embed.add_field(
                        name=f"{i+2}. {title}", value=queue[i], inline=False
                    )
            message = await ctx.send(embed=embed, silent=True)
            await message.delete(delay=10)
        else:
            embed.title = "재생목록이 비어있습니다."
            message = await ctx.send(embed=embed, silent=True)
            await message.delete(delay=bot_del_delay)
    except Exception as e:
        discord_send_message(e)


# 종료
@bot.command(name="종료")
async def leave(ctx):
    """봇이 음성 채널에서 나가고 재생 목록을 초기화."""
    await ctx.message.delete(delay=client_del_delay)
    global current_title, current_song, current_thumbnail, current_song_message, user, view
    embed = discord.Embed(colour=discord.Colour.red())
    try:
        if bot.voice_clients:
            await bot.voice_clients[0].disconnect()
            await current_song_message.delete()
            queue.clear()
            titles.clear()
            current_title = None
            current_song = None
            current_thumbnail = None
            current_song_message = None
            user = None
            view = None
        else:
            embed.title = "봇이 음성 채널에 연결되어 있지 않습니다."
            message = await ctx.send(embed=embed, silent=True)
            await message.delete(delay=bot_del_delay)
    except Exception as e:
        discord_send_message(e)


# 도움말
@bot.command(name="도움말")
async def help(ctx):
    """봇이 음성 채널에서 나가고 재생 목록을 초기화."""

    embed = discord.Embed(
        title="납치된 노래봇 사용법",
        description="이 메시지는 10초 뒤 사라집니다.",
        color=discord.Color.red(),  # 원하는 색상으로 바꿀 수 있음
    )
    embed.add_field(
        name="` /재생 { 제목 or URL } `",
        value="노래 재생(제목 입력 시 { }는 빼고 입력)",
        inline=False,
    )
    embed.add_field(
        name="` /재생목록 `", value="현재 재생목록을 보여줍니다.", inline=False
    )
    embed.add_field(name="` /종료 `", value="노래봇 종료", inline=False)
    embed.add_field(name="` /도움말 `", value="도움말을 보여줍니다.", inline=False)
    message = await ctx.send(embed=embed, silent=True)
    await message.delete(delay=10)


def discord_send_message(text):
    now = datetime.datetime.now()
    message = {"content": f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {str(text)}"}
    requests.post(discord_webhook_url, data=message)


bot.run(BOT_KEY)
