from ccxtws.poloniex import poloniex, poloniex_observer  # noqa: F401
from ccxtws.biki import biki, biki_observer  # noqa: F401
from ccxtws.huobipro import huobipro, huobipro_observer  # noqa: F401
from ccxtws.gateio import gateio, gateio_observer  # noqa: F401
from ccxtws.bibox import bibox, bibox_observer  # noqa: F401
from ccxtws.bitmax import bitmax, bitmax_observer  # noqa: F401
from ccxtws.kucoin import kucoin, kucoin_observer  # noqa: F401

exchanges_ws = [
    'poloniex', 'poloniex_observer',
    'biki', 'biki_observer',
    'huobipro', 'huobipro_observer',
    'gateio', 'gateio_observer',
    'bibox', 'bibox_observer',
    'bitmax', 'bitmax_observer',
    'kucoin', 'kucoin_observer',
]

__all__ = exchanges_ws
