"""
Webhook signal routes for TradingView integration.
"""
from flask import Blueprint, request, jsonify
import logging
import time
import hashlib
import base64
import hmac

logger = logging.getLogger(__name__)
webhook_bp = Blueprint('webhook', __name__)


def _generate_webhook_key(strategy_id: int, user_id: int, secret: str) -> str:
    """Generate deterministic webhook key from strategy_id, user_id, and secret."""
    message = f"{strategy_id}:{user_id}:{secret}"
    return hashlib.sha256(message.encode()).hexdigest()[:32]


def _parse_tradingview_payload(data: dict) -> dict:
    """
    Parse TradingView webhook payload into internal signal format.
    
    TradingView sends:
        buy / long -> open long position
        sell / close -> close long position
        short -> open short position
        close_short -> close short position
    """
    action = str(data.get("action", "")).strip().lower()
    symbol = str(data.get("symbol", "")).strip().upper()
    quantity = float(data.get("qty") or data.get("quantity") or 0)
    price = float(data.get("price") or 0)
    comment = str(data.get("comment", "")).strip()

    signal_type = action
    if action in ("buy", "long"):
        signal_type = "long"
    elif action in ("sell", "close"):
        signal_type = "close_long"
    elif action == "short":
        signal_type = "short"
    elif action == "close_short":
        signal_type = "close_short"

    if "/" not in symbol and len(symbol) > 6:
        base = symbol[:3]
        quote = symbol[3:]
        symbol = f"{base}/{quote}"

    return {
        "signal_type": signal_type,
        "symbol": symbol,
        "quantity": quantity,
        "price": price,
        "comment": comment,
        "timestamp": int(time.time() * 1000),
    }


def _get_strategy_by_webhook_key(webhook_key: str) -> dict:
    """Find strategy by its webhook key."""
    webhook_key_lower = webhook_key.lower().strip()
    webhook_key_lower_lower = webhook_key_lower.lower()

    # Import here to avoid circular imports and use same secret as get_strategy_webhook_url
    import os
    import hashlib

    secret = os.getenv("WEBHOOK_SECRET", "quantdinger-webhook-secret")

    from app.utils.db import get_db_connection

    with get_db_connection() as db:
        cur = db.cursor()
        cur.execute(
            """
            SELECT id, user_id, exchange_config, trading_config, market_type,
                   market_category, status, strategy_name as name
            FROM qd_strategies_trading
            WHERE trading_config IS NOT NULL
            ORDER BY id ASC
            LIMIT 200
            """
        )
        rows = cur.fetchall() or []
        cur.close()

    logger.info(f"Searching for webhook_key='{webhook_key_lower}' among {len(rows)} strategies")

    import json as json_module
    found_keys = []
    for row in rows:
        row_dict = dict(row)
        strategy_id = row_dict.get('id', 0)
        user_id = row_dict.get('user_id', 1)
        trading_config = row_dict.get('trading_config', {})
        if isinstance(trading_config, str):
            try:
                trading_config = json_module.loads(trading_config) or {}
            except Exception:
                trading_config = {}

        stored_key = trading_config.get('webhook_key', '') or ''

        # Compute the dynamic key the same way get_strategy_webhook_url does
        dynamic_key = hashlib.sha256(f"{strategy_id}:{user_id}:{secret}".encode()).hexdigest()[:32]

        found_keys.append({
            'strategy_id': strategy_id,
            'stored_key': stored_key,
            'dynamic_key': dynamic_key,
        })

        # Match against both stored key and dynamically generated key
        if stored_key and stored_key.lower() == webhook_key_lower:
            logger.info(f"Found matching strategy {strategy_id} via stored key: status={row_dict.get('status')}")
            row_dict['trading_config'] = trading_config
            return row_dict
        elif dynamic_key.lower() == webhook_key_lower:
            logger.info(f"Found matching strategy {strategy_id} via dynamic key: status={row_dict.get('status')}")
            row_dict['trading_config'] = trading_config
            return row_dict

    logger.warning(f"No matching strategy found for webhook_key: {webhook_key_lower[:8]}...")
    logger.warning(f"All found keys: {found_keys}")
    return {}


@webhook_bp.route('/register', methods=['POST'])
def register_webhook():
    """
    Generate webhook key for a strategy.
    
    No authentication required - generates key for any strategy_id.
    """
    import traceback
    import os
    import json
    
    try:
        data = request.get_json() or {}
        strategy_id = data.get("strategy_id")
        
        if not strategy_id:
            return jsonify({"error": "Missing strategy_id"}), 400
        
        try:
            strategy_id_int = int(strategy_id)
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid strategy_id"}), 400
        
        from app.utils.db import get_db_connection
        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                "SELECT id, user_id, status FROM qd_strategies_trading WHERE id = %s",
                (strategy_id_int,)
            )
            row = cur.fetchone()
            cur.close()
            
            if not row:
                return jsonify({"error": "Strategy not found"}), 404
            
            user_id = 1
            if isinstance(row, dict):
                user_id = int(row.get('user_id', 1) or 1)
            elif isinstance(row, (tuple, list)):
                if len(row) > 1 and row[1]:
                    user_id = int(row[1])
            
            secret = os.getenv("WEBHOOK_SECRET", "quantdinger-webhook-secret")
            webhook_key = _generate_webhook_key(strategy_id_int, user_id, secret)
        
        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                "SELECT trading_config FROM qd_strategies_trading WHERE id = %s",
                (strategy_id_int,)
            )
            row = cur.fetchone()
            if row:
                raw_config = row[0]
                if isinstance(raw_config, str):
                    try:
                        config_dict = json.loads(raw_config) or {}
                    except Exception:
                        config_dict = {}
                elif isinstance(raw_config, dict):
                    config_dict = raw_config
                else:
                    config_dict = {}
            else:
                config_dict = {}
            
            config_dict['webhook_key'] = webhook_key
            new_config_json = json.dumps(config_dict)
            
            cur.execute(
                "UPDATE qd_strategies_trading SET trading_config = %s WHERE id = %s",
                (new_config_json, strategy_id_int)
            )
            db.commit()
            cur.close()
        
        base_url = os.getenv("WEBHOOK_BASE_URL", request.host_url.rstrip("/"))
        webhook_url = f"{base_url}/api/webhook/signal?key={webhook_key}"
        
        return jsonify({
            "webhook_key": webhook_key,
            "webhook_url": webhook_url,
            "instructions": {
                "tradingview_alert": {
                    "webhook_url": webhook_url,
                    "method": "POST",
                    "body_type": "json",
                    "example_payload": {
                        "action": "buy",
                        "symbol": "BTCUSDT",
                        "qty": 0.01,
                        "comment": "RSI oversold"
                    }
                }
            }
        })
    
    except Exception as e:
        logger.error(f"Webhook registration error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e), "type": type(e).__name__}), 500


@webhook_bp.route('/test', methods=['POST'])
def test_webhook():
    """
    Test endpoint to verify webhook configuration.
    
    Query params:
        key: Webhook key
    
    Returns:
        200: Strategy info if valid
        404: Invalid key
    """
    webhook_key = request.args.get('key', '').strip().lower()
    if not webhook_key:
        return jsonify({"error": "Missing webhook key"}), 401
    
    strategy = _get_strategy_by_webhook_key(webhook_key)
    
    if not strategy:
        return jsonify({"error": "Invalid webhook key"}), 404
    
    return jsonify({
        "status": "valid",
        "strategy_id": strategy.get("id"),
        "strategy_name": strategy.get("name"),
        "status": strategy.get("status"),
    })


@webhook_bp.route('/signal', methods=['POST', 'OPTIONS'])
def webhook_signal():
    """
    Main webhook endpoint for receiving TradingView signals.
    
    Query params:
        key: Webhook key (required)
    
    Body (JSON):
        action: buy/sell/short/close_short
        symbol: Trading symbol (e.g., BTC/USDT)
        qty or quantity: Position size
        price: Optional limit price
        comment: Optional comment
    
    Returns:
        200: Signal processed successfully
        400: Invalid signal
        404: Invalid webhook key
        500: Execution error
    """
    import json
    
    if request.method == 'OPTIONS':
        return '', 200
    
    webhook_key = request.args.get('key', '').strip().lower()
    if not webhook_key:
        logger.warning("Webhook signal missing key")
        return jsonify({"error": "Missing webhook key"}), 401
    
    logger.info(f"Webhook signal request: key={webhook_key[:8]}...")
    
    strategy = _get_strategy_by_webhook_key(webhook_key)
    
    if not strategy:
        logger.warning(f"Webhook key not found: {webhook_key[:8]}...")
        return jsonify({"error": "Invalid webhook key or strategy not running"}), 404
    
    strategy_id = strategy.get("id")
    user_id = strategy.get("user_id", 1)
    
    try:
        data = request.get_json(silent=True)
        if not data:
            raw_data = request.data
            if raw_data:
                try:
                    data = json.loads(raw_data)
                except Exception:
                    pass
        if not data:
            logger.error(f"Webhook: Failed to parse request body. Content-Type={request.content_type}, data_len={len(request.data)}")
            return jsonify({"error": "Missing or invalid request body"}), 400
        logger.info(f"Webhook request body: {data}")
    except Exception as e:
        logger.error(f"Webhook: JSON parse error: {e}")
        return jsonify({"error": "Invalid JSON body"}), 400
    
    def _to_dict(val, default=None):
        if val is None:
            return default or {}
        if isinstance(val, dict):
            return val
        if isinstance(val, str):
            try:
                return json.loads(val) or (default or {})
            except Exception:
                return default or {}
        return default or {}
    
    exchange_config = _to_dict(strategy.get("exchange_config"), {})
    trading_config = _to_dict(strategy.get("trading_config"), {})
    
    logger.info(f"Strategy {strategy_id}: exchange_config keys={list(exchange_config.keys())}, trading_config keys={list(trading_config.keys())}")
    
    if not exchange_config or not exchange_config.get('exchange_id'):
        logger.error(f"Strategy {strategy_id}: exchange_config is empty or missing exchange_id")
        return jsonify({"error": "Strategy missing exchange_config"}), 400
    
    try:
        from app.services.exchange_execution import resolve_exchange_config
        resolved_exchange_config = resolve_exchange_config(exchange_config, user_id=user_id)
        
        has_api_key = bool(resolved_exchange_config.get('api_key'))
        has_secret = bool(resolved_exchange_config.get('secret_key'))
        
        logger.info(f"Strategy {strategy_id}: exchange_id={resolved_exchange_config.get('exchange_id')}, api_key present={has_api_key}, secret present={has_secret}")
        
        if not has_api_key or not has_secret:
            logger.error(f"Strategy {strategy_id}: Missing api_key or secret_key after credential resolution")
            return jsonify({"error": "Strategy missing api_key/secret_key"}), 400
    except Exception as e:
        logger.error(f"Strategy {strategy_id}: Failed to resolve exchange_config: {e}")
        return jsonify({"error": f"Failed to resolve credentials: {e}"}), 400
    
    signal = _parse_tradingview_payload(data)
    logger.info(
        f"Webhook signal received: strategy={strategy_id}, "
        f"signal={signal['signal_type']}, symbol={signal['symbol']}, "
        f"comment={signal.get('comment', '')}"
    )
    
    signal_payload = {
        "signal_type": signal["signal_type"],
        "symbol": signal["symbol"],
        "price": signal.get("price"),
        "quantity": signal.get("quantity"),
        "stop_price": signal.get("stop_price"),
        "comment": f"[Webhook] {signal.get('comment', '')}",
        "source": "tradingview_webhook",
    }
    
    try:
        from app.services.live_trading.factory import create_client
        from app.services.live_trading.execution import LiveOrderResult
        
        market_type = trading_config.get('market_type') or resolved_exchange_config.get('market_type') or 'swap'
        client = create_client(resolved_exchange_config, market_type=market_type)
        
        symbol = signal["symbol"]
        quantity = float(signal.get("quantity") or 0)
        signal_type = signal["signal_type"]
        
        order_price = signal.get("price")
        if not order_price and hasattr(client, 'get_latest_price'):
            order_price = client.get_latest_price(symbol)
            logger.info(f"Using latest price from MEXC: {order_price}")
        
        logger.info(f"Executing: {signal_type} {symbol} qty={quantity} price={order_price}")
        
        if signal_type == "long":
            result = client.open_long(symbol, quantity, order_price)
        elif signal_type == "short":
            result = client.open_short(symbol, quantity, order_price)
        elif signal_type == "close_long":
            result = client.close_long(symbol, quantity, order_price)
        elif signal_type == "close_short":
            result = client.close_short(symbol, quantity, order_price)
        else:
            raise Exception(f"Unknown signal type: {signal_type}")
        
        order_id = getattr(result, 'exchange_order_id', '') or ''
        filled_qty = float(getattr(result, 'filled', quantity) or quantity)
        avg_price = float(getattr(result, 'avg_price', order_price) or order_price)

        from app.services.live_trading.records import record_trade, apply_fill_to_local_position
        record_trade(
            strategy_id=strategy_id,
            symbol=symbol,
            trade_type=signal_type,
            price=avg_price,
            amount=filled_qty,
            user_id=user_id,
        )
        profit, updated_pos = apply_fill_to_local_position(
            strategy_id=strategy_id,
            symbol=symbol,
            signal_type=signal_type,
            filled=filled_qty,
            avg_price=avg_price,
        )
        logger.info(f"Trade recorded: symbol={symbol}, type={signal_type}, qty={filled_qty}, price={avg_price}, profit={profit}")

        from app.utils.strategy_runtime_logs import append_strategy_log
        append_strategy_log(
            strategy_id,
            "info",
            f"Webhook signal executed: {signal['signal_type']} {signal['symbol']} qty={quantity} - order_id={order_id}"
        )
        return jsonify({
            "status": "success",
            "message": f"Signal {signal_type} for {symbol} processed",
            "order_id": order_id,
        })
        
    except Exception as e:
        logger.error(f"Webhook signal execution failed: {e}")
        from app.utils.strategy_runtime_logs import append_strategy_log
        append_strategy_log(strategy_id, "error", f"Webhook execution error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500
