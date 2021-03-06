import json
import gzip
import websockets
from ccxtws.base import Exchange, ExchangeObserver, logger


class biki(Exchange):
    def __init__(self):
        super().__init__()
        # https://github.com/code-biki/open-api/blob/master/README.md#websocket-api
        self.ws_uri = 'wss://ws.biki.com/kline-api/ws'
        self.max_observers = -1

    async def _run(self):
        async with websockets.connect(self.ws_uri) as websocket:
            self.ws_conn = websocket
            added_channels = set()
            while True:
                for channel in self.channels:
                    if channel in added_channels:
                        continue
                    added_channels.add(channel)
                    req = json.dumps({"event": "sub", "params": {"channel": f"market_{channel}_depth_step0", "asks": 5, "bids": 5}})
                    await websocket.send(req)
                resp = await websocket.recv()
                decoded_data = gzip.decompress(resp)
                data = json.loads(decoded_data)
                if 'ping' in data:
                    req = json.dumps({"pong": data['ping']})
                    await websocket.send(req)
                else:
                    self.notify(data)

    def subscribe(self, observer):
        self.observers.append(observer)
        self.channels.add(observer.channel)

    def unsubscribe(self, observer):
        self.observers.remove(observer)
        self.channels = set([observer.channel for observer in self.observers])

    def notify(self, data):
        if 'tick' not in data:
            logger.warning("unknown data %s", data)
            return
        final_data = {'full': True, 'asks': [], 'bids': []}
        final_data['asks'] = [[float(item[0]), float(item[1])] for item in data['tick']['asks']]
        final_data['bids'] = [[float(item[0]), float(item[1])] for item in data['tick']['buys']]

        for observer in self.observers:
            if observer.channel not in data['channel']:
                continue
            observer.update(final_data)


class biki_observer(ExchangeObserver):
    def __init__(self, exchange, symbol, callback):
        market = exchange.market(symbol)
        self.channel = market['id']
        self.callback = callback

    def update(self, data):
        self.callback(data)
