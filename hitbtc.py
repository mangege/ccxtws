import json
import websockets
from ccxtws.base import Exchange, ExchangeObserver, logger
from . import utils


class hitbtc(Exchange):
    def __init__(self):
        super().__init__()
        # https://api.hitbtc.com/#socket-api-reference
        self.ws_uri = 'wss://api.hitbtc.com/api/2/ws/public'
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
                    req = json.dumps({"id": utils.get_req_id(), "method": "subscribeOrderbook", "params": {"symbol": channel}})
                    await websocket.send(req)
                resp = await websocket.recv()
                data = json.loads(resp)
                if 'method' in data and data['method'] in ['snapshotOrderbook', 'updateOrderbook']:
                    self.notify(data)
                else:
                    logger.warning("unknown data %s", data)

    def notify(self, data):
        final_data = {'asks': [], 'bids': []}
        final_data['full'] = data['method'] == 'snapshotOrderbook'
        if 'ask' in data['params']:
            final_data['asks'] = [[float(item['price']), float(item['size'])] for item in data['params']['ask']]
        if 'bid' in data['params']:
            final_data['bids'] = [[float(item['price']), float(item['size'])] for item in data['params']['bid']]

        for observer in self.observers:
            if observer.channel != data['params']['symbol']:
                continue
            observer.update(final_data)


class hitbtc_observer(ExchangeObserver):
    def __init__(self, exchange, symbol, callback):
        market = exchange.market(symbol)
        self.channel = market['id'].upper()
        self.callback = callback

    def update(self, data):
        self.callback(data)
