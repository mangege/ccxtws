import json
import base64
import gzip
import websockets
from ccxtws.base import Exchange, ExchangeObserver
from . import logutils
from . import utils

logger = logutils.get_logger('ccxtws')


class bibox(Exchange):
    def __init__(self):
        super().__init__()
        # https://biboxcom.github.io/zh-hans/
        self.ws_uri = 'wss://push.bibox.com'
        self.ping_sleep_time = 60

    async def _run(self):
        async with websockets.connect(self.ws_uri) as websocket:
            self.ws_conn = websocket
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
                elif 'pong' in data:
                    logger.warning("ping data %s", data)
                else:
                    self.notify(data)

    async def _ping(self):
        req = json.dumps({"ping": utils.get_req_id()})
        await self.ws_conn.send(req)

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
