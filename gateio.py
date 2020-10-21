import json
import websockets
from ccxtws.base import Exchange, ExchangeObserver
from . import logutils
from . import utils

logger = logutils.get_logger('ccxtws')

INTERVALS = {"SUSHI_USDT": "0.001"}


class gateio(Exchange):
    def __init__(self):
        self.ws_uri = 'wss://ws.gate.io/v3/'
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
        async with websockets.connect(self.ws_uri, ping_interval=None) as websocket:
            added_channels = set()
            while True:
                for channel in self.channels:
                    if channel in added_channels:
                        continue
                    added_channels.add(channel)
                    params = [[item, 20, INTERVALS.get(item, "0.00000001")]for item in self.channels]
                    req = json.dumps({"id": utils.get_req_id(), "method": "depth.subscribe", "params": params})
                    await websocket.send(req)
                resp = await websocket.recv()
                data = json.loads(resp)
                if 'method' in data and data['method'] == 'depth.update':
                    self.notify(data)
                else:
                    logger.warning("unknown data %s", data)

    def subscribe(self, observer):
        self.observers.append(observer)
        self.channels.add(observer.channel)

    def unsubscribe(self, observer):
        self.observers.remove(observer)
        self.channels = set([observer.channel for observer in self.observers])

    def notify(self, data):
        final_data = {'asks': [], 'bids': []}
        final_data['full'] = data['params'][0]
        if 'asks' in data['params'][1]:
            final_data['asks'] = [[float(item[0]), float(item[1])] for item in data['params'][1]['asks']]
        if 'bids' in data['params'][1]:
            final_data['bids'] = [[float(item[0]), float(item[1])] for item in data['params'][1]['bids']]

        for observer in self.observers:
            if observer.channel != data['params'][2]:
                continue
            observer.update(final_data)


class gateio_observer(ExchangeObserver):
    def __init__(self, exchange, symbol, callback):
        market = exchange.market(symbol)
        self.channel = market['id'].upper()
        self.callback = callback

    def update(self, data):
        self.callback(data)
