import json
import websockets
from ccxtws.base import Exchange, ExchangeObserver, logger


class mxc(Exchange):
    def __init__(self):
        super().__init__()
        # https://github.com/mxcdevelop/APIDoc/blob/master/websocket/spot/websocket-api.md
        self.ws_uri = 'wss://wbs.mxc.com/socket.io/?EIO=3&transport=websocket'
        self.ping_sleep_time = 5
        self.max_observers = 1

    async def _run(self):
        async with websockets.connect(self.ws_uri, ping_interval=None) as websocket:
            self.ws_conn = websocket
            added_channels = set()
            while True:
                for channel in self.channels:
                    if channel in added_channels:
                        continue
                    added_channels.add(channel)
                    req = json.dumps(["sub.symbol", {"symbol": channel}])
                    await websocket.send(f"42{req}")
                    req = json.dumps(["get.depth", {"symbol": channel}])
                    await websocket.send(f"42{req}")
                resp = await websocket.recv()
                if resp.startswith('42'):
                    data = json.loads(resp.lstrip('42'))
                    if data[0] in ['push.symbol', 'rs.depth']:
                        self.notify(data)
                    else:
                        logger.warning("unknown data %s", data)
                elif resp.startswith('3'):
                    # ping pong
                    pass
                else:
                    logger.warning("unknown data %s", resp)

    async def _ping(self):
        await self.ws_conn.send("2")

    def notify(self, data):
        final_data = {'asks': [], 'bids': []}
        if data[0] == 'rs.depth':
            final_data['full'] = True
        else:
            final_data['full'] = False
        if 'asks' in data[1]['data']:
            final_data['asks'] = [[float(item['p']), float(item['q'])] for item in data[1]['data']['asks']]
        if 'bids' in data[1]['data']:
            final_data['bids'] = [[float(item['p']), float(item['q'])] for item in data[1]['data']['bids']]

        for observer in self.observers:
            if observer.channel != data[1]['symbol']:
                continue
            observer.update(final_data)


class mxc_observer(ExchangeObserver):
    def __init__(self, exchange, symbol, callback):
        market = exchange.market(symbol)
        self.channel = market['id']
        self.callback = callback

    def update(self, data):
        self.callback(data)
