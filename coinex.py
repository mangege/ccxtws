import json
import websockets
from ccxtws.base import Exchange, ExchangeObserver, logger
from . import utils


class coinex(Exchange):
    def __init__(self):
        super().__init__()
        # https://github.com/coinexcom/coinex_exchange_api/wiki/041request_description
        self.ws_uri = 'wss://socket.coinex.com/'
        self.ping_sleep_time = 5
        self.max_observers = -1

    async def _run(self):
        async with websockets.connect(self.ws_uri, ping_interval=None) as websocket:
            self.ws_conn = websocket
            is_added = False
            while True:
                if not is_added:
                    params = [[item, 5, '0']for item in self.channels]
                    req = json.dumps({"id": utils.get_req_id(), "method": "depth.subscribe_multi", "params": params})
                    await websocket.send(req)
                    is_added = True
                resp = await websocket.recv()
                data = json.loads(resp)
                if 'method' in data and data['method'] == 'depth.update':
                    self.notify(data)
                else:
                    logger.warning("unknown data %s", data)

    async def _ping(self):
        req = json.dumps({"id": utils.get_req_id(), "method": "server.ping", "params": []})
        await self.ws_conn.send(req)

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


class coinex_observer(ExchangeObserver):
    def __init__(self, exchange, symbol, callback):
        market = exchange.market(symbol)
        self.channel = market['id'].upper()
        self.callback = callback

    def update(self, data):
        self.callback(data)
