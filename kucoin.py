import json
import asyncio
import websockets
from ccxtws.base import Exchange, ExchangeObserver
from . import logutils
from . import utils

logger = logutils.get_logger('ccxtws')

INTERVALS = {"SUSHI_USDT": "0.001"}


class kucoin(Exchange):
    def __init__(self):
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
        exchange = self.observers[0].exchange
        resp = await exchange.publicPostBulletPublic()
        endpoint = resp['data']['instanceServers'][0]['endpoint']
        token = resp['data']['token']
        ws_uri = f'{endpoint}?token={token}'
        async with websockets.connect(ws_uri) as websocket:
            is_available = False
            is_added = False
            while True:
                if not is_available:
                    resp = await websocket.recv()
                    data = json.loads(resp)
                    if data['type'] == 'welcome':
                        is_available = True
                    else:
                        asyncio.sleep(1)
                        continue
                if not is_added:
                    params = {"id": utils.get_req_id(), "type": "subscribe",
                              "topic": f"/spotMarket/level2Depth5:{','.join(self.channels)}", "privateChannel": False, "response": True}
                    req = json.dumps(params)
                    await websocket.send(req)
                    is_added = True
                resp = await websocket.recv()
                data = json.loads(resp)
                if 'subject' in data and data['subject'] == 'level2':
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
        final_data = {'full': True, 'asks': [], 'bids': []}
        final_data['asks'] = [[float(item[0]), float(item[1])] for item in data['data']['asks']]
        final_data['bids'] = [[float(item[0]), float(item[1])] for item in data['data']['bids']]

        for observer in self.observers:
            if observer.channel not in data['topic']:
                continue
            observer.update(final_data)


class kucoin_observer(ExchangeObserver):
    def __init__(self, exchange, symbol, callback):
        self.exchange = exchange
        market = exchange.market(symbol)
        self.channel = market['id'].upper()
        self.callback = callback

    def update(self, data):
        self.callback(data)
