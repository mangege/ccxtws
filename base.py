from abc import ABCMeta, abstractmethod


# https://refactoringguru.cn/design-patterns/observer/python/example
class ExchangeBoost(metaclass=ABCMeta):
    @abstractmethod
    def subscribe(self, observer):
        pass

    @abstractmethod
    def unsubscribe(self, observer):
        pass

    @abstractmethod
    def notify(self, data):
        pass


class ExchangeObserver(metaclass=ABCMeta):
    # data format: {full: True, 'asks': [[price, volume], ...], 'bids': [[price, volume], ...]}
    # full 是否全量更新
    @abstractmethod
    def update(self, data):
        pass


class Exchange(ExchangeBoost, metaclass=ABCMeta):
    @abstractmethod
    async def run(self):
        pass
