import json
import gzip
import websockets
from ccxtws.base import Exchange, ExchangeObserver, logger
from . import utils


class huobipro(Exchange):
    def __init__(self):
        super().__init__()
        # https://huobiapi.github.io/docs/spot/v1/cn/#5ea2e0cde2-11
        self.ws_uri = 'wss://api.huobi.pro/ws'
        self.max_observers = 10

    async def _run(self):
        async with websockets.connect(self.ws_uri) as websocket:
            self.ws_conn = websocket
            added_channels = set()
            while True:
                for channel in self.channels:
                    if channel in added_channels:
                        continue
                    added_channels.add(channel)
                    req = json.dumps({"sub": f"market.{channel}.mbp.refresh.5", "id": utils.get_req_id()})
                    await websocket.send(req)
                resp = await websocket.recv()
                decoded_data = gzip.decompress(resp)
                data = json.loads(decoded_data)
                if 'ping' in data:
                    req = json.dumps({"pong": data['ping']})
                    await websocket.send(req)
                else:
                    self.notify(data)

    def notify(self, data):
        if 'tick' not in data:
            logger.warning("unknown data %s", data)
            return
        final_data = {'full': True, 'asks': [], 'bids': []}
        final_data['asks'] = [[float(item[0]), float(item[1])] for item in data['tick']['asks']]
        final_data['bids'] = [[float(item[0]), float(item[1])] for item in data['tick']['bids']]

        for observer in self.observers:
            if observer.channel not in data['ch']:
                continue
            observer.update(final_data)


class huobipro_observer(ExchangeObserver):
    def __init__(self, exchange, symbol, callback):
        market = exchange.market(symbol)
        self.channel = market['id']
        self.callback = callback

    def update(self, data):
        self.callback(data)
