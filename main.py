import re
import os
import keep_alive
import pymongo
import discord
import asyncio
import requests
from discord.ext import commands
from discord import app_commands
from discord.ext.commands import has_permissions
from dotenv import load_dotenv


load_dotenv()

#initialise bot and set command prefix
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(intents=intents, command_prefix="$")

#connect to mongodb
cluster = pymongo.MongoClient(os.getenv('MONGODB_CONNECTOR'))
dbname = cluster["AltNames"]


def is_me():
  def predicate(interaction: discord.Interaction) -> bool:
    return interaction.user == os.getenv("USERID")
  return app_commands.check(predicate)

def check():
  def predicate(interaction: discord.Interaction) -> bool:
    return interaction.user == os.getenv("USERID")
  return app_commands.check(predicate) and app_commands.check(has_permissions(manage_roles=True))

@bot.command(
  help="Add a user's alt name to names database. Format: $add MainName AltName",
  brief="Add alt.")
@check()
async def add(ctx, mainName, *args):
  print(len(args))
  for item in args:
    #add a new user to database
    dbname.Alts.insert_one({
      "server_id": ctx.guild.id,
      "name": mainName.strip(",").capitalize(),
      "altName": item.strip(",").capitalize()
    })
  embedVar = discord.Embed(title="Adding alt for Player:",
                           description="",
                           color=0x00ff00)
  embedVar.add_field(name=mainName,
                     value=convertTupleToString(args).title(),
                     inline=False)
  msg = await ctx.send(embed=embedVar)
  await msg.add_reaction('\u274c')
  if await checkReaction(msg, ctx) == True:
    await ctx.send(f"Removing alt: {convertTupleToString(args).title()}...")
    for item in args:
      dbname.Alts.delete_one({
        "server_id": ctx.guild.id,
        "name": mainName.capitalize(),
        "altName": item.strip(",").capitalize()
      })
  return


@bot.command(
  help=
  "Remove a user's information from the database. Format: $remove altName OR $remove mainName removes all instances of alt or main found",
  brief="Removes added alt/main.")
@check()
async def remove(ctx, name):
  dbname.Alts.delete_many({
    "server_id": ctx.guild.id,
    "altName": name.capitalize()
  })
  dbname.Alts.delete_many({"server_id": ctx.guild.id, "name": name.capitalize()})
  dbname.Alts.delete_many({"server_id": ctx.guild.id, "altName": name})
  dbname.Alts.delete_many({"server_id": ctx.guild.id, "name": name})
  await ctx.send(f"all instances of {name.capitalize()} removed.")


@bot.command(help="Lists all added main/alt combinations",
             brief="Lists all added main/alt combinations")
@check()
async def list(ctx):
  users = "The following main/alt combinations have been added:\n"
  for x in dbname.Alts.find({"server_id": ctx.guild.id}, {
      "name": 1,
      "altName": 1
  }):
    if  len(users) + len(str(x["name"]).capitalize() + " - " + str(x["altName"]).capitalize() + "\n") > 2000:
      await ctx.send(users)
      users =""
    users = users + str(x["name"]).capitalize() + " - " + str(x["altName"]).capitalize() + "\n"
  if  len(users) > 0:
    await ctx.send(users)
  return

#LISTENER


@bot.listen('on_message')
async def my_message(ctx):
  search = re.compile('RaidRoster_(\w+)-(\d+)-(\d+)\.txt')
  try:
    if ctx.attachments[0].url and not ctx.author.bot:
      print(f'\nNew attachment recieved from {str(ctx.author)}.')
      print(f'Attachment Link: {ctx.attachments[0].url}\n')
      if re.search(search, ctx.attachments[0].filename):
        r = requests.get(ctx.attachments[0].url, allow_redirects=True)
        fileName = f"Translated_{ctx.attachments[0].filename}"
        with open("translations/" + fileName, 'wb') as file:
          file.write(r.content)
        with open("translations/" + fileName, 'r') as file:
          filedata = file.read()
        for x in dbname.Alts.find({"server_id": ctx.guild.id}, {
            "name": 1,
            "altName": 1
        }):
          if str(x["altName"]).capitalize() in filedata:
            filedata = filedata.replace(
              str(x["altName"]).capitalize(),
              str(x["name"]).capitalize())
          else:
            continue
        with open("translations/" + fileName, 'w') as file:
          file.write(filedata)
          print("conversion finished")
        await ctx.channel.send(file=discord.File("translations/" + fileName),
                               content="Alt names translated...")
        if os.path.exists("translations/" + fileName):
          os.remove("translations/" + fileName)

  except:
    pass


#FUNCTIONS
def convertTupleToString(tup):
  return ' '.join([str(x) for x in tup])


async def checkReaction(msg, ctx):

  def check(reaction, user):
    return user == ctx.author and str(
      reaction.emoji) in ['\u274c'] and reaction.message == msg

  try:
    confirmation = await bot.wait_for("reaction_add",
                                      timeout=10.0,
                                      check=check)
    if confirmation:
      return True
  except asyncio.TimeoutError:
    return


#ERROR HANDLING


@add.error
async def add_error(ctx, error):
  if isinstance(error, commands.MissingRequiredArgument):
    await ctx.send("Add requires both mainName and altName.")
    return
  else:
    await ctx.send(error)

keep_alive.keep_alive()

bot.run(os.getenv('TOKEN'))
