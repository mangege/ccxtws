import json
import zlib
import websockets
from ccxtws.base import Exchange, ExchangeObserver
from . import logutils

logger = logutils.get_logger('ccxtws')


class okex(Exchange):
    def __init__(self):
        super().__init__()
        # https://www.okex.com/docs/zh/
        self.ws_uri = 'wss://real.okex.com:8443/ws/v3'

    async def _run(self):
        async with websockets.connect(self.ws_uri) as websocket:
            self.ws_conn = websocket
            is_added = False
            while True:
                params = {"op": "subscribe", "args": [f'spot/depth5:{item}' for item in self.channels]}
                if not is_added:
                    req = json.dumps(params)
                    await websocket.send(req)
                    is_added = True
                resp = await websocket.recv()
                decoded_data = zlib.decompress(resp, -15)
                data = json.loads(decoded_data)
                if 'table' in data and data['table'] == 'spot/depth5':
                    self.notify(data)
                else:
                    logger.warning("unknown data %s", data)

    def notify(self, data):
        final_data = {'full': True, 'asks': [], 'bids': []}
        final_data['asks'] = [[float(item[0]), float(item[1])] for item in data['data'][0]['asks']]
        final_data['bids'] = [[float(item[0]), float(item[1])] for item in data['data'][0]['bids']]

        for observer in self.observers:
            if observer.channel != data['data'][0]['instrument_id']:
                continue
            observer.update(final_data)


class okex_observer(ExchangeObserver):
    def __init__(self, exchange, symbol, callback):
        market = exchange.market(symbol)
        self.channel = market['id']
        self.callback = callback

    def update(self, data):
        self.callback(data)
