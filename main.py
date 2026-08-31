import json
import os

import discord
import requests
from discord import client
from discord.ext import commands

from dotenv import load_dotenv
import ollama

import getresponses as gr
import getprompt as gp
import global_var as gvar

from gtts import gTTS


load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
ALLIE_ID = os.getenv('ALLIE_ID')

intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix='/', intents=intents) # / prefix to use commands; intents defined above

conversation = {}
users = {}
context_limit = 25 # how many messages allieBot may remember at a given time
model = "llama3.2" # ..............the model allieBot is running

@client.event
async def on_ready():
    print(f"{client.user.name} is online!")
    await client.change_presence(activity=discord.Game(name="i am the perfect machine"), status=discord.Status.dnd)
    await client.tree.sync() # type: ignore

def store_messages(server, channel, message, role, id):
    if (server in conversation) and (channel in conversation[server]):
        current_chat = conversation[server][channel]

        if context_limit <= len(current_chat):
            current_chat.pop(0) # if the length of your conversation with allieBot exceeds
                                # her limit, the first message in said conversation
                                # is returned and removed from the list

        current_chat.append({"role": role, "content": message}) # update history upon new message and specify if from
                                                                # user or bot
    else:
        if server not in conversation:
            conversation[server] = {} # create conversation history for a server
        conversation[server][channel] = [{"role": role, "content": message}]

def get_messages(server, channel):
    return conversation[server][channel]

@client.tree.command(name = "dottsresponses", description = "enable or disable tts with responses")
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.allowed_installs(guilds=True, users=True)
async def dottsResponses(interaction: discord.Interaction, do: bool): # pass in either true or false (on or off)
                                                                    # as of 8/29 this applies in EVERY server. fix
    if do:
        gvar.doTTS = True
        await interaction.response.send_message("tts enabled", ephemeral=True)
        await interaction.followup.send(gr.cake_spam, ephemeral=True)
    else:
        await interaction.response.send_message("tts disabled", ephemeral=True)
        gvar.doTTS = False

@client.event
async def on_message(message):
    if message.author == client.user: # don't do anything if the author of the message is allieBot herself
        return
    if message.content.startswith("allieBot"): # only engage if a message starts with her name
        if message.author.id == int(ALLIE_ID):
            print("talking to allie")
            system_prompt = gp.defmd #get prompt according to user id
        else:
            print("talking to", message.author.name)
            system_prompt = gp.default #get prompt

        store_messages(str(message.guild.id), str(message.channel.id), message.content, "user", str(message.author.id))
        findresponse = ollama.chat(
            model=model, # llama 3.2; specified above
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message.content},
            ] + get_messages(str(message.guild.id), str(message.channel.id)), # return previous conversation
            options = {'temperature': 0.4} # temperature measures how strictly allieBot abides by her prompt
                                           # or "rules", ranging from 0.0-2.5; the higher it is, the more responses
                                           # may deviate from said prompt
        )
        store_messages(str(message.guild.id), str(message.channel.id),
        findresponse.message.content, "assistant", str(client.user.id))

        botresponse = findresponse['message']['content']
        for i in range (0, len(botresponse), 2000): # gotta be under 2000 characters because this is discord
            await message.channel.send(botresponse[i:i+2000])

        if gvar.doTTS: # if you have doTTS enabled
            tts = gTTS(text=botresponse, lang='en')
            tts.save("response.mp3")
            file=discord.File("response.mp3")
            await message.channel.send(file=file)
        await client.process_commands(message)

@client.tree.command(name = "talk", description = "talk to alliebot wherever you'd like")
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.allowed_installs(guilds=True, users=True)
async def talk(interaction: discord.Interaction, message: str): # pass in a string as your message to her
    firstResponse = True
    await interaction.response.defer()
    channel = client.get_channel(interaction.channel_id)
    guild = str(client.get_guild(interaction.guild_id)) if interaction.guild_id else "0"

    if interaction.user.id == int(ALLIE_ID):
        print("talking to allie")
        system_prompt = gp.defmd
    else:
        print("talking to", interaction.user.name)
        system_prompt = gp.default

    store_messages(str(interaction.guild_id), str(interaction.channel_id), message, "user", str(interaction.user.id))
    findresponse = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ] + get_messages(str(interaction.guild_id), str(interaction.channel_id)),
        options = {'temperature': 0.4}
    )
    store_messages(str(interaction.guild_id), str(interaction.channel_id),
    findresponse.message.content, "assistant", str(client.user.id))

    botresponse = findresponse['message']['content']
    for i in range(0, len(botresponse), 2000):
        if firstResponse:
            await interaction.followup.send(botresponse[i:i + 2000])
            firstResponse = False # no longer first response
        else:
            await interaction.channel.send(botresponse[i:i + 2000])
            firstResponse = False
    await client.process_commands(message)

@client.tree.command(name = "cake", description = "yummmmm")
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.allowed_installs(guilds=True, users=True)
async def cake(interaction: discord.Interaction):
    await interaction.response.send_message(gr.cake_spam) # many cake emojis
    await interaction.followup.send(gr.cake_spam)
    await interaction.followup.send(gr.cake_spam)

@client.tree.command(name="skyfall", description="where were you when the sky was falling?")
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.allowed_installs(guilds=True, users=True)
async def skyfall(interaction: discord.Interaction):
    await interaction.response.send_message(gr.skyfall) # review found on the steam page of a chicken little game

class WeatherAPIError(Exception):
    # Raised when WeatherAPI returns an error response.
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(f"WeatherAPI error {code}: {message}")

@client.tree.command(name="weather", description = "weather today")
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@discord.app_commands.allowed_installs(guilds=True, users=True)
async def weather(interaction: discord.Interaction, location: str, aqi: bool = True) -> dict: # pass in desired location
    parameters = {
        "key": os.getenv("WEATHER_API_TOKEN"),
        "q": location,
        "aqi": "yes" if aqi else "no", # always going to be yes because i said so
    }

    result = requests.get(f"https://api.weatherapi.com/v1/current.json", params=parameters)

    if not result.ok: # uh oh!
        error = result.json()["error"]
        raise WeatherAPIError(error["code"], error["message"])

    response = result.json()
    print(response)

    await interaction.response.defer()
    channel = client.get_channel(interaction.channel_id)
    guild = str(client.get_guild(interaction.guild_id)) if interaction.guild_id else "0"

    system_prompt = f"{json.dumps(response)}, please summarize this information" # convert response into json-formatted
                                                                                 # string
    store_messages(str(interaction.guild_id), str(interaction.channel_id), location, "user", str(interaction.user.id))
    findresponse = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(response)},
        ], options = {'temperature': 0.4}
    )
    store_messages(str(interaction.guild_id), str(interaction.channel_id),
    findresponse.message.content, "assistant", str(client.user.id))

    botresponse = findresponse.message.content
    for i in range(0, len(botresponse), 2000):
        await interaction.followup.send(botresponse[i:i + 2000])

    await client.process_commands(response)
    await interaction.channel.send(botresponse[i:i + 2000])


client.run(TOKEN)
