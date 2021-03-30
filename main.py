import discord, asyncio, os, platform, sys, logging
from discord_slash import http
from pysnc import ServiceNowClient
from aiohttp import web

if not os.path.isfile("config.py"):
    sys.exit("'config.py' not found! Please add it and try again.")
else:
    import config

GUILD_ID = '183730219763499009' # make None when not testing



class NowAgent:

    def __init__(self, client):
        self.client = client

    def commands(self):
        cmd_gr = self.client.GlideRecord('x_snc_discord_commands')
        cmd_gr.add_active_query()
        cmd_gr.query()
        for cmd in cmd_gr:
            yield cmd

    def options(self, command, typ: int = None):
        target = command if type(command) == str else command.sys_id
        s_gr = self.client.GlideRecord('x_snc_discord_command_option')
        s_gr.fields = 'name,description,type,required'
        s_gr.add_active_query()
        oq = s_gr.add_query('command', target)
        oq.add_or_condition('command_option', target)
        if typ:
            s_gr.add_query('type', typ)
        s_gr.query()
        for scmd in s_gr:
            yield scmd

    def choices(self, option):
        c_gr = self.client.GlideRecord('x_snc_discord_command_option_choice')
        c_gr.fields = 'name,value'
        target = option if type(option) == str else option.sys_id
        c_gr.add_query('option', target)
        c_gr.query()
        for e in c_gr:
            yield e

    async def execute_action(self, cmd):
        # this is where i would call the rest service
        target = "{url}/api/x_snc_discord/discord/webhook/{token}".format(url=self.client.instance, token=config.WEBHOOK_TOKEN)
        resp = self.client.session.post(target, json=cmd, headers=dict(Accept="application/json"))
        print(resp.status_code)
        print(resp.text)
        return resp.json()


class CommandManager:
    def __init__(self, discord, agent):
        self.logger = logging.getLogger("CommandManager")
        self.req = http.SlashCommandRequest(self.logger, discord, None)
        self.discord = discord
        self.agent = agent

    def _marshal_option(self, option, choices):
        return {
            'name': option.name,
            'description': option.description,
            'type': option.type,
            'required': option.required,
            'choices': [ {'name':c.name, 'value':c.value} for c in choices ]
        }

    async def sync_commands(self):
        commands = self.agent.commands()
        for cmd in commands:
            options = self.agent.options(cmd)
            optarr = []
            for option in options:
                choices = self.agent.choices(option)
                s = self._marshal_option(option, choices)
                optarr.append(s)

            await self.req.add_slash_command(GUILD_ID, cmd.name, cmd.description, optarr)
        print(await self.req.get_all_commands())

    async def process_command(self, cmd):
        print(f"Got slash command: {cmd['data']['name']}")
        print(cmd)
        base = {"type": 5} # ACK an interaction and edit to a response later, the user sees a loading state
        await self.req.post_initial_response(base, cmd['id'], cmd['token'])
        res = await self.agent.execute_action(cmd)
        await self.req.post_followup({'content': res['result']}, cmd['token'])


def sync(self):
        pass

class NowBot(discord.Client):
    """
    Ultimately a proxy between discord and ServiceNow
    """
    def __init__(self):
        self.logger = logging.getLogger("NowBot")
        self._now = ServiceNowClient(config.NOW_INSTANCE, (config.NOW_USER, config.NOW_PASS))
        self.agent = NowAgent(self._now)
        self.req = http.SlashCommandRequest(self.logger, self, None)
        self.manager = CommandManager(self, self.agent)
        super().__init__()

    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))
        await self.manager.sync_commands()
        #print(await self.req.get_all_commands())

    async def on_message(self, message):
        if message.author == self.user or message.author.bot:
            return
        # Ignores if a command is being executed by a blacklisted user
        if message.author.id in config.BLACKLIST:
            return

        #print('Message: %s' % message)

    async def on_socket_response(self, msg):
        """
        :param msg: Gateway message.
        """
        if msg["t"] != "INTERACTION_CREATE":
            return

        to_use = msg["d"]
        await self.manager.process_command(to_use)

    async def process_webhook(self, request):
        token = request.match_info['token']
        if token != config.WEBHOOK_TOKEN:
            return web.HTTPForbidden()
        data = {'some':'data'}
        return web.json_response(data)


async def main(bot) -> None:
    app = web.Application()

    app.add_routes([web.post('/webhook/{token}', bot.process_webhook)])

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, port=os.environ.get('PORT', 8080))
    await site.start()
    print("Started web")


def handle_exit(client: discord.Client) -> None:
    print("Handling exit")
    client.loop.run_until_complete(client.logout())
    # For python 3.9, use asyncio.all_tasks instead
    for t in asyncio.Task.all_tasks(loop=client.loop):
        if t.done():
            t.exception()
            continue
        t.cancel()
        try:
            client.loop.run_until_complete(asyncio.wait_for(t, 5, loop=client.loop))
            t.exception()
        except (asyncio.InvalidStateError, asyncio.TimeoutError, asyncio.CancelledError):
            pass


if __name__ == '__main__':
    bot = NowBot()

    while True:
        bot.loop.create_task(main(bot))
        try:
            print('Starting...')
            bot.loop.run_until_complete(bot.start(config.TOKEN))
        except SystemExit:
            handle_exit(bot)
        except KeyboardInterrupt:
            handle_exit(bot)
            bot.loop.close()
            print("Program ended")
            break

