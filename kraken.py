import asyncio
import json
import websockets
from ccxtws.base import Exchange, ExchangeObserver, logger
from . import utils


class kraken(Exchange):
    def __init__(self):
        super().__init__()
        # https://docs.kraken.com/websockets/
        self.ws_uri = 'wss://ws.kraken.com'
        self.max_observers = 1024

    async def _run(self):
        async with websockets.connect(self.ws_uri, ping_interval=None) as websocket:
            self.ws_conn = websocket
            is_added = False
            while True:
                if not is_added:
                    req = json.dumps({"event": "subscribe", "subscription": {"name": "book", "depth": 10}, "pair": self.channels})
                    await websocket.send(req)
                    is_added = True
                resp = await websocket.recv()
                data = json.loads(resp)
                if 'event' in data:
                    if data['event'] == 'subscriptionStatus':
                        logger.info(f"kraken's subscription status: data['status']")
                elif isinstance(data, list):
                    self.notify(data)
                else:
                    logger.warning("unknown data %s", data)

    def notify(self, data):
        if len(data) < 4:
            logger.warning("unknown data %s", data)
            return
        pair = data[-1]
        orderbook = data[1]
        final_data = {'asks': [], 'bids': []}

        ask_key = 'a'
        bid_key = 'b'

        if 'as' in orderbook:
            final_data['full'] = True
            ask_key = 'as'
            bid_key = 'bs'
        else:
            final_data['full'] = False

        if ask_key in orderbook:
            final_data['asks'] = [[float(item[0]), float(item[1])] for item in orderbook[ask_key]]
        if bid_key in orderbook:
            final_data['bids'] = [[float(item[0]), float(item[1])] for item in orderbook[bid_key]]

        for observer in self.observers:
            if observer.channel != pair:
                continue
            observer.update(final_data)

class kraken_observer(ExchangeObserver):
    def __init__(self, exchange, symbol, callback):
        market = exchange.market(symbol)
        self.channel = market['id']
        self.callback = callback

    def update(self, data):
        self.callback(data)
