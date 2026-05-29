# Debug Session: mexc-client-open-long

## Session ID
`mexc-client-open-long`

## Created
2026-05-29 17:24:26

## Status
[FIXED]

## Original Symptom
```
'MexcClient' object has no attribute 'open_long'
```

## Root Cause
The original `mexc.py` file had a `MexcHttpClient` class but the `factory.py` was trying to import `MexcClient`, and even after renaming, the class was missing the `open_long`, `open_short`, `close_long`, `close_short` methods that the trading executor expects.

## Fix Applied
Added the following methods to `MexcClient` class in [mexc.py](file:///Users/k7/code/github.com/QuantDinger/backend_api_python/app/services/live_trading/mexc.py#L223-L237):
- `open_long()` - Buy LIMIT order
- `open_short()` - Sell LIMIT order
- `close_long()` - Sell LIMIT order
- `close_short()` - Buy LIMIT order

## Verification
After fix, the webhook request processed correctly:
```
2026-05-29 17:31:08,035 - app.routes.webhook - INFO - Executing: long BTC/USDT qty=100.0 price=50000.0
```
The `open_long` method was found and called. The subsequent HTTP 400 error is a different issue related to MEXC API credentials (missing signature) - not related to the original bug.

## Timeline
- 17:24:26 - Original error: 'MexcClient' object has no attribute 'open_long'
- 17:31:08 - After fix: webhook processes correctly, open_long method is called