import pyrebase
import os
import uuid
import asyncio
from constants.reminders import REMINDERS
from datetime import datetime, timedelta
from classes.Singleton import Singleton
from dotenv import load_dotenv
from functions.messaging import log
from interactions import ChannelType, Overwrite, Permissions, Client, Channel, Guild, Embed, Role, Permission


class FirebaseManager(metaclass=Singleton):
    load_dotenv()

    def __init__(self):
        self.config = {
            "apiKey": os.getenv("FIREBASE_API_KEY"),
            "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
            "databaseURL": os.getenv("FIREBASE_DB_URL"),
            "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET")
        }
        self.category_id = os.getenv("CATEGORY_ID")
        self.allowed_roles = os.getenv("ALLOWED_ROLES").split(",")
        self.not_allowed_roles = os.getenv("NOT_ALLOWED_ROLES").split(",")
        self.muted_roles = os.getenv("MUTED_ROLES").split(",")
        self.role_mentions = ", ".join([f"<@&{role}>" for role in self.allowed_roles])

        self.firebase = pyrebase.initialize_app(self.config)
        self.db = self.firebase.database()

    def active_bank_transfers(self):
        _transfers = self.db.child("transfers").get()

        if _transfers.each():
            return [{transfer.key(): transfer.val()} for transfer in _transfers.each()]

        return False

    def start_bank_transfer(self, data):
        _transfer = self.db.child("transfers").child(data["user_id"]).get()

        if not _transfer.val():
            bank_transfer_id = str(uuid.uuid4())
            data["id"] = bank_transfer_id
            return self.db.child("transfers").child(data["user_id"]).set(data), False

        return dict(_transfer.val()), True

    def end_bank_transfer(self, data):
        _transfer = self.db.child("transfers").child(data["user_id"]).get()
        paid = data["paid"]

        if _transfer.val():
            transfer_data = _transfer.val()
            transfer_data["archived_at"] = datetime.now().isoformat()
            transfer_data["paid"] = paid

            if not paid:
                self.db.child("transfers").child(data["user_id"]).update(None)
            else:
                renewal_date = datetime.fromisoformat(_transfer.val()["renewal_date"])
                new_renewal_data = renewal_date + timedelta(days=30)

                self.db.child("transfers").child(data["user_id"]).update({
                    "renewal_date": new_renewal_data.isoformat(),
                    "has_channel": False,
                    "channel_id": "",
                    "reminders": {
                        "first_day": False,
                        "second_day": False,
                        "fourth_day": False,
                        "sixth_day": False
                    }
                })

            self.db.child("archived_transfers").child(str(uuid.uuid4())).set(transfer_data)

            return transfer_data

        return False

    def add_days(self, user_id: str, amount_of_days: int):
        _transfer = self.db.child("transfers").child(user_id).get()

        if _transfer.val():
            renewal_date = datetime.fromisoformat(_transfer.val()["renewal_date"])
            new_renewal_data = renewal_date + timedelta(days=amount_of_days)

            self.db.child("transfers").child(user_id).update({
                "reminders": {
                    "first_day": False,
                    "second_day": False,
                    "fourth_day": False,
                    "sixth_day": False
                }
            })

            return self.db.child("transfers").child(user_id).update({
                "renewal_date": new_renewal_data.isoformat()
            })

        return False

    async def monitor(self, client: Client):
        while True:
            try:
                current_guild = [guild for guild in client.guilds if str(guild.id) == os.getenv("GUILD_ID")][0]
                all_transfers = self.db.child("transfers").get()

                if all_transfers.each():
                    for transfer in all_transfers.each():
                        transfer_data = transfer.val()

                        user_name = transfer_data["user_name"]
                        user_id = transfer_data["user_id"]
                        has_channel = transfer_data["has_channel"]
                        channel_id = transfer_data["channel_id"]
                        reminders = transfer_data["reminders"]
                        renewal_date = datetime.fromisoformat(transfer_data["renewal_date"])
                        is_og = transfer_data["is_og"]

                        current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                        time_difference = (current_date - renewal_date).days

                        if 0 <= time_difference < 6:
                            if not has_channel:
                                channel = await self.create_channel(current_guild, (user_id, user_name, renewal_date))
                            else:
                                channel = [
                                    c for c in await current_guild.get_all_channels()
                                    if str(c.id) == channel_id
                                ][0]

                            embed_text = None
                            dm_text = None
                            for key, value in REMINDERS.items():
                                if time_difference == value["day_difference"] and not reminders[key]:
                                    embed_text = value["text"](user_id, self.role_mentions)
                                    dm_text = value["dm_text"](user_id, str(channel.id))
                                    reminders[key] = True
                                    self.update_transfer_data(user_id, {"reminders": reminders})

                            if embed_text:
                                embeds = []
                                embed = Embed(
                                    title=os.getenv("WEBHOOK_TITLE"),
                                    color=os.getenv("WEBHOOK_COLOR"),
                                    description=embed_text
                                )
                                embed.set_footer(
                                    icon_url=os.getenv("WEBHOOK_ICON"),
                                    text=os.getenv("WEBHOOK_NAME")
                                )
                                embeds.append(embed)

                                if time_difference == 0:
                                    info_embed = Embed(color=os.getenv("WEBHOOK_COLOR"))
                                    info_embed.add_field(name="User", value=user_name)
                                    info_embed.add_field(
                                        name="Renewal date",
                                        value=transfer_data["renewal_date"].split("T")[0]
                                    )
                                    info_embed.add_field(name="Is OG", value=is_og)
                                    info_embed.set_footer(
                                        icon_url=os.getenv("WEBHOOK_ICON"),
                                        text=os.getenv("WEBHOOK_NAME")
                                    )
                                    embeds.append(info_embed)

                                _payment_link = self.db.child("payment_link").get()

                                if _payment_link.val() and time_difference < 5:
                                    og_url = _payment_link.val()["og"]
                                    new_url = _payment_link.val()["new"]

                                    payment_link_embed = Embed(color=os.getenv("WEBHOOK_COLOR"))
                                    payment_link_embed.add_field(
                                        name="URL",
                                        value=f"[Klik hier]({og_url if is_og else new_url})"
                                    )
                                    payment_link_embed.set_footer(
                                        icon_url=os.getenv("WEBHOOK_ICON"),
                                        text=os.getenv("WEBHOOK_NAME")
                                    )
                                    embeds.append(payment_link_embed)

                                await channel.send(
                                    embeds=embeds,
                                    content=f"{self.role_mentions} & <@{user_id}>"
                                )

                                user = await current_guild.get_member(member_id=user_id)

                                try:
                                    embed.description = dm_text
                                    await user.send(embeds=[embed])
                                except Exception:
                                    log(f"{user_name} {user_id} has DMs turned off.")

                        elif time_difference >= 6:
                            data = {
                                "user_id": user_id,
                                "paid": False
                            }
                            self.end_bank_transfer(data)

                            if has_channel:
                                channel = [
                                    c for c in await current_guild.get_all_channels()
                                    if str(c.id) == channel_id
                                ][0]
                                await channel.delete()

                log("Bank transfers check done.")
            except Exception:
                log("Something went wrong getting transfers.")

            await asyncio.sleep(60)

    def update_transfer_data(self, user_id: str, data):
        self.db.child("transfers").child(user_id).update(data)

    def update_payment_link(self, payment_link: str, is_og: bool):
        self.db.child("payment_link").update({
            "og" if is_og else "new": payment_link
        })

    async def create_channel(self, current_guild: Guild, user: tuple):
        overwrites = []
        renewal_date: datetime = user[2]

        for role in self.allowed_roles:
            overwrites.append(Overwrite(
                id=int(role),
                type=0,
                allow=Permissions.VIEW_CHANNEL
            ))

        for role in self.not_allowed_roles:
            overwrites.append(Overwrite(
                id=int(role),
                type=0,
                deny=Permissions.VIEW_CHANNEL
            ))

        overwrites.append(Overwrite(
            id=int(user[0]),
            type=1,
            allow=Permissions.VIEW_CHANNEL | Permissions.SEND_MESSAGES | Permissions.EMBED_LINKS
                  | Permissions.ATTACH_FILES | Permissions.ADD_REACTIONS | Permissions.USE_EXTERNAL_EMOJIS
                  | Permissions.READ_MESSAGE_HISTORY
        ))

        for role in self.muted_roles:
            overwrites.append(Overwrite(
                id=int(role),
                type=0,
                deny=Permissions.SEND_MESSAGES | Permissions.SEND_MESSAGES_IN_THREADS |
                     Permissions.CREATE_PUBLIC_THREADS | Permissions.CREATE_PRIVATE_THREADS | Permissions.ADD_REACTIONS
            ))

        channel = await current_guild.create_channel(
            name=f"{renewal_date.day}-{renewal_date.month}-{user[1]}",
            parent_id=self.category_id,
            type=ChannelType.GUILD_TEXT,
            permission_overwrites=overwrites
        )

        channel_id = str(channel.id)
        self.update_transfer_data(user[0], {
            "has_channel": True,
            "channel_id": channel_id
        })

        return channel


firebase_manager = FirebaseManager()
