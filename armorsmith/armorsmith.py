import logging
import os
from collections import namedtuple, OrderedDict, defaultdict
from copy import deepcopy
from datetime import datetime
from random import choice

import discord
from __main__ import send_cmd_help
from cogs.utils.chat_formatting import pagify, box
from cogs.utils.dataIO import dataIO
from discord.ext import commands

from .utils import checks

DEFAULTS = {
    "HP": 50
}


class ArmorException(Exception):
    pass


class InventoryException(Exception):
    pass


class AccountAlreadyExists(InventoryException):
    pass


class NoAccount(InventoryException):
    pass


class ItemNotFound(InventoryException):
    pass


class SameSenderAndReceiver(InventoryException):
    pass


class Item(namedtuple('Item', 'name cost')):
    @staticmethod
    def _roll_dice(dice):
        """Returns the value of rolling XdY dice
        Ex: _roll_dice("2d6") returns the result of rolling 2 six-sided die"""
        (num_rolls, dice_sides) = map(int, dice.split('d'))
        val = 0
        for roll in range(num_rolls):
            val += choice(range(1, dice_sides + 1))
        return val

    def __str__(self):
        s = ""
        for name, value in self._asdict().items():
            s += "{}: {}\n".format(name, value)
        s += ""
        return s

    def __repr__(self):
        return self.name


class Weapon(namedtuple('Weapon', Item._fields + ('hit_dice',)), Item):
    def damage_roll(self):
        return self._roll_dice(self.hit_dice)

    def get_type(self):
        return "weapon"


class Armor(namedtuple('Armor', Item._fields + ('damage_reduction',)), Item):
    def block_damage(self, damage):
        return max(damage - int(self.damage_reduction), 0)

    def get_type(self):
        return "armor"


class HealPotion(namedtuple('HealPotion', Item._fields + ('heal_dice',)), Item):
    def healing_roll(self):
        return self._roll_dice(self.heal_dice)

    def get_type(self):
        return "potion"


class Account:
    def __init__(self, id, name, stash, equipment, created_at, server, member):
        self.id = id
        self.name = name
        self.stash = stash
        self.created_at = created_at
        self.server = server
        self.member = member
        self.equipment = equipment

    def get_equipment(self):
        if self.equipment["weapon"]:
            weapon = Weapon(*self.equipment["weapon"])
        else:
            weapon = None
        if self.equipment["armor"]:
            armor = Armor(*self.equipment["armor"])
        else:
            armor = None
        if self.equipment["potion"]:
            potion = HealPotion(*self.equipment["potion"])
        else:
            potion = None
        return (weapon, armor, potion)


class Inventory:
    def __init__(self, bot, file_path):
        self.bot = bot
        self.accounts = dataIO.load_json(file_path)

    def create_account(self, user):
        server = user.server
        if not self.account_exists(user):
            if server.id not in self.accounts:
                self.accounts[server.id] = {}
            if user.id in self.accounts:  # Legacy account
                stash = self.accounts[user.id]["stash"]
                equipment = self.accounts[user.id]["equipment"]
            else:
                stash = OrderedDict()
                equipment = {
                    "weapon": None,
                    "armor": None,
                    "potion": None
                }
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            account = {"name": user.name,
                       "stash": stash,
                       "created_at": timestamp,
                       "equipment": equipment
                       }
            self.accounts[server.id][user.id] = account
            self._save_inventory()
            return self.get_account(user)
        else:
            raise AccountAlreadyExists()

    def account_exists(self, user):
        try:
            self._get_account(user)
        except NoAccount:
            return False
        return True

    def has_item(self, user, item):
        account = self._get_account(user)
        stash = account["stash"]
        if item.name in stash.keys():
            return True
        else:
            return False

    def equipped_item(self, user, item):
        account = self._get_account(user)
        equipment = account["equipment"]
        if equipment[item.get_type()][0] == item.name:
            return True
        return False

    def remove_item(self, user, item):
        server = user.server
        account = self._get_account(user)
        stash = account["stash"]
        equipment = account["equipment"]
        if self.has_item(user, item):
            del stash[item.name]
            # TODO: Make this work
            if self.equipped_item(user, item):
                equipment[item.get_type()] = None
            self.accounts[server.id][user.id] = account
            self._save_inventory()
        else:
            raise ItemNotFound()

    def give_item(self, user, item):
        server = user.server
        account = self._get_account(user)
        stash = account["stash"]
        stash[item.name] = item
        self.accounts[server.id][user.id] = account
        self._save_inventory()

    def transfer_item(self, sender, receiver, item):
        if sender is receiver:
            raise SameSenderAndReceiver()
        if self.account_exists(sender) and self.account_exists(receiver):
            if not self.has_item(sender, item):
                raise ItemNotFound()
            self.remove_item(sender, item)
            self.give_item(receiver, item)
        else:
            raise NoAccount()

    def wipe_inventories(self, server):
        self.accounts[server.id] = {}
        self._save_inventory()

    def get_server_accounts(self, server):
        if server.id in self.accounts:
            raw_server_accounts = deepcopy(self.accounts[server.id])
            accounts = []
            for k, v in raw_server_accounts.items():
                v["id"] = k
                v["server"] = server
                acc = self._create_account_obj(v)
                accounts.append(acc)
            return accounts
        else:
            return []

    def get_all_accounts(self):
        accounts = []
        for server_id, v in self.accounts.items():
            server = self.bot.get_server(server_id)
            if server is None:
                # Servers that have since been left will be ignored
                # Same for users_id from the old bank format
                continue
            raw_server_accounts = deepcopy(self.accounts[server.id])
            for k, v in raw_server_accounts.items():
                v["id"] = k
                v["server"] = server
                acc = self._create_account_obj(v)
                accounts.append(acc)
        return accounts

    def get_stash(self, user):
        account = self._get_account(user)
        return [str(x) for x in account["stash"]]

    def get_account(self, user):
        acc = self._get_account(user)
        acc["id"] = user.id
        acc["server"] = user.server
        return self._create_account_obj(acc)

    def equip(self, user, item: Item):
        server = user.server
        account = self._get_account(user)
        equipment = account["equipment"]
        if not self.has_item(user, item):
            raise ItemNotFound()
        if isinstance(item, Weapon):
            equipment["weapon"] = item
        elif isinstance(item, Armor):
            equipment["armor"] = item
        elif isinstance(item, HealPotion):
            equipment["potion"] = item
        self.accounts[server.id][user.id] = account
        self._save_inventory()

    def _create_account_obj(self, account):
        account["member"] = account["server"].get_member(account["id"])
        account["created_at"] = datetime.strptime(account["created_at"],
                                                  "%Y-%m-%d %H:%M:%S")
        account_obj = Account(**account)
        return account_obj

    def _save_inventory(self):
        dataIO.save_json("data/armorsmith/inventory.json", self.accounts)

    def _get_account(self, user):
        server = user.server
        try:
            return deepcopy(self.accounts[server.id][user.id])
        except KeyError:
            raise NoAccount()


class Store:
    """Interface to item list"""

    def __init__(self, bot, file_path):
        self.bot = bot
        self.file_path = file_path
        self.inventory = {"weapon": [],
                          "armor": [],
                          "potion": []}
        self._generate_inventory()

    def _generate_inventory(self):
        item_list = dataIO.load_json(self.file_path)
        for weapon in item_list["weapons_list"]:
            self.inventory["weapon"].append(Weapon(
                weapon["name"],
                weapon["cost"],
                weapon["hit_dice"]
            ))
        for armor in item_list["armor_list"]:
            self.inventory["armor"].append(Armor(
                armor["name"],
                armor["cost"],
                armor["damage_reduction"]
            ))
        for potion in item_list["potion_list"]:
            self.inventory["potion"].append(HealPotion(
                potion["name"],
                potion["cost"],
                potion["heal_dice"]
            ))

    def get_item_by_name(self, item_name):
        for item_type in self.inventory.values():
            for item in item_type:
                if item.name == item_name:
                    return item
        raise ItemNotFound


class Arena:
    def __init__(self, bot, file_path):
        self.bot = bot
        self.leaderboard = dataIO.load_json(file_path)

    def create_entry(self, user):
        server = user.server
        if not self.score_exists(user):
            if server.id not in self.leaderboard:
                self.leaderboard[server.id] = {}
            if user.id in self.leaderboard:
                wins = self.leaderboard[user.id]["wins"]
                losses = self.leaderboard[user.id]["losses"]
            else:
                wins = 0
                losses = 0
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            entry = {
                "name": user.name,
                "wins": wins,
                "losses": losses,
                "created_at": timestamp
            }
            self.leaderboard[server.id][user.id] = entry
            self._save_leaderboard()
        else:
            raise AccountAlreadyExists()

    def score_exists(self, user):
        try:
            self._get_entry(user)
        except NoAccount:
            return False
        return True

    def get_entry(self, user):
        score = self._get_entry(user)
        score["id"] = user.id
        score["server"] = user.server
        return self._create_entry_obj(score)

    def get_entries(self, server):
        if server.id in self.leaderboard:
            raw_server_scores = deepcopy(self.leaderboard[server.id])
            scores = []
            for k, v in raw_server_scores.items():
                v["id"] = k
                v["server"] = server
                score = self._create_entry_obj(v)
                scores.append(score)
            return scores
        else:
            return []

    def add_result(self, user, is_win):
        server = user.server
        entry = self._get_entry(user)
        if is_win:
            entry["wins"] += 1
        else:
            entry["losses"] += 1
        self.leaderboard[server.id][user.id] = entry
        self._save_leaderboard()

    def _create_entry_obj(self, score):
        score["member"] = score["server"].get_member(score["id"])
        score["created_at"] = datetime.strptime(score["created_at"], "%Y-%m-%d %H:%M:%S")
        Score = namedtuple("Score", "id name wins losses created_at server member")
        return Score(**score)

    def _save_leaderboard(self):
        dataIO.save_json("data/armorsmith/leaderboard.json", self.leaderboard)

    def _get_entry(self, user):
        server = user.server
        try:
            return deepcopy(self.leaderboard[server.id][user.id])
        except KeyError:
            raise NoAccount()


class Armorsmith:
    def __init__(self, bot):
        global DEFAULTS
        self.bot = bot
        self.inventory = Inventory(bot, "data/armorsmith/inventory.json")
        self.store = Store(bot, "data/armorsmith/items.json")
        self.arena = Arena(bot, "data/armorsmith/leaderboard.json")
        self.bank = self.bot.get_cog("Economy").bank
        self.file_path = "data/armorsmith/settings.json"
        self.settings = dataIO.load_json(self.file_path)
        self.settings = defaultdict(lambda: DEFAULTS, self.settings)

    @commands.group(name="inventory", pass_context=True)
    async def _inventory(self, ctx):
        """Inventory operations."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_inventory.command(pass_context=True, no_pm=True)
    async def register(self, ctx):
        """Registers an inventory with the Armorsmith."""
        author = ctx.message.author
        try:
            account = self.inventory.create_account(author)
            await self.bot.say("{} Stash opened.".format(author.mention))
        except AccountAlreadyExists:
            await self.bot.say("{} You already have a stash with the Armorsmith".format(author.mention))

    @_inventory.command(pass_context=True)
    async def stash(self, ctx, user: discord.Member = None):
        """Shows stash of user. Defaults to yours."""
        if not user:
            user = ctx.message.author
            try:
                await self.bot.say("{} Your stash contains: {}".format(user.mention, self.inventory.get_stash(user)))
            except NoAccount:
                await self.bot.say(
                    "{} You don't have a stash with the Armorsmith. Type `{}inventory register` to open one".format(
                        user.mention, ctx.prefix))
        else:
            try:
                await self.bot.say("{}'s stash is {}".format(user.name, self.inventory.get_stash(user)))
            except NoAccount:
                await self.bot.say("That user has no inventory stash")

    @_inventory.command(pass_context=True)
    async def transfer(self, ctx, user: discord.Member, item: str):
        """Transfers an item to other users."""
        author = ctx.message.author
        try:
            item = self.store.get_item_by_name(item)
            self.inventory.transfer_item(author, user, item)
            logger.info(
                "{} ({}) transferred {} to {}({})".format(author.name, author.id, item.name, user.name, user.id))
            await self.bot.say("{} has been transferred to {}'s stash.".format(item.name, user.name))
        except SameSenderAndReceiver:
            await self.bot.say("You can't transfer to yourself.")
        except ItemNotFound:
            await self.bot.say("Item was not found in your stash.")
        except NoAccount:
            await self.bot.say("That user has no stash account.")

    @_inventory.command(pass_context=True, no_pm=True)
    async def equip(self, ctx, *, item_name: str):
        """Equip an item so you may use it in fights"""
        author = ctx.message.author
        try:
            item = self.store.get_item_by_name(item_name)
            self.inventory.equip(author, item)
            await self.bot.say("{} equipped {}".format(author.mention, item_name))
        except ItemNotFound:
            await self.bot.say("Item name was not found.")
        except NoAccount:
            await self.bot.say("Please register an account with the inventory before equipping.")

    @_inventory.command(pass_context=True, no_pm=True)
    async def equipment(self, ctx, user: discord.Member = None):
        """View currently equipped items"""
        if not user:
            user = ctx.message.author
        try:
            account = self.inventory.get_account(user)
            await self.bot.say(
                "{} has equipped: {}".format(user.mention,
                                             ", ".join([item.name for item in account.get_equipment() if item])))
        except NoAccount:
            await self.bot.say("Provided user has no stash account.")

    @_inventory.command(pass_context=True, no_pm=True)
    async def remove(self, ctx, *, item_name):
        """Removes an item from your inventory (and unequips it)"""
        user = ctx.message.author
        try:
            item = self.store.get_item_by_name(item_name)
            self.inventory.remove_item(user, item)
            await self.bot.say("Removed item {} fom inventory".format(item_name))
        except ItemNotFound:
            await self.bot.say("Item was not found.")

    @_inventory.command(name="give", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _give(self, ctx, user: discord.Member, *, item_name: str):
        """Gives an item to a user."""
        author = ctx.message.author
        try:
            item_obj = self.store.get_item_by_name(item_name)
            self.inventory.give_item(user, item_obj)
            logger.info("{}({}) gave {} to {}({})".format(author.name, author.id, item_obj.name, user.name, user.id))
            await self.bot.say("{} has been given to {}".format(item_obj.name, user.name))
        except ItemNotFound:
            await self.bot.say("Item name does not exist")

    @_inventory.command(pass_context=True, no_pm=True)
    @checks.serverowner_or_permissions(administrator=True)
    async def reset(self, ctx, confirmation: bool = False):
        """Deletes all server's stash accounts"""
        if confirmation is False:
            await self.bot.say(
                "This will delete all stash accounts on this server.\nIf you're sure, type {}inventory reset yes".format(
                    ctx.prefix))
        else:
            self.inventory.wipe_inventories(ctx.message.server)
            await self.bot.say("All stash accounts on this server have been deleted.")

    @commands.group(name="store", pass_context=True)
    async def _store(self, ctx):
        """Store operations."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_store.command(pass_context=True, no_pm=False)
    async def list(self, ctx):
        """Lists all available items for purchase"""
        message = "What're ya buyin', traveler?\n"
        message += "Item Shop\n\n"
        for item_type in self.store.inventory.keys():
            message += item_type + "\n---------------\n"
            for item in self.store.inventory[item_type]:
                message += str(item) + "\n"
            message += "\n\n"
        for page in pagify(message, shorten_by=12):
            await self.bot.whisper(box(page))

    @_store.command(pass_context=True, no_pm=True)
    async def buy(self, ctx, *, item_name):
        """Buy an item for yourself"""
        author = ctx.message.author
        try:
            item = self.store.get_item_by_name(item_name)
            if not self.bank.can_spend(author, item.cost):
                await self.bot.say("You have insufficient funds to purchase that item.")
                return
            self.bank.withdraw_credits(author, item.cost)
            self.inventory.give_item(author, item)
            await self.bot.say("{} bought {} for {} credits.".format(author.mention, item_name, item.cost))
        except NoAccount:
            await self.bot.say("You do not have a stash register. Please do so before buying.")
        except ItemNotFound:
            await self.bot.say("The item specified does not exist.")

    @commands.group(name="fight", pass_context=True)
    async def _fight(self, ctx):
        """Dueling operations."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_fight.command(pass_context=True, no_pm=True)
    async def challenge(self, ctx, user: discord.Member, wager=0):
        """Challenge a user to a duel they must accept, with optional wager."""
        settings = self.settings[ctx.message.server.id]
        author = ctx.message.author
        if not user:
            await send_cmd_help(ctx)
            return
        try:
            account_author = self.inventory.get_account(author)
        except NoAccount:
            await self.bot.say("You must have an account to duel. Make one with `!inventory register`")
            return
        try:
            account_user = self.inventory.get_account(user)
        except NoAccount:
            await self.bot.say("Selected user does not have an account")
            return
        try:
            self.arena.create_entry(author)
        except AccountAlreadyExists:
            pass
        try:
            self.arena.create_entry(user)
        except AccountAlreadyExists:
            pass
        if wager > 0 and not (self.bank.can_spend(author, wager) and self.bank.can_spend(user, wager)):
            await self.bot.say("Someone can't spare the wagered amount. Please try again.")
            return
        await self.bot.say("{}, do you accept this challenge?".format(user.mention))
        msg = await self.bot.wait_for_message(timeout=15, author=user, content='yes')
        if msg and msg.content == "yes":
            battle_text, author_won = self.duel(author, user, settings)
            for page in pagify(battle_text, shorten_by=12):
                await self.bot.say(box(page, lang="py"))
            if author_won:
                self.bank.transfer_credits(user, author, wager)
            else:
                self.bank.transfer_credits(author, user, wager)
        else:
            await self.bot.say("Challenge declined.")

    def duel(self, author, user, settings):
        """Fight between two people"""
        hp_author = settings.get("HP", 50)
        hp_user = settings.get("HP", 50)
        a_weapon, a_armor, a_potion = self.inventory.get_account(author).get_equipment()
        u_weapon, u_armor, u_potion = self.inventory.get_account(user).get_equipment()
        if not a_weapon or not u_weapon:
            raise Exception
        battle_text = ""
        while hp_author > 0 and hp_user > 0:
            damage_to_user = a_weapon.damage_roll()
            if u_armor:
                damage_to_user = u_armor.block_damage(damage_to_user)
            hp_user -= damage_to_user
            battle_text += "{} hit {} for {} damage!\n".format(author.name, user.name, damage_to_user)
            if hp_user <= 0 and u_potion is not None:
                hp_user += u_potion.healing_roll()
                self.inventory.remove_item(user, u_potion)
                u_potion = None
                battle_text += "{} used a potion\n".format(user.name)
            damage_to_author = u_weapon.damage_roll()
            if a_armor:
                damage_to_author = a_armor.block_damage(damage_to_author)
            hp_author -= damage_to_author
            battle_text += "{} hit {} for {} damage\n".format(user.name, author.name, damage_to_author)
            if hp_author <= 0 and a_potion is not None:
                hp_author += a_potion.healing_roll()
                self.inventory.remove_item(author, a_potion)
                a_potion = None
                battle_text += "{} used a potion".format(author.name)
        if hp_user <= 0:
            battle_text += "{} beat {} in a duel with {} hp remaining!\n".format(author.name, user.name, hp_author)
            self.arena.add_result(author, True)
            self.arena.add_result(user, False)
            author_won = True
        else:
            battle_text += "{} beat {} in a duel with {} hp remaining!\n".format(user.name, author.name, hp_user)
            self.arena.add_result(user, True)
            self.arena.add_result(author, False)
            author_won = False
        return battle_text, author_won

    @_fight.command(pass_context=True, no_pm=True)
    async def leaderboard(self, ctx, top=10):
        """Displays the win/loss leaderboard"""
        server = ctx.message.server
        if top < 1:
            top = 10
        entries_sorted = sorted(self.arena.get_entries(server), key=lambda x: x.wins, reverse=True)
        entries_sorted = [a for a in entries_sorted if a.member]
        if len(entries_sorted) < top:
            top = len(entries_sorted)
        topentries = entries_sorted[:top]
        highscore = "Wins Losses\n".rjust(23)
        place = 1
        for acc in topentries:
            highscore += str(place).ljust(len(str(top)) + 1)
            highscore += (str(acc.member.display_name) + " ").ljust(23 - len(str(acc.wins) + " " + str(acc.losses)))
            highscore += str(acc.wins) + " " + str(acc.losses) + "\n"
            place += 1
        if highscore != "":
            for page in pagify(highscore, shorten_by=12):
                await self.bot.say(box(page, lang="py"))
        else:
            await self.bot.say("There are no accounts in the leaderboard")

    @commands.group(name="armorsmithset", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_server=True)
    async def armorsmithset(self, ctx):
        """Changes Armorsmith module settings"""
        server = ctx.message.server
        settings = self.settings[server.id]
        if ctx.invoked_subcommand is None:
            msg = "```"
            for k, v in settings.items():
                msg += "{}: {}\n".format(k, v)
            msg += "```"
            await send_cmd_help(ctx)
            await self.bot.say(msg)


def check_folders():
    if not os.path.exists("data/armorsmith"):
        print("Creating data/armorsmith folder...")
        os.makedirs("data/armorsmith")


def check_files():
    f = "data/armorsmith/settings.json"
    if not dataIO.is_valid_json(f):
        print("Creating default armorsmith settings.json...")
        dataIO.save_json(f, {})

    f = "data/armorsmith/inventory.json"
    if not dataIO.is_valid_json(f):
        print("Creating empty inventory.json...")
        dataIO.save_json(f, {})

    f = "data/armorsmith/items.json"
    if not dataIO.is_valid_json(f):
        print("Item file not found/invalid. Creating blank item file")
        dataIO.save_json(f, {})

    f = "data/armorsmith/leaderboard.json"
    if not dataIO.is_valid_json(f):
        print("Leaderboard file not found/invalid. Creating blank leaderboard")
        dataIO.save_json(f, {})


def setup(bot):
    global logger
    check_folders()
    check_files()
    logger = logging.getLogger("red.armorsmith")
    if logger.level == 0:
        # Prevents the logger from being loaded again in case of module reload
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(filename='data/armorsmith/inventory.log', encoding='utf-8', mode='a')
        handler.setFormatter(logging.Formatter('%(asctime)s %(message)s', datefmt="[%d/%m/%Y %H:%M]"))
        logger.addHandler(handler)
    bot.add_cog(Armorsmith(bot))
