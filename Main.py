import discord
from discord.ext import commands
import os
from datetime import tzinfo, timedelta, datetime
from discord.utils import get

tank = "<:tank:850946014348050432>"
healer = "<:healer:850945923592880178>"
damage = "<:damage:850946049421213736>"
role = ""
characterName = ""
checkmark = "<:white_check_mark:212e30e47232be03033a87dc58edaa95>"
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command("help")

# TODO: UPDATE THIS BEFORE SENDING TO HITP
officer_role = "Threes Company"
member_role = "Raider"

# Checks if user has role with same name as parameter officer_roll
def an_officer(ctx):
    author = ctx.message.author
    author_roles = []
    for person in author.roles:
        author_roles.append(str(person))
    if officer_role in author_roles:
        return True
    else:
        return False


# Makes a channel with format username-discriminator-mon-day-year
async def make_officer_channel(user, guild_id):
    now = datetime.now()
    dt = now.strftime("%m-%d-%y")
    channel_name = characterName + '-' + dt
    cata_obj = bot.get_channel(int(open("officer_category.txt").readline().rstrip()))
    channel = await guild_id.create_text_channel(name=channel_name, category=cata_obj)
    # Set user permissions for Bot first, everyone else, officers, then the person applying
    await channel.set_permissions(bot.user, read_messages=True, send_messages=True)
    await channel.set_permissions(guild_id.default_role, read_messages=False, send_messages=False)
    await channel.set_permissions(discord.utils.get(guild_id.roles, name=officer_role),
                                  read_messages=True, send_messages=True)
    await channel.set_permissions(user, read_messages=True, send_messages=True)
    return channel


async def make_member_channel(user, guild_id):
    now = datetime.now()
    dt = now.strftime("%m-%d-%y")
    channel_name = characterName + '-' + dt
    cata_obj = bot.get_channel(int(open("member_category.txt").readline().rstrip()))
    channel = await guild_id.create_text_channel(name=channel_name, category=cata_obj)
    # Set user permissions for Bot first, everyone else, officers, then the person applying
    await channel.set_permissions(bot.user, read_messages=True, send_messages=True)
    await channel.set_permissions(guild_id.default_role, read_messages=False, send_messages=False)
    await channel.set_permissions(discord.utils.get(guild_id.roles, name=member_role),
                                  read_messages=True, send_messages=True)
    return channel


# Build content for the app that Members can see. Breaks apart apps at the 1800 char mark to avoid discord issues.
async def build_normal_app(user, application):
    guild_id = bot.get_guild(int(open("guild.txt").readline().rstrip()))
    channel = await make_member_channel(user, guild_id)
    officer_app = ''
    if len(application) <= 1800:
        embed = discord.Embed(color=0x00ffff, description=application)
        await channel.send(embed=embed)
        return
    else:
        app_content = application.split("\n")
        for item in app_content:
            if len(officer_app) + len(item) > 1800:
                embed = discord.Embed(color=0x00ffff, description=officer_app)
                await channel.send(embed=embed)
                officer_app = ''
            officer_app += item + "\n"

    embed = discord.Embed(color=0x00ffff, description=officer_app)
    await channel.send(embed=embed)


# Build content for the app that the officers can see. Breaks apart apps at the 1800 char mark to avoid discord issues.
# It will also make a channel for the officers and the applicant to communicate privately if needed.
async def build_officer_app(user, application):
    guild_id = bot.get_guild(int(open("guild.txt").readline().rstrip()))
    channel = await make_officer_channel(user, guild_id)

    officer_app = ''
    if len(application) <= 1800:
        embed = discord.Embed(color=0x00ffff, description=application)
        await channel.send(embed=embed)
        return
    else:
        app_content = application.split("\n")
        for item in app_content:
            if len(officer_app) + len(item) > 1800:
                embed = discord.Embed(color=0x00ffff, description=officer_app)
                await channel.send(embed=embed)
                officer_app = ''
            officer_app += item + "\n"

    embed = discord.Embed(color=0x00ffff, description=officer_app)
    await channel.send(embed=embed)


# Parses message history between bot and applicant to create an application for submission.
# NOTE: MESSAGE HISTORY IS ATTACHED TO BOT BEING ONLINE.  If the bot goes down the message history can NOT be parsed.
async def build_application(reaction, user):
    global characterName
    app_content = []
    async for message in reaction.message.channel.history(limit=200):
        if message.embeds and message.author == bot.user:
            if len(message.embeds) > 0:
                #Parse bots own messages for embeds, using those to know when we have reached the first question
                if not isinstance(message.embeds[0].title, discord.embeds._EmptyEmbed):
                    app_content.append(message.embeds[0].description)
                    if message.embeds[0].title == "Q1":
                        break
        elif message.author == bot.user:
            # We dont care about other messages that the bot has sent during this time.
            continue
        else:
            if message.embeds:
                app_content.append(message.clean_content)
            else:
                app_content.append(message.content)

    application = "----------NEW-Speakeasy Raider Application----------\n\n"
    app_content.reverse()
    app_content.pop()
    characterName = app_content[1].replace(" ", "-")
    count = 1
    app_content.insert(11, role)
    for item in app_content:
        if count % 2:
            item = "**" + item + "**"
        application += item + "\n"
        count += 1
        if count % 2:
            application += "\n"

    now = datetime.now()
    dt = now.strftime("%m/%d/%Y, %H:%M:%S")
    application += "\nDate of Application: " + str(dt) + "\nName of Applicant: "
    application += user.name + "#" + user.discriminator

    await build_normal_app(user, application)
    await build_officer_app(user, application)


# Thanks applicant and sends the first question
async def start_application(ctx):
    embed = discord.Embed(color=0x00ffff, description=open("app_start.txt").readline().rstrip())
    await ctx.author.send(embed=embed)

    q_file = os.path.join(os.getcwd(), "Questions", "Q1.txt")
    embed = discord.Embed(title="Q1", color=0x00ffff, description=open(q_file).readline().rstrip())
    await ctx.author.send(embed=embed)


# Uses previous question number to determine the current question to output
# If we are on final question then add a reaction in order to allow user to submit their application.
async def fetch_next_question(ctx, question_number):
    
    question_cap = determine_final_question("Q")
    current_question = int(question_number[1:])
    if current_question != question_cap:
        next_question = int(question_number[1:])+1
        q_file = os.path.join(os.getcwd(), "Questions", "Q%s.txt" % next_question)
        embed = discord.Embed(title="Q%s" % next_question, color=0x00ffff, description=open(q_file).readline().rstrip())
        message = await ctx.author.send(embed=embed)
        if next_question == 6:
            await message.add_reaction(tank)
            await message.add_reaction(healer)
            await message.add_reaction(damage)
        if next_question == question_cap:
            await message.add_reaction('\N{White Heavy Check Mark}')
            await message.add_reaction('\N{Cross Mark}')

async def fetch_next_question_tank(ctx, question_number):
    
    question_cap = determine_final_question("T")
    current_question = int(question_number[1:])
    if current_question != question_cap:
        next_question = int(question_number[1:])+1
        q_file = os.path.join(os.getcwd(), "Questions", "T%s.txt" % next_question)
        embed = discord.Embed(title="T%s" % next_question, color=0x00ffff, description=open(q_file).readline().rstrip())
        channel = ctx.channel
        message = await channel.send(embed=embed)
        if next_question == question_cap:
            await message.add_reaction('\N{White Heavy Check Mark}')
            await message.add_reaction('\N{Cross Mark}')
async def fetch_next_question_healer(ctx, question_number):
    
    question_cap = determine_final_question("H")
    current_question = int(question_number[1:])
    if current_question != question_cap:
        next_question = int(question_number[1:])+1
        q_file = os.path.join(os.getcwd(), "Questions", "H%s.txt" % next_question)
        embed = discord.Embed(title="H%s" % next_question, color=0x00ffff, description=open(q_file).readline().rstrip())
        channel = ctx.channel
        message = await channel.send(embed=embed)
        if next_question == question_cap:
            await message.add_reaction('\N{White Heavy Check Mark}')
            await message.add_reaction('\N{Cross Mark}')

async def fetch_next_question_dps(ctx, question_number):
    
    question_cap = determine_final_question("D")
    current_question = int(question_number[1:])
    if current_question != question_cap:
        next_question = int(question_number[1:])+1
        q_file = os.path.join(os.getcwd(), "Questions", "D%s.txt" % next_question)
        embed = discord.Embed(title="D%s" % next_question, color=0x00ffff, description=open(q_file).readline().rstrip())
        channel = ctx.channel
        message = await channel.send(embed=embed)
        if next_question == question_cap:
            await message.add_reaction('\N{White Heavy Check Mark}')
            await message.add_reaction('\N{Cross Mark}')

# Parse file names to determine last question
def determine_final_question(role):
    count = 0
    q_files = os.path.join(os.getcwd(), "Questions")
    for file in os.listdir(q_files):
        if file.startswith(role):
            count += 1
    return count

# If the final question has been reacted to (and its not the bots own reaction) then route the application.
@bot.event
async def on_reaction_add(reaction, user):
    global role 
    if reaction.me and reaction.count > 1:
        print(reaction.emoji)
        if reaction.emoji == '\N{White Heavy Check Mark}':
            async for message in reaction.message.channel.history(limit=200):
                if message.content == "**Your application has been submitted**":
                    await user.send("You have already submitted an application, if you would "
                                    "like to apply again type !apply")
                    return
                if message.embeds:
                    if len(message.embeds) > 0:
                        if not isinstance(message.embeds[0].title, discord.embeds._EmptyEmbed):
                            #last_q = "Q%s" % determine_final_question()
                            #if message.embeds[0].title == last_q:
                                await user.send("**Your application has been submitted** \nWe will contact you in less than 1 week if we are interested. Thank you!")
                                await build_application(reaction, user)
                                break
        if str(reaction.emoji) == tank:
            role = "Tank"
            await fetch_next_question_tank(reaction.message, "T0")
        if str(reaction.emoji) == healer:
            role = "Healer"
            await fetch_next_question_healer(reaction.message, "H0")
        if str(reaction.emoji) == damage:
            role = "DPS"
            await fetch_next_question_dps(reaction.message, "D0")            



# Initial application command, checks if user if on blacklist. Will let them know if so, if not calls for app start.
# TODO: Update so existing members can not apply.
@bot.command(pass_context=True)
async def apply(ctx):

    author = ctx.author.name + "#" + ctx.author.discriminator

    blacklist_txt = open('blacklist.txt').readline().rstrip()
    if author in blacklist_txt:
        embed = discord.Embed(title="Denied", color=0x00ffff, description="You have been blacklisted "
                                                                          "from applying, please contact an officer.")
        await ctx.author.send(embed=embed)
        if not isinstance(ctx.channel, discord.DMChannel):
            await ctx.message.delete()
        return

    await start_application(ctx)

    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.message.delete()


# Checks all messages bot can see. Process commands as needed, but if the message is in a DM it might be an application
# in this case we need to fetch the next question in line.
@bot.event
async def on_message(ctx):
    if ctx.content.startswith("!"):
        await bot.process_commands(ctx)
        return

    if not ctx.author.bot:
        if isinstance(ctx.channel, discord.DMChannel):
            async for message in ctx.channel.history(limit=200):
                if message.author.bot and len(message.embeds) > 0:
                    print(message.embeds[0].title)
                    if message.embeds[0].title.startswith("Q"):
                        await fetch_next_question(ctx, message.embeds[0].title.replace(':', ''))
                        break
                    if message.embeds[0].title.startswith("T"):
                        await fetch_next_question_tank(ctx, message.embeds[0].title.replace(':', ''))
                        break
                    if message.embeds[0].title.startswith("H"):
                        await fetch_next_question_healer(ctx, message.embeds[0].title.replace(':', ''))
                        break
                    if message.embeds[0].title.startswith("D"):
                        await fetch_next_question_dps(ctx, message.embeds[0].title.replace(':', ''))
                        break
                    


# Clear chat history. Only works on messages with freshness of 2 weeks, and up to 200 at a time.
@bot.command(pass_context=True)
async def clear(ctx):
    if not an_officer(ctx):
        if not isinstance(ctx.channel, discord.DMChannel):
            await ctx.message.delete()
        return
    count = ctx.message.content.replace("!clear ", '')
    if count.isdigit():
        async for message in ctx.channel.history(limit=int(count)+1):
            await message.delete()
    else:
        return await ctx.channel.send("!Clear must have an integer number!")


# Sends help message containing all the commands
@bot.command(pass_context=True)
async def help(ctx):
    file = open("help.txt", 'r')
    lines = file.readlines()
    info = '```'
    for line in lines:
        info += line
    info += '```'
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.message.delete()
    return await ctx.channel.send(info)


# Provides full blacklist
@bot.command(pass_context=True)
async def banned(ctx):
    with open('blacklist.txt') as f:
        line_count = 0
        for line in f:
            line_count += 1
    if line_count > 0:
        file = open("blacklist.txt", 'r')

        lines = file.readlines()
        info = '```'
        for line in lines:
            info += line
        info += '```'
        embed = discord.Embed(color=0x00ffff, description=info)
        await ctx.channel.send(embed=embed)
    else:
        embed = discord.Embed(color=0x00ffff, description="```No users are blacklisted!```")
        await ctx.channel.send(embed=embed)
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.message.delete()


# Accepts users into the guild. Requires 1 member and their assigned role. Sends a greeting by default, but can also
# send customized messages.
@bot.command(pass_context=True)
async def accept(ctx):
    if not an_officer(ctx):
        return

    if len(ctx.message.mentions) == 0:
        return await ctx.channel.send("You must include a person and role in order to !accept them")
    if len(ctx.message.role_mentions) == 0:
        return await ctx.channel.send("You must include a person and role in order to !accept them")
    if len(ctx.message.mentions) > 1:
        return await ctx.channel.send("Please only attach 1 person and 1 role to each !accept")
    if len(ctx.message.role_mentions) > 1:
        return await ctx.channel.send("Please only attach 1 person and 1 role to each !accept")

    user = ctx.message.mentions[0]
    user_id = user.id
    role = ctx.message.role_mentions[0].id

    strip_message = ctx.message.system_content.replace('!accept', '')
    strip_message = strip_message.replace("<@&" + str(role) + ">", '')
    strip_message = strip_message.replace("<@!" + str(user_id) + ">", '')
    strip_message = strip_message.replace("<@" + str(user_id) + ">", '')

    guest_role = discord.utils.get(ctx.guild.roles, name='Guest')

    await user.add_roles(ctx.message.role_mentions[0])
    await user.remove_roles(guest_role)
    if len(strip_message.replace(' ', '')) > 0:
        embed = discord.Embed(color=0x00ffff, description=strip_message)
        await user.send(embed=embed)
        channel_send = "The following message has been sent to %s#%s" % (user.name, user.discriminator)
        channel_send += "```" + strip_message + "```"
        embed = discord.Embed(color=0x00ffff, description=channel_send)
        await ctx.channel.send(embed=embed)

    else:
        q_file = os.path.join(os.getcwd(), "Questions", "TY.txt")
        embed = discord.Embed(color=0x00ffff, description=open(q_file).readline().rstrip())
        await user.send(embed=embed)
        channel_send = "The following message has been sent to %s#%s" % (user.name, user.discriminator)
        channel_send += "```" + open(q_file).readline().rstrip() + "```"
        embed = discord.Embed(color=0x00ffff, description=channel_send)
        await ctx.channel.send(embed=embed)


# Same as Accept, but only for rejection letters. Just requires 1 member.
@bot.command(pass_context=True)
async def reject(ctx):
    if not an_officer(ctx):
        return

    if len(ctx.message.mentions) == 0:
        return await ctx.channel.send("You must include a person !reject them")
    if len(ctx.message.mentions) > 1:
        return await ctx.channel.send("Please only attach 1 person and 1 role to each !accept")
    if len(ctx.message.role_mentions) > 0:
        return await ctx.channel.send("This is a !reject command. Did you mean !accept?")

    user = ctx.message.mentions[0]
    user_id = user.id
    strip_message = ctx.message.system_content.replace('!reject', '')
    strip_message = strip_message.replace("<@!" + str(user_id) + ">", '')

    if len(strip_message.replace(' ', '')) > 0:
        embed = discord.Embed(color=0x00ffff, description=strip_message)
        await user.send(embed=embed)
        channel_send = "The following message has been sent to %s#%s" % (user.name, user.discriminator)
        channel_send += "```" + strip_message + "```"
        embed = discord.Embed(color=0x00ffff, description=channel_send)
        await ctx.channel.send(embed=embed)
    else:
        q_file = os.path.join(os.getcwd(), "Questions", "NOTY.txt")
        embed = discord.Embed(color=0x00ffff, description=open(q_file).readline().rstrip())
        await user.send(embed=embed)
        channel_send = "The following message has been sent to %s#%s" % (user.name, user.discriminator)
        channel_send += "```" + open(q_file).readline().rstrip() + "```"
        embed = discord.Embed(color=0x00ffff, description=channel_send)
        await ctx.channel.send(embed=embed)


# Initial setup for bot, determines channel that will contain ALL the applications
@bot.command(pass_context=True)
async def guild(ctx):
    if not an_officer(ctx):
        return
    with open("channel.txt", "w") as f:
        f.write(str(ctx.channel.id))
    embed = discord.Embed(color=0x00ffff, description="```Applications will now be submitted to this channel!```")
    await ctx.channel.send(embed=embed)


@bot.command(pass_context=True)
async def member_here(ctx):
    if not an_officer(ctx):
        return
    with open("member_category.txt", "w") as f:
        f.write(str(ctx.channel.category_id))
    with open("guild.txt", "w") as f:
        f.write(str(ctx.guild.id))
    embed = discord.Embed(color=0x00ffff, description="```Member versions of "
                                                      "Applications will now be submitted to this category!```")
    await ctx.channel.send(embed=embed)


@bot.command(pass_context=True)
async def officer_here(ctx):
    if not an_officer(ctx):
        return
    with open("officer_category.txt", "w") as f:
        f.write(str(ctx.channel.category_id))
    with open("guild.txt", "w") as f:
        f.write(str(ctx.guild.id))
    embed = discord.Embed(color=0x00ffff, description="```Officer versions of "
                                                      "Applications will now be submitted to this category!```")
    await ctx.channel.send(embed=embed)


@bot.command(pass_context=True)
async def officer_archive(ctx):
    if not an_officer(ctx):
        return
    with open("officer_archive.txt", "w") as f:
        f.write(str(ctx.channel.category_id))
    with open("guild.txt", "w") as f:
        f.write(str(ctx.guild.id))
    embed = discord.Embed(color=0x00ffff, description="```Officer Discussions will be archived here!```")
    await ctx.channel.send(embed=embed)


@bot.command(pass_context=True)
async def member_archive(ctx):
    if not an_officer(ctx):
        return
    with open("member_archive.txt", "w") as f:
        f.write(str(ctx.channel.category_id))
    with open("guild.txt", "w") as f:
        f.write(str(ctx.guild.id))
    embed = discord.Embed(color=0x00ffff, description="```Member Discussions will be archived here!```")
    await ctx.channel.send(embed=embed)

# Sends user an embed containing ALL application questions (minus the final 'Are you sure?' question)
@bot.command(pass_context=True)
async def questions(ctx):
    content = ''
    question_cap = determine_final_question()
    for i in range(1, question_cap):
        current_question = i
        if current_question != question_cap:
            next_question = i
            q_file = os.path.join(os.getcwd(), "Questions", "Q%s.txt" % next_question)
            content += str(current_question) + ") " + open(q_file).readline().rstrip() + "\n\n"
    embed = discord.Embed(title="Questions!", color=0x00ffff, description=content)
    await ctx.author.send(embed=embed)
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.message.delete()


# Blacklists a user.
@bot.command(pass_context=True)
async def blacklist(ctx):
    if not an_officer(ctx):
        return

    if len(ctx.message.mentions) == 0:
        return await ctx.channel.send("You must include 1 person in order to !blacklist them")
    if len(ctx.message.mentions) > 1:
        return await ctx.channel.send("Please only attach 1 person to !blacklist")

    user = ctx.message.mentions[0]
    user_id = user.id
    f = open("blacklist.txt", "a+")
    f.write(str(user)+"\n")
    f.close()
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.message.delete()
    return await ctx.channel.send("<@%s> has been blacklisted!" % str(user_id))


# Removes a user from blacklist
@bot.command(pass_context=True)
async def whitelist(ctx):
    if not an_officer(ctx):
        return

    if len(ctx.message.mentions) == 0:
        return await ctx.channel.send("You must include 1 person in order to !whitelist them")
    if len(ctx.message.mentions) > 1:
        return await ctx.channel.send("Please only attach 1 person to !whitelist")

    user = ctx.message.mentions[0]
    user_id = user.id

    with open('blacklist.txt') as f:
        line_count = 0
        for line in f:
            line_count += 1
    banned_list = open('blacklist.txt').readline().rstrip()

    f = open("blacklist.txt", "w+")
    if line_count > 1:
        for line in banned_list:
            if str(user) != line:
                f.write(line)
    else:
        if banned_list != str(user):
            f.write(banned_list)

    f.close()
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.message.delete()
    return await ctx.channel.send("<@%s> has been whitelisted!" % str(user_id))


# Configures default messages for !Accept and !Reject
@bot.command(pass_context=True)
async def default(ctx):
    if not an_officer(ctx):
        return

    if ctx.message.content.lower().startswith("!default accept "):
        q_file = os.path.join(os.getcwd(), "Questions", "YTY.txt")
        f = open(q_file, "w+")
        default_update = ctx.message.content[len("!default accept "):]
        f.write(default_update)
        f.close()
        message = "Default reply on accept is now:```" + default_update + "```"
        embed = discord.Embed(color=0x00ffff, description=message)
        await ctx.channel.send(embed=embed)
        if not isinstance(ctx.channel, discord.DMChannel):
            await ctx.message.delete()
    elif ctx.message.content.lower().startswith("!default reject "):
        q_file = os.path.join(os.getcwd(), "Questions", "NOTY.txt")
        f = open(q_file, "w+")
        default_update = ctx.message.content[len("!default reject "):]
        f.write(default_update)
        f.close()
        message = "Default reply on reject is now:```" + default_update + "```"
        embed = discord.Embed(color=0x00ffff, description=message)
        await ctx.channel.send(embed=embed)
        if not isinstance(ctx.channel, discord.DMChannel):
            await ctx.message.delete()
    else:
        await ctx.channel.send("No '!default accept' or '!default reject' detected!")


# Moves application to designated category, NOTE THE CHANNEL MUST HAVE A VALID USER ID AT THE START.
@bot.command(pass_context=True)
async def archive(ctx):
    if not an_officer(ctx):
        return

    if ctx.channel.category_id == int(open("member_category.txt").readline().rstrip()):
        category_id = int(open("member_archive.txt").readline().rstrip())
    elif ctx.channel.category_id == int(open("officer_category.txt").readline().rstrip()):
        category_id = int(open("officer_archive.txt").readline().rstrip())
    else:
        return
    cata_obj = bot.get_channel(category_id)
    channel = ctx.channel
    channel_member_list = ctx.channel.members
    bot_name = bot.user.name

    for member_check in channel_member_list:
        if member_check.name != bot_name and officer_role not in member_check.roles:
            await channel.set_permissions(member_check, read_messages=False, send_messages=False)

    await channel.edit(category=cata_obj)
    embed = discord.Embed(color=0x00ffff, description="```This application will now be archived, members "
                                                          "will be removed from accessing this channel```")
    await channel.send(embed=embed)
    await channel.set_permissions(discord.utils.get(channel.guild.roles, name=member_role),
                                        read_messages=False, send_messages=False)

@bot.command(pass_context=True)
async def delete(ctx):
    if not an_officer(ctx):
        return
    await ctx.channel.delete(reason="app deleted")
    return

# Basic Startup validation.
@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print('------')

# Starts bot using dev token.
bot.run(open("token.txt").readline().rstrip())

