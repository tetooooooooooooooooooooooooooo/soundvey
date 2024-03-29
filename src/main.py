import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
import Database
from pymongo import MongoClient
import certifi
import asyncio
import datetime


async def UpdateTask(bot):
    while True:
        now = datetime.datetime.now()
        if not (12 < now.hour < 18):
            return

        database = Database.get_bot_database(bot.MongoClient)
        roles = database["roles"]
        servers = database["servers"]

        wantedDate = (datetime.datetime.now() - datetime.timedelta(days=8)).date()

        objects = roles.find({"date": str(wantedDate)})
        for object in objects:
            # Check if bot has mentioned these clients today.
            if not "mentioned" in object:
                print("found!")
                # The date has not been mentioned in this guild
                roles.find_one_and_update(
                    {"_id": object["_id"]},
                    {"$set": {"mentioned": True}},
                )

                guild = await bot.fetch_guild(object["guild_id"])
                if not guild:
                    return

                # Get discovery channel in server and mention role in that channel
                server = servers.find_one({"guild_id": object["guild_id"]})
                if not server:
                    print(f'Could not find server data for guild {object["guild_id"]}')
                    return

                channel = await guild.fetch_channel(server["discovery_channel"])
                if not channel:
                    print("Could not find discovery channel. It was probably deleted?")
                    return

                message = await channel.send(content=f'<@&{object["role_id"]}>')
                await message.delete(delay=5.0)

        # Delete old data
        oldDate = (datetime.datetime.now() - datetime.timedelta(days=9)).date()
        objects = roles.find({"date": str(oldDate)})
        for object in objects:
            guild = await bot.fetch_guild(object["guild_id"])
            role = guild.get_role(object["role_id"])
            if not role:
                return

            role.delete(reason="The date became old and was ultimately cleaned up")

        # Delete all the data for the old date
        roles.delete_many({"date": str(oldDate)})

        await asyncio.sleep(1 * 60 * 60)


class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

        self.cogslist = ["Cogs.commandcog", "Cogs.eventcog"]
        self.MongoClient = MongoClient(
            os.environ.get("Database_Connection_String"), tlsCAFile=certifi.where()
        )

    async def setup_hook(self):
        for ext in self.cogslist:
            await self.load_extension(ext)

    async def on_ready(self):
        print("Bot is ready!")

        synced = await self.tree.sync()
        print(f"Loaded {len(synced)} slash commands.")

        self.loop.create_task(UpdateTask(self))


load_dotenv()

bot = Bot()
bot.run(os.environ.get("BOT_TOKEN"))
