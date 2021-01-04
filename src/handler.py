from configparser import ConfigParser, ExtendedInterpolation

from discord import Embed
import discord.ext
from utils import colours, emojis
import asyncio


class Menu:
    """Object that manages embed in a form of a menu."""

    def __init__(self, pages: dict, ctx: discord.ext.commands.context, bot: discord.ext.commands.AutoShardedBot):
        """Initialisation method of the Menu object.
        Args:
            pages (dict): (str) name of the flow type that will map to its embed. -> (Embed) it's embed
            ctx (discord.ext.commands.context): context, required to display the menu
            bot (discord.ext.commands.AutoShardedBot) : bot, required to control action (reactions).
        """

        self.__pages = pages
        self.__ctx = ctx
        self.__bot = bot
        self.__reactions = {}
        self.__message = None
        self.__exit = False
    
    def attach_function(self, reaction, function, args: tuple):
        """Attaches a function to the reaction. The function will run if
           the reaction is triggered by the user.

        Args:
            reaction (emoji): unicode string of the emoji.
            function (function): function that is going to be attached to that emoji
            args (tuple): arguments that need to be run as the arguments of the function.
        """
        self.__reactions[reaction] = (function, args)
        
    async def attach_numbers(self):
        """makes the pages behave in a page form."""
        for page, i in zip(self.__pages.keys(), range(1, 10)):
            self.__reactions[emojis.PAGES[i]] = (Menu.change_page, (self, page))
        
    def verify(self, reaction: discord.reaction.Reaction, user: discord.member.Member):
        """method that checks that the reaction is sent from the user.

        Args:
            reaction (discord.reaction.Reaction): Reaction object that is sent from discord
            user (discord.member.Member): Member object that contains user info. Sent from discord

        Returns:
            boolean: Flag that indicates whether it satisfies the verification function.
        """
        return user == self.__ctx.message.author
    
    async def attach_reactions(self, message):
        """Attach reactions

        Args:
            message (discord.message.Message): discord object representing a message. 
        """
        for reaction in self.__reactions.keys():
            await message.add_reaction(reaction)
        
        await asyncio.sleep(2)
    
    async def deploy_menu(self):
        """This method deploys the menu into the ctx.channel and manages the menu."""

        self.__message = await self.__ctx.message.channel.send(embed=self.__pages['MAIN'])
        for i in self.__reactions.keys():
            await self.__message.add_reaction(i)
        
        while not self.__exit:
            reaction, user = await self.__bot.wait_for('reaction_add', timeout=60.0, check=self.verify)
            if reaction is None:
                break
            
            emoji = reaction.emoji
            if emoji in self.__reactions.keys():
                func, args = self.__reactions[emoji]
                await func(*args)
            await reaction.remove(user)

    async def clear_reactions(self):
        self.__ctx.message.clear_reactions()

    async def change_page(self, page):
        """function that changes the embed on display

        Args:
            page (str): flow state that identifies the page embed in the page
        """
        await self.__message.edit(embed=self.__pages[page])


class Handler:
    """Handler object is responsible for handling messages that are to be sent to the client.
       Data is stored in .ini files, where they are called and parsed. """
    
    def __init__(self, ctx: discord.ext.commands.context, bot: discord.ext.commands.AutoShardedBot,
                 pages: dict, player: object):

        self.__ctx = ctx
        self.__bot = bot
        self.player = player
        self.__pages = pages
        self.message = None
    
    async def send(self, flow: str):
        return await self.__ctx.send(embed=self.retrieve_embed(flow))
    
    def verify(self, message):
        """Method verifies if the content of the message is in the contents

        Args:
            message (discord.message.Message): message that is getting verified

        Returns:
            bool: true of false that indicates whether the data is valid.
        """
        
        return message.author == self.__ctx.message.author and \
            message.channel == self.__ctx.message.channel

    async def get_message(self):
        """This method waits for a message to be sent by the user"""

        confirm = await self.__bot.wait_for('message', timeout=60.0, check=self.verify)

        if confirm is not None:
            return confirm.content
        return None

    async def display(self, flow):
        """this is the main function that we use to send one message, and one message only.
           However edits to that message can take place.

        Args:
            flow (str): name of the flow key.
        """

        if self.message is None:
            self.message = await self.send(flow)
        else:
            await self.message.edit(embed=self.retrieve_embed(flow))


    def retrieve_embed(self, flow_type):
        """Reads the contents of the section in the .ini file, and
        creates an embed with that data.

        Args:
            flow_type (str): Name of the section in the .ini state

        Returns:
            Embed: Embed Object, discord compatible.
        """
        flow = self.__pages[flow_type](self.player)

        colour = colours.get_colour(flow.colour)
        embed = Embed(title=flow.title, colour=colour)

        for field in flow.fields:
            if len(field) == 2:
                embed.add_field(name=field[0], value=field[1], inline=True)
            else:
                embed.add_field(name=field[0], value=field[1], inline=field[2])

        embed.set_footer(text=flow.footer_text, icon_url=flow.footer_image)
        embed.set_thumbnail(url=flow.thumbnail)
        embed.set_image(url=flow.image)

        return embed

    def retrieve_menu(self, flow_type: str):
        """Method that gets the menu specified

        Args:
            flow_type (str): string that labels the flow

        Returns:
        Menu : Object that contains the menu
        """
        embed, message_type = self.retrieve_embed(flow_type)
        pointer = self.__pages[flow_type].pointer
        menu = {'MAIN': embed}

        while pointer is not None:
            # gets all the pages in the menu.
            menu[pointer.flow] = self.retrieve_embed(pointer.flow)
            pointer = pointer.pointer

        return Menu(menu, self.__ctx, self.__bot)