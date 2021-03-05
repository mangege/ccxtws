import json
import websockets
from ccxtws.base import Exchange, ExchangeObserver, logger


class bitmax(Exchange):
    def __init__(self):
        super().__init__()
        # https://bitmax-exchange.github.io/bitmax-pro-api/#general-message-request-handling-logic-from-client-side
        self.ws_uri = 'wss://bitmax.io/0/api/pro/v1/stream'
        self.ping_sleep_time = 30

    async def _run(self):
        async with websockets.connect(self.ws_uri) as websocket:
            self.ws_conn = websocket
            added_channels = set()
            while True:
                for channel in self.channels:
                    if channel in added_channels:
                        continue
                    added_channels.add(channel)
                    req = json.dumps({"op": "sub", "ch": f"depth:{channel}"})
                    await websocket.send(req)
                    req = json.dumps({"op": "req", "action": "depth-snapshot-top100", "args": {"symbol": channel}})
                    await websocket.send(req)
                resp = await websocket.recv()
                data = json.loads(resp)
                if data['m'] == 'ping':
                    req = json.dumps({'op': 'pong'})
                    await websocket.send(req)
                elif data['m'] in ['depth-snapshot', 'depth']:
                    self.notify(data)
                else:
                    logger.warning("unknown data %s", data)

    async def _ping(self):
        req = json.dumps({"op": "ping"})
        await self.ws_conn.send(req)

    def notify(self, data):
        final_data = {'asks': [], 'bids': []}
        if data['m'] == 'depth-snapshot':
            final_data['full'] = True
        else:
            final_data['full'] = False
        final_data['asks'] = [[float(item[0]), float(item[1])] for item in data['data']['asks']]
        final_data['bids'] = [[float(item[0]), float(item[1])] for item in data['data']['bids']]

        for observer in self.observers:
            if observer.channel != data['symbol']:
                continue
            observer.update(final_data)


class bitmax_observer(ExchangeObserver):
    def __init__(self, exchange, symbol, callback):
        market = exchange.market(symbol)
        self.channel = market['id']
        self.callback = callback

    def update(self, data):
        self.callback(data)
