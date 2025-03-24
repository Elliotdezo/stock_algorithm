class Ticker:
    def init(self, name, volume):
        self.name = name
        self.volume = volume


def transformer_ticker_data(ticker_input) -> Ticker:
    name = ticker_input["Ticker_val"]
    volume = ticker_input["Volume_val"]

    ticker_output = Ticker(name, volume)
    return ticker_output