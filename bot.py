import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio
import os

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

queues = {}

YDL_OPTIONS = {
    "format": "bestaudio",
    "quiet": True,
    "noplaylist": True,
    "cookiefile": "youtube_cookies.txt",
    "extractor_args": {
        "youtube": {
            "player_client": ["android"]
        }
    }
}

FFMPEG_OPTIONS = {
    "options": "-vn"
}


class MusicControls(discord.ui.View):

    def __init__(
        self,
        vc,
        guild_id
    ):

        super().__init__(timeout=None)

        self.vc = vc
        self.guild_id = guild_id

    @discord.ui.button(
        label="Pause",
        style=discord.ButtonStyle.gray
    )
    async def pause_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if self.vc.is_playing():

            self.vc.pause()

            await interaction.response.send_message(
                "⏸️ Paused",
                ephemeral=True
            )

    @discord.ui.button(
        label="Resume",
        style=discord.ButtonStyle.green
    )
    async def resume_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if self.vc.is_paused():

            self.vc.resume()

            await interaction.response.send_message(
                "▶️ Resumed",
                ephemeral=True
            )

    @discord.ui.button(
        label="Vol +",
        style=discord.ButtonStyle.blurple
    )
    async def volume_up(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if hasattr(self.vc.source, "volume"):

            self.vc.source.volume = min(
                self.vc.source.volume + 0.1,
                2.0
            )

            volume = int(
                self.vc.source.volume * 100
            )

            await interaction.response.send_message(
                f"🔊 Volume: {volume}%",
                ephemeral=True
            )

    @discord.ui.button(
        label="Vol -",
        style=discord.ButtonStyle.red
    )
    async def volume_down(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if hasattr(self.vc.source, "volume"):

            self.vc.source.volume = max(
                self.vc.source.volume - 0.1,
                0.0
            )

            volume = int(
                self.vc.source.volume * 100
            )

            await interaction.response.send_message(
                f"🔉 Volume: {volume}%",
                ephemeral=True
            )

    @discord.ui.button(
        label="Skip",
        style=discord.ButtonStyle.blurple
    )
    async def skip_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if self.vc.is_playing():

            self.vc.stop()

            await interaction.response.send_message(
                "⏭️ Skipped",
                ephemeral=True
            )

    @discord.ui.button(
        label="Stop",
        style=discord.ButtonStyle.danger
    )
    async def stop_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        queues[self.guild_id] = []

        self.vc.stop()

        await self.vc.disconnect()

        await interaction.response.send_message(
            "🛑 Music Stopped",
            ephemeral=True
        )


async def play_next(guild_id):

    guild = bot.get_guild(guild_id)

    if not guild:
        return

    vc = guild.voice_client

    if not vc:
        return

    if guild_id not in queues:
        return

    if len(queues[guild_id]) == 0:

        await vc.disconnect()

        return

    song = queues[guild_id].pop(0)

    source = discord.PCMVolumeTransformer(
        discord.FFmpegPCMAudio(
            song["url"],
            **FFMPEG_OPTIONS
        )
    )

    source.volume = 0.5

    def after_play(error):

        fut = play_next(guild_id)

        asyncio.run_coroutine_threadsafe(
            fut,
            bot.loop
        )

    vc.play(
        source,
        after=after_play
    )


@bot.event
async def on_ready():

    await bot.tree.sync()

    print(f"✅ {bot.user} online")


@bot.tree.command(
    name="play",
    description="Phát nhạc"
)
@app_commands.describe(
    song="Tên hoặc link YouTube"
)
async def play(
    interaction: discord.Interaction,
    song: str
):

    await interaction.response.defer()

    if not interaction.user.voice:

        await interaction.followup.send(
            "❌ Bạn chưa vào voice",
            ephemeral=True
        )

        return

    voice_channel = interaction.user.voice.channel

    vc = interaction.guild.voice_client

    if vc is None:

        vc = await voice_channel.connect()

    elif vc.channel != voice_channel:

        await vc.move_to(voice_channel)

    try:

        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:

            if "youtube.com" in song or "youtu.be" in song:

                info = ydl.extract_info(
                    song,
                    download=False
                )

            else:

                info = ydl.extract_info(
                    f"ytsearch1:{song}",
                    download=False
                )["entries"][0]

        data = {
            "url": info["url"],
            "title": info["title"]
        }

    except Exception as e:

        await interaction.followup.send(
            f"❌ Lỗi:\n{e}",
            ephemeral=True
        )

        return

    if interaction.guild.id not in queues:

        queues[interaction.guild.id] = []

    queues[interaction.guild.id].append(data)

    if not vc.is_playing():

        await play_next(
            interaction.guild.id
        )

    embed = discord.Embed(
        title="🎧 FAT SHARK MUSIC",
        description=f"""
▶️ NOW PLAYING

🎶 {data['title']}
""",
        color=0x5865F2
    )

    embed.set_image(
        url="https://media.tenor.com/7sk6P7JGifMAAAAd/shark-confused-ahh-meme.gif"
    )

    embed.add_field(
        name="📜 Queue",
        value=f"{len(queues[interaction.guild.id])} songs",
        inline=True
    )

    embed.set_footer(
        text="💜 FAT SHARK MUSIC • CHILL VIBES ONLY"
    )

    await interaction.followup.send(
        embed=embed,
        view=MusicControls(
            vc,
            interaction.guild.id
        )
    )


@bot.tree.command(
    name="queue",
    description="Xem queue"
)
async def queue(
    interaction: discord.Interaction
):

    if interaction.guild.id not in queues:

        await interaction.response.send_message(
            "❌ Queue trống",
            ephemeral=True
        )

        return

    if len(queues[interaction.guild.id]) == 0:

        await interaction.response.send_message(
            "❌ Queue trống",
            ephemeral=True
        )

        return

    text = ""

    for i, song in enumerate(
        queues[interaction.guild.id],
        start=1
    ):

        text += f"{i}. {song['title']}\n"

    embed = discord.Embed(
        title="📜 Music Queue",
        description=text,
        color=0x5865F2
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


@bot.tree.command(
    name="volume",
    description="Chỉnh volume"
)
@app_commands.describe(
    volume="1-200"
)
async def volume(
    interaction: discord.Interaction,
    volume: int
):

    vc = interaction.guild.voice_client

    if not vc or not vc.source:

        await interaction.response.send_message(
            "❌ Không có nhạc đang phát",
            ephemeral=True
        )

        return

    if volume < 1 or volume > 200:

        await interaction.response.send_message(
            "❌ Volume chỉ từ 1-200",
            ephemeral=True
        )

        return

    vc.source.volume = volume / 100

    embed = discord.Embed(
        title="🔊 Volume Changed",
        description=f"Current Volume: {volume}%",
        color=0x5865F2
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


@bot.tree.command(
    name="resetfat",
    description="Reset bot"
)
async def resetfat(
    interaction: discord.Interaction
):

    await interaction.response.defer(
        ephemeral=True
    )

    try:

        if interaction.guild.voice_client:

            await interaction.guild.voice_client.disconnect(
                force=True
            )

        queues[interaction.guild.id] = []

        embed = discord.Embed(
            title="🔄 FAT RESET",
            description="""
✅ Queue Reset
✅ Voice Reset
✅ Fixed Loading
""",
            color=0x57F287
        )

        await interaction.followup.send(
            embed=embed,
            ephemeral=True
        )

    except Exception as e:

        await interaction.followup.send(
            f"❌ Error:\n{e}",
            ephemeral=True
        )


bot.run(TOKEN)
