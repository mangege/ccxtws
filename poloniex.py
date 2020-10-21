import json
import websockets
from ccxtws.base import Exchange, ExchangeObserver
from . import logutils

logger = logutils.get_logger('ccxtws')


class poloniex(Exchange):
    def __init__(self):
        self.ws_uri = 'wss://api2.poloniex.com'
        self.observers = []
        self.channels = set()
        self.is_running = False

    async def run(self):
        if self.is_running:
            return
        self.is_running = True
        while True:
            try:
                await self._run()
            except Exception as e:
                logger.exception(e)

    async def _run(self):
        async with websockets.connect(self.ws_uri) as websocket:
            added_channels = set()
            while True:
                for channel in self.channels:
                    if channel in added_channels:
                        continue
                    added_channels.add(channel)
                    req = json.dumps({"command": "subscribe", "channel": channel})
                    await websocket.send(req)
                resp = await websocket.recv()
                data = json.loads(resp)
                if data[0] == 1010:
                    continue
                else:
                    self.notify(data)

    def subscribe(self, observer):
        self.observers.append(observer)
        self.channels.add(observer.channel)

    def unsubscribe(self, observer):
        self.observers.remove(observer)
        self.channels = set([observer.channel for observer in self.observers])

    def notify(self, data):
        final_data = {'asks': [], 'bids': []}
        if len(data) >= 3:
            if data[2][0][0] == 'i':
                final_data['full'] = True
                final_data['asks'] = [[float(p), float(v)] for p, v in data[2][0][1]['orderBook'][0].items()]
                final_data['bids'] = [[float(p), float(v)] for p, v in data[2][0][1]['orderBook'][1].items()]
            elif data[2][0][0] == 'o':
                final_data['full'] = False
                final_data['asks'] = [[float(item[2]), float(item[3])] for item in data[2] if item[0] == 'o' and item[1] == 0]
                final_data['bids'] = [[float(item[2]), float(item[3])] for item in data[2] if item[0] == 'o' and item[1] == 1]
            else:
                logger.warning("unknown data %s", data)
                return
        else:
            logger.warning("unknown data %s", data)
            return

        for observer in self.observers:
            if observer.channel != data[0]:
                continue
            observer.update(final_data)


class poloniex_observer(ExchangeObserver):
    def __init__(self, exchange, symbol, callback):
        market = exchange.market(symbol)
        self.channel = market['info']['id']
        self.callback = callback

    def update(self, data):
        self.callback(data)
