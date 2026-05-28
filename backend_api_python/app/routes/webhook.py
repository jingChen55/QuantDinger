"""
TradingView Webhook Signal Handler

Receives trading signals from TradingView alerts via webhook.
Supports standard TradingView webhook payload format.

TradingView Alert Webhook URL format:
https://your-domain.com/api/webhook/signal?key=YOUR_WEBHOOK_KEY

TradingView sends JSON like:
{
    "action": "buy|sell|close|short|long",
    "symbol": "BTCUSDT",
    "price": 50000.00,        // optional
    "qty": 0.1,               // optional (quantity)
    "limit_price": 49500.00,  // optional
    "stop_price": 51000.00,   // optional
    "comment": "RSI oversold" // optional
}
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import hashlib
import hmac
import time
import logging

from app.utils.db import get_db_connection
from app.utils.logger import get_logger
from app.services.live_trading.execution import place_order_from_signal
from app.services.live_trading.factory import create_client
from app.utils.strategy_runtime_logs import append_strategy_log

logger = get_logger(__name__)

webhook_bp = Blueprint('webhook', __name__)


def _generate_webhook_key(strategy_id: int, user_id: int, secret: str) -> str:
    """Generate a deterministic webhook key for a strategy."""
    raw = f"{strategy_id}:{user_id}:{secret}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _verify_webhook_key(strategy_id: int, user_id: int, provided_key: str) -> bool:
    """Verify the provided webhook key matches the strategy's key."""
    try:
        import os
        from app.utils.db import get_db_connection
        
        secret = os.getenv("WEBHOOK_SECRET", "quantdinger-webhook-secret")
        expected_key = _generate_webhook_key(strategy_id, user_id, secret)
        return hmac.compare_digest(expected_key, provided_key.lower())
    except Exception as e:
        logger.error(f"Webhook key verification failed: {e}")
        return False


def _get_strategy_by_webhook_key(webhook_key: str) -> dict:
    """Find strategy by its webhook key."""
    webhook_key_lower = webhook_key.lower()
    
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
    
    for row in rows:
        row_dict = dict(row)
        trading_config = row_dict.get('trading_config', {})
        if isinstance(trading_config, str):
            try:
                import json
                trading_config = json.loads(trading_config) or {}
            except Exception:
                trading_config = {}
        
        stored_key = trading_config.get('webhook_key', '') or ''
        if stored_key and stored_key.lower() == webhook_key_lower:
            logger.info(f"Found matching strategy {row_dict.get('id')}: status={row_dict.get('status')}")
            row_dict['trading_config'] = trading_config
            return row_dict
        else:
            logger.debug(f"Strategy {row_dict.get('id')}: stored_key='{stored_key}' (type={type(stored_key).__name__}), looking for='{webhook_key_lower}'")
    
    logger.warning(f"No matching strategy found for webhook_key: {webhook_key_lower[:8]}...")
    return {}


def _parse_tradingview_payload(data: dict) -> dict:
    """Parse TradingView webhook payload into standardized signal."""
    action = str(data.get("action", "")).lower().strip()
    
    signal_map = {
        "buy": "long",
        "long": "long",
        "sell": "close_long",
        "close": "close_long",
        "close_long": "close_long",
        "short": "short",
        "close_short": "close_short",
    }
    
    signal_type = signal_map.get(action, action)
    
    symbol = str(data.get("symbol", "")).strip().upper()
    
    price = float(data.get("price") or data.get("limit_price") or 0)
    quantity = float(data.get("qty") or data.get("quantity") or 0)
    stop_price = float(data.get("stop_price") or 0)
    comment = str(data.get("comment") or data.get("message") or "")
    
    return {
        "signal_type": signal_type,
        "symbol": symbol,
        "price": price,
        "quantity": quantity,
        "stop_price": stop_price,
        "comment": comment,
        "timestamp": int(time.time() * 1000),
    }


@webhook_bp.route('/signal', methods=['POST'])
def receive_webhook():
    """
    Main webhook endpoint for TradingView signals.
    
    Query params:
        key: Webhook key (strategy-specific)
    
    Returns:
        200: Signal received and processed
        400: Invalid payload
        401: Invalid webhook key
        404: Strategy not found
    """
    try:
        webhook_key = request.args.get('key', '').strip().lower()
        if not webhook_key:
            logger.warning("Webhook received without key")
            return jsonify({"error": "Missing webhook key"}), 401
        
        strategy = _get_strategy_by_webhook_key(webhook_key)
        if not strategy:
            logger.warning(f"Webhook key not found: {webhook_key[:8]}...")
            return jsonify({"error": "Invalid webhook key or strategy not running"}), 404
        
        strategy_id = strategy.get("id")
        user_id = strategy.get("user_id")
        
        data = request.get_json(silent=True) or {}
        if not data:
            logger.warning(f"Webhook {strategy_id}: Empty payload")
            return jsonify({"error": "Empty payload"}), 400
        
        signal = _parse_tradingview_payload(data)
        logger.info(
            f"Webhook signal received: strategy={strategy_id}, "
            f"signal={signal['signal_type']}, symbol={signal['symbol']}, "
            f"comment={signal.get('comment', '')}"
        )
        
        def _to_dict(val, default=None):
            if val is None:
                return default or {}
            if isinstance(val, dict):
                return val
            if isinstance(val, str):
                try:
                    import json
                    return json.loads(val) or (default or {})
                except Exception:
                    return default or {}
            return default or {}
        
        exchange_config = _to_dict(strategy.get("exchange_config"), {})
        trading_config = _to_dict(strategy.get("trading_config"), {})
        
        logger.info(f"Strategy {strategy_id}: exchange_config={exchange_config}, trading_config keys={list(trading_config.keys())}")
        
        if not exchange_config or not exchange_config.get('exchange_id'):
            logger.error(f"Strategy {strategy_id}: exchange_config is empty or missing exchange_id")
            return jsonify({"error": "Strategy missing exchange_config"}), 400
        
        try:
            from app.services.exchange_execution import resolve_exchange_config
            resolved_exchange_config = resolve_exchange_config(exchange_config, user_id=user_id)
            
            has_api_key = bool(resolved_exchange_config.get('api_key'))
            has_secret = bool(resolved_exchange_config.get('secret_key'))
            
            api_key_info = f"len={len(resolved_exchange_config.get('api_key', ''))}"
            secret_key_info = f"len={len(resolved_exchange_config.get('secret_key', ''))}"
            logger.info(f"Strategy {strategy_id}: exchange_id={resolved_exchange_config.get('exchange_id')}, api_key=({api_key_info}), secret_key=({secret_key_info})")
            
            if not has_api_key or not has_secret:
                logger.error(f"Strategy {strategy_id}: Missing api_key or secret_key")
                logger.error(f"Strategy {strategy_id}: resolved_exchange_config keys: {list(resolved_exchange_config.keys())}")
                return jsonify({"error": "Strategy missing api_key/secret_key"}), 400
        except Exception as e:
            logger.error(f"Strategy {strategy_id}: Failed to resolve exchange_config: {e}")
            return jsonify({"error": f"Failed to resolve credentials: {e}"}), 400
        
        signal_payload = {
            "signal_type": signal["signal_type"],
            "symbol": signal["symbol"],
            "price": signal["price"],
            "quantity": signal["quantity"],
            "stop_price": signal["stop_price"],
            "comment": f"[Webhook] {signal.get('comment', '')}",
            "source": "tradingview_webhook",
        }
        
        try:
            from app.services.live_trading.factory import create_client
            from app.services.live_trading.execution import LiveOrderResult
            
            market_type = trading_config.get('market_type') or resolved_exchange_config.get('market_type') or 'swap'
            client = create_client(resolved_exchange_config, market_type=market_type)
            
            symbol = signal["symbol"]
            quantity = float(signal["quantity"] or 0)
            signal_type = signal["signal_type"]
            
            logger.info(f"Executing: {signal_type} {symbol} qty={quantity} price={signal.get('price')}")
            
            if signal_type == "long":
                result = client.open_long(symbol, quantity, signal.get("price") or None)
            elif signal_type == "short":
                result = client.open_short(symbol, quantity, signal.get("price") or None)
            elif signal_type == "close_long":
                result = client.close_long(symbol, quantity, signal.get("price") or None)
            elif signal_type == "close_short":
                result = client.close_short(symbol, quantity, signal.get("price") or None)
            else:
                raise Exception(f"Unknown signal type: {signal_type}")
            
            append_strategy_log(
                strategy_id,
                "info",
                f"Webhook signal executed: {signal['signal_type']} {signal['symbol']} qty={quantity} - {signal.get('comment', '')}"
            )
            return jsonify({
                "status": "success",
                "message": f"Signal {signal_type} for {symbol} processed",
                "order_id": getattr(result, 'exchange_order_id', None),
            })
            
        except Exception as e:
            logger.error(f"Webhook signal execution failed: {e}")
            append_strategy_log(strategy_id, "error", f"Webhook execution error: {str(e)}")
            return jsonify({
                "status": "error",
                "message": str(e),
            }), 500
            
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return jsonify({"error": str(e)}), 500


@webhook_bp.route('/register', methods=['POST'])
def register_webhook():
    """
    Generate webhook key for a strategy.
    
    Requires authentication.
    """
    from app.utils.auth import login_required
    from flask import g
    
    try:
        user_id = g.user_id
        data = request.get_json() or {}
        strategy_id = data.get("strategy_id")
        
        if not strategy_id:
            return jsonify({"error": "Missing strategy_id"}), 400
        
        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                "SELECT id, user_id, status FROM qd_strategies_trading WHERE id = %s AND user_id = %s",
                (int(strategy_id), int(user_id))
            )
            row = cur.fetchone()
            cur.close()
        
        if not row:
            return jsonify({"error": "Strategy not found"}), 404
        
        import os
        secret = os.getenv("WEBHOOK_SECRET", "quantdinger-webhook-secret")
        webhook_key = _generate_webhook_key(int(strategy_id), int(user_id), secret)
        
        import json
        with get_db_connection() as db:
            cur = db.cursor()
            cur.execute(
                "SELECT trading_config FROM qd_strategies_trading WHERE id = %s",
                (int(strategy_id),)
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
                (new_config_json, int(strategy_id))
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
        return jsonify({"error": str(e)}), 500


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
        "status": "ok",
        "strategy_id": strategy.get("id"),
        "strategy_name": strategy.get("name"),
        "market_category": strategy.get("market_category"),
        "message": "Webhook key is valid and strategy is running"
    })