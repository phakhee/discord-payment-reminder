import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from classes.FirebaseManager import firebase_manager
from interactions.ext.paginator import Page, Paginator
from interactions import Client, Intents, Option, OptionType, CommandContext, Embed, Member

load_dotenv()

server_name = os.getenv("SERVER_NAME")
discord_token = os.getenv("DISCORD_CLIENT_TOKEN")
guild_id = int(os.getenv("GUILD_ID"))

webhook_color = int(os.getenv("WEBHOOK_COLOR"))
webhook_icon = os.getenv("WEBHOOK_ICON")
webhook_name = os.getenv("WEBHOOK_NAME")

allowed_roles = os.getenv("ALLOWED_ROLES").split(",")

client = Client(
    token=discord_token,
    default_scope=guild_id,
    intents=Intents.DEFAULT | Intents.GUILD_MESSAGE_CONTENT
)


@client.event
async def on_ready():
    print(f"{webhook_name} is online")
    event_loop = asyncio.get_running_loop()
    asyncio.ensure_future(firebase_manager.monitor(client), loop=event_loop)


def is_allowed(user_roles):
    u_roles = [str(role) for role in user_roles]
    for role in u_roles:
        if role in allowed_roles:
            return True

    return False


def divide_chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]


@client.command(
    name="update_payment_link",
    description="Update bank transfer payment link",
    scope=guild_id,
    options=[
        Option(
            name="url",
            description="The payment link url.",
            type=OptionType.STRING,
            required=True
        ),
        Option(
            name="is_og",
            description="Checks if the user's member role is OG or new.",
            type=OptionType.BOOLEAN,
            required=True
        )
    ]
)
async def update_payment_link(ctx: CommandContext, url: str, is_og: bool):
    if is_allowed(ctx.author.roles):
        firebase_manager.update_payment_link(url, is_og)
        embed = Embed(
            title=f"Successfully updated{' OG ' if is_og else ' '}payment link!",
            color=webhook_color
        )
        embed.add_field(name="New URL", value=url)
        embed.set_footer(icon_url=webhook_icon, text=webhook_name)

        await ctx.send(embeds=[embed])
    else:
        await ctx.send("User is not allowed to run this command")


@client.command(
    name="active_bank_transfers",
    description="Get all active bank transfers",
    scope=guild_id
)
async def active_bank_transfers(ctx: CommandContext):
    if is_allowed(ctx.author.roles):
        transfers = firebase_manager.active_bank_transfers()
        embeds = []
        embed_string = ""

        if transfers:
            partitioned_transfers = list(divide_chunks(transfers, 10))
            for p_transfers in partitioned_transfers:
                for transfer in p_transfers:
                    u_id = list(transfer.keys())[0]

                    embed_string += f"User ID: {u_id}\n"
                    embed_string += f"Username: {transfer[u_id]['user_name']}\n"
                    embed_string += f"Renewal date: {transfer[u_id]['renewal_date']}\n\n"

                embed_string = f"```{embed_string}```"
                embed = Embed(
                    title=server_name,
                    color=webhook_color,
                    description=embed_string
                )
                embed.set_footer(text=webhook_name, icon_url=webhook_icon)
                embeds.append(embed)
                embed_string = ""
        else:
            embed_string = "No active bank transfers found"
            embed = Embed(
                title="All active bank transfers",
                color=webhook_color,
                description=embed_string
            )
            embed.set_footer(icon_url=webhook_icon, text=webhook_name)
            embeds.append(embed)

        if len(embeds) == 1:
            await ctx.send(embeds=embeds)
        else:
            embeds = [Page(embeds=[embed]) for embed in embeds]
            await Paginator(
                client=client,
                ctx=ctx,
                pages=embeds,
            ).run()
    else:
        await ctx.send("User is not allowed to run this command")


@client.command(
    name="start_bank_transfer",
    description="Create and add new bank transfer for a user.",
    scope=guild_id,
    options=[
        Option(
            name="user",
            description="The user attached to the bank transfer",
            type=OptionType.USER,
            required=True
        ),
        Option(
            name="date",
            description="The date when the user is required to pay the bank transfer, for example: 16-08-22",
            type=OptionType.STRING,
            required=True
        ),
        Option(
            name="is_og",
            description="Checks if the user's member role is OG or new.",
            type=OptionType.BOOLEAN,
            required=True
        )
    ]
)
async def start_bank_transfer(ctx: CommandContext, user: Member, date: str, is_og: bool):
    if is_allowed(ctx.author.roles):
        r_date = datetime.strptime(date, "%d-%m-%y")
        data = {
            "user_id": str(user.id),
            "user_name": str(user.user.username),
            "renewal_date": r_date.isoformat(),
            "has_channel": False,
            "channel_id": "",
            "reminders": {
                "first_day": False,
                "second_day": False,
                "fourth_day": False,
                "sixth_day": False
            },
            "is_og": is_og
        }
        data, exists = firebase_manager.start_bank_transfer(data)

        embed_text = f"Bank overschrijving aangemaakt voor <@{data['user_id']}>" if not exists \
            else f"Bank overschrijving bestaat al voor <@{data['user_id']}>"

        embed = Embed(
            title=server_name,
            color=webhook_color,
            description=embed_text,
        )
        embed.add_field(name="Transfer ID", value=data["id"])
        embed.add_field(name="User ID", value=data["user_id"])
        embed.add_field(name="Renewal date", value=data["renewal_date"])
        embed.add_field(name="Is OG", value=data["is_og"])
        embed.set_footer(text=webhook_name, icon_url=webhook_icon)

        await ctx.send(embeds=embed)
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if (today - datetime.fromisoformat(r_date.isoformat())).days == 0 and not data["has_channel"]:
            await firebase_manager.create_channel(
                await ctx.get_guild(),
                (str(user.id), str(user.user.username), r_date)
            )

    else:
        await ctx.send("User is not allowed to run this command")


@client.command(
    name="add_days",
    description="Add days to the renewal day of existing bank transfers",
    scope=guild_id,
    options=[
        Option(
            name="user",
            description="Which user's bank transfer to add days to.",
            type=OptionType.USER,
            required=True
        ),
        Option(
            name="amount_of_days",
            description="The amount of days to be added to the renewal date.",
            type=OptionType.INTEGER,
            required=True
        )
    ]
)
async def add_days(ctx: CommandContext, user: Member, amount_of_days: int):
    if is_allowed(ctx.author.roles):
        data = firebase_manager.add_days(str(user.id), amount_of_days)
        embed = Embed(
            title=server_name,
            color=webhook_color
        )
        embed.set_footer(text=webhook_name, icon_url=webhook_icon)

        if data:
            embed.description = f"{amount_of_days} dag(en) toegevoegd aan de renewal van <@{user.id}>"
            embed.add_field(name="New renewal date", value=data["renewal_date"])
        else:
            embed.description = f"Geen bank overschrijving gevonden voor <@{user.id}>"

        await ctx.send(embeds=[embed])
    else:
        await ctx.send("User is not allowed to run this command")


@client.command(
    name="end_bank_transfer",
    description="End an existing bank transfer",
    scope=guild_id,
    options=[
        Option(
            name="user",
            description="Which user's bank transfer to delete",
            type=OptionType.USER,
            required=True
        ),
        Option(
            name="paid",
            description="Whether the bank transfer is paid or not.",
            type=OptionType.BOOLEAN,
            required=True
        )
    ]
)
async def end_bank_transfer(ctx: CommandContext, user: Member, paid: bool):
    if is_allowed(ctx.author.roles):
        data = {
            "user_id": str(user.id),
            "paid": paid
        }
        data = firebase_manager.end_bank_transfer(data)

        embed = Embed(
            title=server_name,
            color=webhook_color
        )
        embed.set_footer(text=webhook_name, icon_url=webhook_icon)

        if data:
            guild = await ctx.get_guild()
            channel = [
                c for c in await guild.get_all_channels()
                if str(c.id) == data["channel_id"]
            ]

            embed.description = f"<@{str(user.id)}> {'heeft' if paid else 'heeft niet'} de renewal betaald."
            await ctx.send(embeds=[embed])

            if len(channel) > 0:
                channel = channel[0]

                await channel.send(embeds=[embed])
                await channel.delete()
        else:
            embed.description = f"Geen bank overschrijving gevonden voor <@{str(user.id)}>"
            await ctx.send(embeds=[embed])
    else:
        await ctx.send("User is not allowed to run this command")


client.start()
