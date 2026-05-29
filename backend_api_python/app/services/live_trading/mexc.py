"""
MEXC (direct REST) client for spot / perpetual swap orders.

API Base URL: https://api.mexc.com

Signing:
- Signature = HMAC_SHA256(secret, stringToSign)
- stringToSign = HTTP_METHOD + "\n" + REQUEST_PATH + "\n" + TIMESTAMP + "\n" + BODY
- Headers: Key, Timestamp, Signature
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import logging
from decimal import Decimal, ROUND_DOWN
from typing import Any, Dict, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

from app.services.live_trading.base import BaseRestClient, LiveOrderResult, LiveTradingError
from app.services.live_trading.symbols import to_mexc_symbol, to_mexc_swap_symbol


class MexcClient(BaseRestClient):
    """
    MEXC REST client for spot and perpetual swap trading.

    Supports both spot and swap (perpetual futures) markets.
    """

    def __init__(
        self,
        *,
        api_key: str,
        secret_key: str,
        passphrase: str = "",
        base_url: str = "https://api.mexc.com",
        timeout_sec: float = 15.0,
        market_type: str = "swap",
    ):
        super().__init__(base_url=base_url, timeout_sec=timeout_sec)
        self.api_key = (api_key or "").strip()
        self.secret_key = (secret_key or "").strip()
        self.passphrase = (passphrase or "").strip()
        self.market_type = (market_type or "swap").strip().lower()
        if self.market_type not in ("swap", "spot"):
            self.market_type = "swap"

        if not self.api_key or not self.secret_key:
            raise LiveTradingError("Missing MEXC api_key/secret_key")

        self._inst_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._inst_cache_ttl_sec = 300.0

        self._lev_cache: Dict[str, Tuple[float, bool]] = {}
        self._lev_cache_ttl_sec = 60.0

    @staticmethod
    def _to_dec(x: Any) -> Decimal:
        try:
            return Decimal(str(x))
        except Exception:
            return Decimal("0")

    @staticmethod
    def _dec_str(d: Decimal, max_decimals: int = 18, strict_precision: Optional[int] = None) -> str:
        try:
            if d == 0:
                return "0"
            normalized = d.normalize()

            if strict_precision is not None:
                try:
                    prec = int(strict_precision)
                    if 0 <= prec <= 18:
                        q = Decimal("1").scaleb(-prec)
                        quantized = normalized.quantize(q, rounding=ROUND_DOWN)
                        s = format(quantized, f".{prec}f")
                        if "." in s:
                            s = s.rstrip("0").rstrip(".")
                        return s if s else "0"
                except Exception:
                    pass

            s = format(normalized, f".{max_decimals}f")
            if "." in s:
                s = s.rstrip("0").rstrip(".")
            return s if s else "0"
        except Exception:
            try:
                f = float(d)
                if f == 0:
                    return "0"
                if strict_precision is not None:
                    try:
                        prec = int(strict_precision)
                        if 0 <= prec <= 18:
                            s = format(f, f".{prec}f")
                            if "." in s:
                                s = s.rstrip("0").rstrip(".")
                            return s if s else "0"
                    except Exception:
                        pass
                s = format(f, f".{max_decimals}f")
                if "." in s:
                    s = s.rstrip("0").rstrip(".")
                return s if s else "0"
            except Exception:
                s = str(d)
                if "e" in s.lower() or "E" in s:
                    try:
                        f = float(s)
                        if strict_precision is not None:
                            try:
                                prec = int(strict_precision)
                                if 0 <= prec <= 18:
                                    s = format(f, f".{prec}f")
                                    if "." in s:
                                        s = s.rstrip("0").rstrip(".")
                                    return s if s else "0"
                            except Exception:
                                pass
                        s = format(f, f".{max_decimals}f")
                        if "." in s:
                            s = s.rstrip("0").rstrip(".")
                    except Exception:
                        pass
                return s if s else "0"

    def _sign(self, sign_target) -> str:
        logger.debug(f"Sign target: {sign_target}")
        mac = hmac.new(
            self.secret_key.encode('utf-8'),
            sign_target.encode('utf-8'),
            hashlib.sha256
        )
        return mac.hexdigest()

    # 帶 body  headder 簽名
    def _generate_signature_with_body(self, timestamp: str, body_raw: str) -> str:
        sign_target = self.api_key + timestamp + body_raw
        return {
            "ApiKey": self.api_key,
            "Request-Time": timestamp,
            "Signature":  self._sign(sign_target),
            "Content-Type": "application/json",
        }

    def _get_symbol(self, symbol: str) -> str:
        if self.market_type == "swap":
            return to_mexc_swap_symbol(symbol)
        return to_mexc_symbol(symbol)

    def _get_instrument_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        cache_key = f"{self.market_type}:{symbol}"
        now = time.time()
        if cache_key in self._inst_cache:
            stored_at, info = self._inst_cache[cache_key]
            if now - stored_at < self._inst_cache_ttl_sec:
                return info

        try:
            if self.market_type == "swap":
                path = f"/api/v1/private/contract/{symbol}"
            else:
                path = f"/api/v3/account/avgPrice?symbol={symbol}"
            status, resp, _ = self._request("GET", path)
            if status == 200:
                info = resp if isinstance(resp, dict) else {}
                self._inst_cache[cache_key] = (now, info)
                return info
        except Exception:
            pass
        return None

    def set_leverage(self, symbol: str, leverage: int = 1) -> bool:
        cache_key = f"{symbol}:{leverage}"
        now = time.time()
        if cache_key in self._lev_cache:
            stored_at, success = self._lev_cache[cache_key]
            if now - stored_at < self._lev_cache_ttl_sec:
                return success

        try:
            contract_code = to_mexc_swap_symbol(symbol)
            path = "/api/v1/private/position/change_leverage"
            body = json.dumps({"contract_code": contract_code, "lever_rate": leverage})
            headers = self._headers(path, json.dumps(body))
            status, resp, _ = self._request("POST", path, json_body={"contract_code": contract_code, "lever_rate": leverage}, headers=headers)
            success = status == 200
            self._lev_cache[cache_key] = (now, success)
            return success
        except Exception as e:
            self._lev_cache[cache_key] = (now, False)
            return False

    def get_balance(self) -> Dict[str, float]:
        try:
            if self.market_type == "swap":
                path = "/api/v1/private/balance"
            else:
                path = "/api/v3/account/balance"
            headers = self._headers(path)
            status, resp, _ = self._request("GET", path, headers=headers)
            if status == 200:
                data = resp.get("data", resp) if isinstance(resp, dict) else resp
                if isinstance(data, list):
                    for item in data:
                        asset = item.get("currency", item.get("asset", ""))
                        if asset == "USDT":
                            if self.market_type == "swap":
                                return {"USDT": float(item.get("availableBalance", item.get("positionMargin", 0)))}
                            return {"USDT": float(item.get("free", item.get("available", 0)))}
                return {"USDT": 0.0}
        except Exception:
            pass
        return {"USDT": 0.0}

    def get_positions(self, symbol: str = "") -> list:
        try:
            if self.market_type == "swap":
                path = "/api/v1/private/position/all"
            else:
                path = "/api/v3/account/positions"
            headers = self._headers(path)
            status, resp, _ = self._request("GET", path, headers=headers)
            if status == 200:
                data = resp.get("data", resp) if isinstance(resp, dict) else resp
                if isinstance(data, list):
                    if symbol:
                        return [p for p in data if to_mexc_swap_symbol(symbol) in str(p.get("contract_code", ""))]
                    return data
            return []
        except Exception:
            return []

    def open_long(self, symbol: str, quantity: float, price: Optional[float] = None) -> LiveOrderResult:
        return self._open_order(symbol, quantity, "buy", price)

    def open_short(self, symbol: str, quantity: float, price: Optional[float] = None) -> LiveOrderResult:
        return self._open_order(symbol, quantity, "sell", price)

    def _open_order(self, symbol: str, quantity: float, side: str, price: Optional[float] = None) -> LiveOrderResult:
        contract_code = to_mexc_swap_symbol(symbol) if self.market_type == "swap" else to_mexc_symbol(symbol)
        qty_str = self._dec_str(self._to_dec(quantity))

        try:
            inst_info = self._get_instrument_info(contract_code)
            if inst_info:
                min_qty = float(inst_info.get("min_quantity", inst_info.get("minVol", 0)))
                if quantity < min_qty:
                    qty_str = self._dec_str(self._to_dec(min_qty))

            if self.market_type == "swap":
                path = "/api/v1/private/order/create"
                
                side_map = {
                    "buy": 1,   # open long
                    "sell": 3,  # open short
                }
                order_side = side_map.get(side.lower(), 1)
                leverage = int(trading_config.get('leverage', 20)) if 'trading_config' in dir() else 20
                
                body = {
                    "symbol": contract_code,
                    "side": order_side,
                    "vol": qty_str,
                    "type": 5 if not price else 1,  # 5=market, 1=limit
                    "openType": 2,  # 2=cross margin
                    "leverage": leverage,
                    "positionMode": 2,  # 2=one-way mode
                    "externalOid": f"qd_{int(time.time() * 1000)}",
                }
                if price:
                    body["price"] = self._dec_str(self._to_dec(price))
            else:
                path = "/api/v3/order"
                body = {
                    "symbol": contract_code,
                    "side": side.upper(),
                    "type": "LIMIT" if price else "MARKET",
                    "quantity": qty_str,
                    "newClientOrderId": f"qd_{int(time.time() * 1000)}",
                }
                if price:
                    body["price"] = self._dec_str(self._to_dec(price))
                    body["timeInForce"] = "GTC"

            body_json = json.dumps(body)
            timestamp = str(int(time.time() * 1000))

            logger.info(f"MEXC order: path={path}, body={body_json}")
            headers = self._generate_signature_with_body(timestamp, body_json)
            status, resp, raw = self._request("POST", path, json_body=body, headers=headers)
            logger.info(f"MEXC order response: status={status}, resp={resp}")

            if status == 200:
                order_data = resp.get("data", resp) if isinstance(resp, dict) else {}
                order_id = str(
                    order_data.get("order_id") 
                    or order_data.get("orderId")
                    or order_data.get("clientOrderId")
                    or order_data.get("id")
                    or order_data.get("data", {}).get("order_id", "")
                    if isinstance(order_data.get("data"), dict) else ""
                )
                logger.info(f"MEXC order_id parsed: {order_id}")
                return LiveOrderResult(
                    exchange_id="mexc",
                    exchange_order_id=order_id,
                    filled=float(order_data.get("filled_qty", order_data.get("deal_volume", 0))),
                    avg_price=float(order_data.get("avg_price", order_data.get("price", price or 0))),
                    raw=order_data,
                )
            raise LiveTradingError(f"MEXC open order failed: {resp}")
        except LiveTradingError:
            raise
        except Exception as e:
            logger.error(f"MEXC order error: {e}")
            raise LiveTradingError(f"MEXC open order error: {e}")

    def close_long(self, symbol: str, quantity: float, price: Optional[float] = None) -> LiveOrderResult:
        return self._close_order(symbol, quantity, "sell", price)

    def close_short(self, symbol: str, quantity: float, price: Optional[float] = None) -> LiveOrderResult:
        return self._close_order(symbol, quantity, "buy", price)

    def _close_order(self, symbol: str, quantity: float, side: str, price: Optional[float] = None) -> LiveOrderResult:
        contract_code = to_mexc_swap_symbol(symbol) if self.market_type == "swap" else to_mexc_symbol(symbol)
        qty_str = self._dec_str(self._to_dec(quantity))

        try:
            if self.market_type == "swap":
                path = "/api/v1/private/order/create"
                
                side_map = {
                    "buy": 2,   # close short
                    "sell": 4,  # close long
                }
                order_side = side_map.get(side.lower(), 4)
                
                body = {
                    "symbol": contract_code,
                    "side": order_side,
                    "vol": qty_str,
                    "type": 5 if not price else 1,  # 5=market, 1=limit
                    "openType": 2,  # 2=cross margin
                    "positionMode": 2,  # 2=one-way mode
                    "externalOid": f"qd_{int(time.time() * 1000)}",
                }
                if price:
                    body["price"] = self._dec_str(self._to_dec(price))
            else:
                path = "/api/v3/order"
                body = {
                    "symbol": contract_code,
                    "side": side.upper(),
                    "type": "LIMIT" if price else "MARKET",
                    "quantity": qty_str,
                    "newClientOrderId": f"qd_{int(time.time() * 1000)}",
                }
                if price:
                    body["price"] = self._dec_str(self._to_dec(price))
                    body["timeInForce"] = "GTC"

            headers = self._headers(path, json.dumps(body))
            status, resp, raw = self._request("POST", path, json_body=body, headers=headers)
            logger.info(f"MEXC close order response: status={status}, resp={resp}")

            if status == 200:
                order_data = resp.get("data", resp) if isinstance(resp, dict) else {}
                order_id = str(
                    order_data.get("order_id") 
                    or order_data.get("orderId")
                    or order_data.get("clientOrderId")
                    or order_data.get("id")
                    or order_data.get("data", {}).get("order_id", "")
                    if isinstance(order_data.get("data"), dict) else ""
                )
                logger.info(f"MEXC close order_id parsed: {order_id}")
                return LiveOrderResult(
                    exchange_id="mexc",
                    exchange_order_id=order_id,
                    filled=float(order_data.get("filled_qty", order_data.get("deal_volume", 0))),
                    avg_price=float(order_data.get("avg_price", order_data.get("price", price or 0))),
                    raw=order_data,
                )
            raise LiveTradingError(f"MEXC close order failed: {resp}")
        except LiveTradingError:
            raise
        except Exception as e:
            raise LiveTradingError(f"MEXC close order error: {e}")

    def cancel_order(self, symbol: str, order_id: str) -> bool:
        try:
            contract_code = to_mexc_swap_symbol(symbol) if self.market_type == "swap" else to_mexc_symbol(symbol)
            if self.market_type == "swap":
                path = "/api/v1/private/order/cancel"
                body = {"contract_code": contract_code, "order_id": order_id}
            else:
                path = f"/api/v3/order?symbol={contract_code}&orderId={order_id}"
                body = None
            headers = self._headers(path, json.dumps(body) if body else "")
            status, resp, _ = self._request("DELETE", path, json_body=body, headers=headers)
            return status == 200
        except Exception:
            return False

    def get_order(self, symbol: str, order_id: str) -> Optional[Dict[str, Any]]:
        try:
            contract_code = to_mexc_swap_symbol(symbol) if self.market_type == "swap" else to_mexc_symbol(symbol)
            if self.market_type == "swap":
                path = f"/api/v1/private/order/{order_id}?contract_code={contract_code}"
            else:
                path = f"/api/v3/order?symbol={contract_code}&orderId={order_id}"
            headers = self._headers(path)
            status, resp, _ = self._request("GET", path, headers=headers)
            if status == 200:
                return resp.get("data", resp) if isinstance(resp, dict) else resp
        except Exception:
            pass
        return None

    def get_fee_rate(self, symbol: str, market_type: str = "swap") -> Optional[Dict[str, float]]:
        try:
            contract_code = to_mexc_swap_symbol(symbol) if market_type == "swap" else to_mexc_symbol(symbol)
            if market_type == "swap":
                path = f"/api/v1/private/contract/{contract_code}"
            else:
                path = f"/api/v3/account/avgPrice?symbol={contract_code}"
            status, resp, _ = self._request("GET", path)
            if status == 200:
                return {"maker": 0.002, "taker": 0.002}
        except Exception:
            pass
        return {"maker": 0.002, "taker": 0.002}

    def ping(self) -> bool:
        try:
            if self.market_type == "swap":
                status, _, _ = self._request("GET", "/api/v1/contract/ping")
            else:
                status, _, _ = self._request("GET", "/api/v3/ping")
            return status == 200
        except Exception:
            return False