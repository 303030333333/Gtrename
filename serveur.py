from aiohttp import web

async def handler(request):
    return web.Response(text="Bot Actif - Auto Ping OK")

app = web.Application()
app.router.add_get("/", handler)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=8000)