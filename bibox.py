import json
import base64
import gzip
import websockets
from ccxtws.base import Exchange, ExchangeObserver
from . import logutils

logger = logutils.get_logger('ccxtws')


class bibox(Exchange):
    def __init__(self):
        self.ws_uri = 'wss://push.bibox.com'
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
                self.wipe_orderbook()
                logger.exception(e)

    async def _run(self):
        async with websockets.connect(self.ws_uri) as websocket:
            added_channels = set()
            while True:
                for channel in self.channels:
                    if channel in added_channels:
                        continue
                    added_channels.add(channel)
                    req = json.dumps({"event": "addChannel", "channel": f"bibox_sub_spot_{channel}_depth"})
                    await websocket.send(req)
                resp = await websocket.recv()
                data = json.loads(resp)
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
        if len(data) > 1:
            logger.warning("unknown data %s", data)
            return
        b64_data = data[0]['data']
        gz_data = base64.b64decode(b64_data)
        decoded_data = gzip.decompress(gz_data)
        j_data = json.loads(decoded_data)
        final_data = {'full': True, 'asks': [], 'bids': []}
        final_data['asks'] = [[float(item['price']), float(item['volume'])] for item in j_data['asks']]
        final_data['bids'] = [[float(item['price']), float(item['volume'])] for item in j_data['bids']]

        for observer in self.observers:
            if observer.channel not in data[0]['channel']:
                continue
            observer.update(final_data)


class bibox_observer(ExchangeObserver):
    def __init__(self, exchange, symbol, callback):
        market = exchange.market(symbol)
        self.channel = market['id']
        self.callback = callback

    def update(self, data):
        self.callback(data)
