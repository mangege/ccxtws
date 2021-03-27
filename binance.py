import asyncio
import json
import websockets
from ccxtws.base import Exchange, ExchangeObserver, logger
from . import utils


class binance(Exchange):
    def __init__(self):
        super().__init__()
        # https://binance-docs.github.io/apidocs/spot/cn/#6ae7c2b506
        self.ws_uri = 'wss://stream.binance.com:9443/ws/stream'
        self.max_observers = 1024

    async def _run(self):
        async with websockets.connect(self.ws_uri) as websocket:
            self.ws_conn = websocket
            req = json.dumps({"method": "SET_PROPERTY", "params": ["combined", True], "id": utils.get_req_id()})
            await websocket.send(req)

            added_channels = set()
            while True:
                for channel in self.channels:
                    if channel in added_channels:
                        continue
                    added_channels.add(channel)
                    req = json.dumps({"method": "SUBSCRIBE", "params": [f"{channel}@depth5@100ms"], "id": utils.get_req_id()})
                    await websocket.send(req)
                    await asyncio.sleep(0.25)
                resp = await websocket.recv()
                data = json.loads(resp)
                if 'ping' in data:
                    req = json.dumps({"pong": data['ping']})
                    await websocket.send(req)
                else:
                    self.notify(data)

    def notify(self, data):
        if 'data' not in data:
            logger.warning("unknown data %s", data)
            return
        final_data = {'full': True, 'asks': [], 'bids': []}
        final_data['asks'] = [[float(item[0]), float(item[1])] for item in data['data']['asks']]
        final_data['bids'] = [[float(item[0]), float(item[1])] for item in data['data']['bids']]

        for observer in self.observers:
            if observer.channel not in data['stream']:
                continue
            observer.update(final_data)


class binance_observer(ExchangeObserver):
    def __init__(self, exchange, symbol, callback):
        market = exchange.market(symbol)
        self.channel = market['lowercaseId']
        self.callback = callback

    def update(self, data):
        self.callback(data)
