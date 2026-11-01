"""Continuous double auction for one trading period (rules in APPROACH.md, Fixed decisions)."""

from dataclasses import dataclass

from task import APPLICANTS

CASH = 200
SHARES = 2
MIN_PRICE, MAX_PRICE = 0, 200
DIVIDEND_GBP = 2
GBP_PER_ECU = 2 / 100


class InvalidAction(ValueError):
    """Rule violation; the message is shown to the agent as feedback."""


@dataclass
class Order:
    id: int
    trader: int
    applicant: str
    side: str  # "bid" or "ask"
    price: int


class Market:
    def __init__(self, traders):
        self.cash = {t: CASH for t in traders}
        self.shares = {t: {a: SHARES for a in APPLICANTS} for t in traders}
        self.orders = []  # open orders, in submission order
        self.trades = []  # (applicant, price, buyer, seller)
        self.submitted = []  # every bid/ask submitted, including ones that traded at once (for spreads)
        self._next_id = 1

    # --- accounting -------------------------------------------------------

    def available_cash(self, t):
        return self.cash[t] - sum(o.price for o in self.orders if o.trader == t and o.side == "bid")

    def available_shares(self, t, a):
        return self.shares[t][a] - sum(1 for o in self.orders if o.trader == t and o.side == "ask" and o.applicant == a)

    def _best(self, side, a, exclude):
        """Best standing order on `side` for applicant `a` from someone other than `exclude`; price then time priority."""
        book = [o for o in self.orders if o.side == side and o.applicant == a and o.trader != exclude]
        if not book:
            return None
        return min(book, key=lambda o: (o.price if side == "ask" else -o.price, o.id))

    def _trade(self, a, price, buyer, seller):
        self.cash[buyer] -= price
        self.cash[seller] += price
        self.shares[buyer][a] += 1
        self.shares[seller][a] -= 1
        trade = (a, price, buyer, seller)
        self.trades.append(trade)
        return trade

    # --- actions ----------------------------------------------------------

    def bid(self, t, a, price):
        self._check(a, price)
        if price > self.available_cash(t):
            raise InvalidAction(f"Bid of {price} ECU exceeds your available cash of {self.available_cash(t)} ECU.")
        self.submitted.append(("bid", a, price))
        ask = self._best("ask", a, exclude=t)
        if ask and price >= ask.price:
            self.orders.remove(ask)
            return self._trade(a, ask.price, buyer=t, seller=ask.trader)
        return self._place(t, a, "bid", price)

    def ask(self, t, a, price):
        self._check(a, price)
        if self.available_shares(t, a) < 1:
            raise InvalidAction(f"You have no available share of applicant {a} to sell.")
        self.submitted.append(("ask", a, price))
        bid = self._best("bid", a, exclude=t)
        if bid and price <= bid.price:
            self.orders.remove(bid)
            return self._trade(a, bid.price, buyer=bid.trader, seller=t)
        return self._place(t, a, "ask", price)

    def buy(self, t, a):
        self._check(a)
        ask = self._best("ask", a, exclude=t)
        if not ask:
            raise InvalidAction(f"There is no ask from another participant for applicant {a}.")
        if ask.price > self.available_cash(t):
            raise InvalidAction(f"The lowest ask ({ask.price} ECU) exceeds your available cash of {self.available_cash(t)} ECU.")
        self.orders.remove(ask)
        return self._trade(a, ask.price, buyer=t, seller=ask.trader)

    def sell(self, t, a):
        self._check(a)
        bid = self._best("bid", a, exclude=t)
        if not bid:
            raise InvalidAction(f"There is no bid from another participant for applicant {a}.")
        if self.available_shares(t, a) < 1:
            raise InvalidAction(f"You have no available share of applicant {a} to sell.")
        self.orders.remove(bid)
        return self._trade(a, bid.price, buyer=bid.trader, seller=t)

    def cancel(self, t, order_id):
        for o in self.orders:
            if o.id == order_id and o.trader == t:
                self.orders.remove(o)
                return o
        raise InvalidAction(f"You have no open order #{order_id}.")

    def _check(self, a, price=None):
        if a not in APPLICANTS:
            raise InvalidAction(f"Unknown applicant {a!r}.")
        if price is not None and not (type(price) is int and MIN_PRICE <= price <= MAX_PRICE):
            raise InvalidAction(f"Price must be a whole number from {MIN_PRICE} to {MAX_PRICE} ECU.")

    def _place(self, t, a, side, price):
        o = Order(self._next_id, t, a, side, price)
        self._next_id += 1
        self.orders.append(o)
        return o

    # --- observation and outcomes ----------------------------------------

    def state(self, t):
        """Text for the {market_state} placeholder, as seen by trader t. Others are not identified."""
        lines = []
        for a in APPLICANTS:
            asks = sorted(o.price for o in self.orders if o.applicant == a and o.side == "ask")
            bids = sorted((o.price for o in self.orders if o.applicant == a and o.side == "bid"), reverse=True)
            prices = [p for (x, p, _, _) in self.trades if x == a]
            lines.append(
                f"Applicant {a}: asks {_fmt(asks)}; bids {_fmt(bids)}; trade prices this period (oldest first) {_fmt(prices)}"
            )
        own = [o for o in self.orders if o.trader == t]
        lines.append("Your open orders: " + (", ".join(f"#{o.id} {o.side} {o.applicant} at {o.price}" for o in own) or "none"))
        return "\n".join(lines)

    def holdings(self, t):
        """Text for the {holdings} placeholder."""
        return ", ".join(f"{a}: {self.shares[t][a]} (available: {self.available_shares(t, a)})" for a in APPLICANTS)

    def spreads(self):
        """Data B measure: total ask money minus total bid money submitted, per applicant."""
        return {a: sum(p if s == "ask" else -p for s, x, p in self.submitted if x == a) for a in APPLICANTS}

    def payoff_gbp(self, t, best):
        """Market earnings if this period is paid: dividends plus cash at 100 ECU = £2."""
        return DIVIDEND_GBP * self.shares[t][best] + GBP_PER_ECU * self.cash[t]


def _fmt(prices):
    return ", ".join(map(str, prices)) if prices else "none"
