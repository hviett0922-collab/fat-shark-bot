python
import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio

TOKEN = "YOUR_BOT_TOKEN"

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

queues = {}

FFMPEG_OPTIONS = {
    "options": "-vn"
}

YDL_OPTIONS = {
    "format": "bestaudio/best",
    "quiet": True
}


class MusicControls(discord.ui.View):

    def __init__(self, vc, guild_id, title):
        super().__init__(timeout=None)
        self.vc = vc
        self.guild_id = guild_id
        self.title = title

    @discord.ui.button(
        label="Pause",
        style=discord.ButtonStyle.gray
    )
    async def pause(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if self.vc.is_playing():
            self.vc.pause()

            await interaction.response.send_message(
                "⏸️ Đã pause",
                ephemeral=True
            )

    @discord.ui.button(
        label="Resume",
        style=discord.ButtonStyle.green
    )
    async def resume(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if self.vc.is_paused():
            self.vc.resume()

            await interaction.response.send_message(
                "▶️ Đã resume",
                ephemeral=True
            )

    @discord.ui.button(
        label="Skip",
        style=discord.ButtonStyle.blurple
    )
    async def skip(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if self.vc.is_playing():
            self.vc.stop()

            await interaction.response.send_message(
                "⏭️ Đã skip",
                ephemeral=True
            )

    @discord.ui.button(
        label="Stop",
        style=discord.ButtonStyle.red
    )
    async def stop(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        self.vc.stop()

        queues[self.guild_id] = []

        await self.vc.disconnect()

        await interaction.response.send_message(
            "⏹️ Đã dừng nhạc",
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

    if len(queues[guild_id]) > 0:

        queues[guild_id].pop(0)

    if len(queues[guild_id]) == 0:

        await vc.disconnect()
        return

    next_song = queues[guild_id][0]

    def after(error):

        fut = play_next(guild_id)

        asyncio.run_coroutine_threadsafe(
            fut,
            bot.loop
        )

    source = discord.PCMVolumeTransformer(
        discord.FFmpegPCMAudio(
            next_song["url"],
            **FFMPEG_OPTIONS
        ),
        volume=0.8
    )

    vc.play(
        source,
        after=after
    )


@bot.event
async def on_ready():

    try:

        synced = await bot.tree.sync()

        print(f"✅ Synced {len(synced)} commands")

    except Exception as e:

        print(e)

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

    if not vc.is_playing() and not vc.is_paused():

        first_song = queues[
            interaction.guild.id
        ][0]

        def after(error):

            fut = play_next(
                interaction.guild.id
            )

            asyncio.run_coroutine_threadsafe(
                fut,
                bot.loop
            )

        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(
                first_song["url"],
                **FFMPEG_OPTIONS
            ),
            volume=0.8
        )

        vc.play(
            source,
            after=after
        )

    volume_now = 80

    volume_bar = "▰▰▰▰▱▱▱▱▱▱"

    embed = discord.Embed(
        title="🎧 FAT SHARK MUSIC",
        description=f"""

NOW PLAYING
{data['title']}

⏱️ 01:24 / 03:45

{volume_bar}

▶ PLAYING...
````

""",
color=0x5865F2
)

embed.set_image(
    url="https://i.imgur.com/8Km9tLL.gif"
)

embed.add_field(
    name="🔊 Volume",
    value=f"{volume_now}%",
    inline=True
)

embed.add_field(
    name="🎵 Queue",
    value=f"`{len(queues[interaction.guild.id])}` songs",
    inline=True
)

embed.add_field(
    name="👥 Listening",
    value=f"`{len(voice_channel.members)-1}` users",
    inline=True
)

embed.set_footer(
    text="💜 FAT SHARK MUSIC • CHILL VIBES ONLY"
)

await interaction.followup.send(
    embed=embed,
    view=MusicControls(
        vc,
        interaction.guild.id,
        data["title"]
    )
)

@bot.tree.command(
name="volume",
description="Chỉnh volume"
)
@app_commands.describe(
amount="1-200"
)
async def queue(
    interaction: discord.Interaction
):
    await interaction.response.send_message("Queue")
```
vc = interaction.guild.voice_client

if not vc:

    await interaction.response.send_message(
        "❌ Bot chưa vào voice",
        ephemeral=True
    )
    return

if amount < 1 or amount > 200:

    await interaction.response.send_message(
        "❌ Volume chỉ từ 1-200",
        ephemeral=True
    )
    return

volume_value = amount / 100

if hasattr(vc.source, "volume"):
    vc.source.volume = volume_value

bar_count = int(amount / 20)

volume_bar = (
    "▰" * bar_count +
    "▱" * (10 - bar_count)
)

embed = discord.Embed(
    title="🔊 FAT SHARK VOLUME",
    description=f"""
```

## {amount}%

{volume_bar}
""",
color=0x5865F2
)

```
embed.set_footer(
    text="💜 FAT SHARK MUSIC"
)

await interaction.response.send_message(
    embed=embed,
    ephemeral=True
)
```

@bot.tree.command(
    name="volume",
    description="Chỉnh volume"
)
@app_commands.describe(
    amount="1-200"
)
async def volume(
    interaction: discord.Interaction,
    amount: int
):

    vc = interaction.guild.voice_client

    if not vc:

        await interaction.response.send_message(
            "❌ Bot chưa vào voice",
            ephemeral=True
        )
        return

    if amount < 1 or amount > 200:

        await interaction.response.send_message(
            "❌ Volume chỉ từ 1-200",
            ephemeral=True
        )
        return

    volume_value = amount / 100

    if hasattr(vc.source, "volume"):
        vc.source.volume = volume_value

    bar_count = int(amount / 20)

    volume_bar = (
        "▰" * bar_count +
        "▱" * (10 - bar_count)
    )

    embed = discord.Embed(
        title="🔊 FAT SHARK VOLUME",
        description=f"""

## {amount}%

{volume_bar}

""",
        color=0x5865F2
    )

    embed.set_footer(
        text="💜 FAT SHARK MUSIC"
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


@bot.tree.command(
    name="queue",
    description="Xem queue"
)
async def queue(
    interaction: discord.Interaction
):

    queue_list = queues.get(
        interaction.guild.id,
        []
    )

    if not queue_list:

        await interaction.response.send_message(
            "❌ Queue trống",
            ephemeral=True
        )
        return

    text = ""

    for i, song in enumerate(queue_list):

        text += f"{i+1}. {song['title']}\n"

    embed = discord.Embed(
        title="📜 Queue",
        description=text,
        color=0x5865F2
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


@bot.tree.command(
    name="leave",
    description="Rời voice"
)
async def leave(
    interaction: discord.Interaction
):

    vc = interaction.guild.voice_client

    if vc:

        await vc.disconnect()

        await interaction.response.send_message(
            "👋 Đã rời voice",
            ephemeral=True
        )

    else:

        await interaction.response.send_message(
            "❌ Bot chưa vào voice",
            ephemeral=True
        )


bot.run(TOKEN)
