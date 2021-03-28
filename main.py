import discord, asyncio, os, platform, sys, logging
from discord_slash import http
from pysnc import ServiceNowClient
from aiohttp import web

if not os.path.isfile("config.py"):
    sys.exit("'config.py' not found! Please add it and try again.")
else:
    import config


class NowBot(discord.Client):
    """
    Ultimately a proxy between discord and ServiceNow
    """
    def __init__(self):
        self.logger = logging.getLogger("NowBot")
        self.now = ServiceNowClient(config.NOW_INSTANCE, (config.NOW_USER, config.NOW_PASS))
        self.req = http.SlashCommandRequest(self.logger, self, None)
        super().__init__()

    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))
        print(await self.req.get_all_commands())


    async def on_message(self, message):
        if message.author == self.user or message.author.bot:
            return
        # Ignores if a command is being executed by a blacklisted user
        if message.author.id in config.BLACKLIST:
            return

        print('Message: %s' % message)

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

