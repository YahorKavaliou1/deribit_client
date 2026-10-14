# Deribit Client

A service that fetches the current index price of `btc_usd` and `eth_usd` from the
[Deribit](https://docs.deribit.com/) exchange every minute (via Celery), stores the ticker,
price and UNIX timestamp in PostgreSQL, and exposes the saved data through an external
FastAPI-based API.
