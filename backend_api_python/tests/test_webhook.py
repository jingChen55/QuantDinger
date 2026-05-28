"""
Unit tests for webhook signal handler
"""
import unittest
from unittest.mock import MagicMock, patch
import json


class TestWebhookParsing(unittest.TestCase):
    """Test TradingView payload parsing"""
    
    def test_parse_buy_signal(self):
        """Test parsing buy action"""
        from app.routes.webhook import _parse_tradingview_payload
        
        payload = {
            "action": "buy",
            "symbol": "BTCUSDT",
            "qty": 0.01,
            "comment": "RSI oversold"
        }
        
        result = _parse_tradingview_payload(payload)
        
        self.assertEqual(result["signal_type"], "long")
        self.assertEqual(result["symbol"], "BTCUSDT")
        self.assertEqual(result["quantity"], 0.01)
        self.assertEqual(result["comment"], "RSI oversold")
    
    def test_parse_sell_signal(self):
        """Test parsing sell action"""
        from app.routes.webhook import _parse_tradingview_payload
        
        payload = {
            "action": "sell",
            "symbol": "ETHUSDT",
            "qty": 1.5
        }
        
        result = _parse_tradingview_payload(payload)
        
        self.assertEqual(result["signal_type"], "close_long")
        self.assertEqual(result["symbol"], "ETHUSDT")
    
    def test_parse_short_signal(self):
        """Test parsing short action"""
        from app.routes.webhook import _parse_tradingview_payload
        
        payload = {
            "action": "short",
            "symbol": "SOLUSDT",
            "qty": 10.0
        }
        
        result = _parse_tradingview_payload(payload)
        
        self.assertEqual(result["signal_type"], "short")
    
    def test_parse_close_short_signal(self):
        """Test parsing close_short action"""
        from app.routes.webhook import _parse_tradingview_payload
        
        payload = {
            "action": "close_short",
            "symbol": "DOGEUSDT"
        }
        
        result = _parse_tradingview_payload(payload)
        
        self.assertEqual(result["signal_type"], "close_short")
    
    def test_parse_with_price(self):
        """Test parsing with limit price"""
        from app.routes.webhook import _parse_tradingview_payload
        
        payload = {
            "action": "buy",
            "symbol": "BTCUSDT",
            "qty": 0.1,
            "price": 50000.0
        }
        
        result = _parse_tradingview_payload(payload)
        
        self.assertEqual(result["price"], 50000.0)
        self.assertEqual(result["signal_type"], "long")


class TestWebhookKeyGeneration(unittest.TestCase):
    """Test webhook key generation"""
    
    def test_generate_key_format(self):
        """Test key is 32 chars"""
        from app.routes.webhook import _generate_webhook_key
        
        key = _generate_webhook_key(1, 1, "test-secret")
        
        self.assertEqual(len(key), 32)
        self.assertTrue(key.isalnum())
    
    def test_same_inputs_same_key(self):
        """Test deterministic generation"""
        from app.routes.webhook import _generate_webhook_key
        
        key1 = _generate_webhook_key(1, 1, "secret")
        key2 = _generate_webhook_key(1, 1, "secret")
        
        self.assertEqual(key1, key2)
    
    def test_different_inputs_different_key(self):
        """Test different inputs produce different keys"""
        from app.routes.webhook import _generate_webhook_key
        
        key1 = _generate_webhook_key(1, 1, "secret1")
        key2 = _generate_webhook_key(1, 1, "secret2")
        
        self.assertNotEqual(key1, key2)


class TestWebhookSignalLookup(unittest.TestCase):
    """Test webhook strategy lookup"""
    
    @patch('app.routes.webhook.get_db_connection')
    def test_find_strategy_by_key(self, mock_db):
        """Test finding strategy by webhook key"""
        from app.routes.webhook import _get_strategy_by_webhook_key
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                'id': 9,
                'user_id': 1,
                'exchange_config': '{"exchange_id": "binance"}',
                'trading_config': json.dumps({'webhook_key': 'abc123', 'symbol': 'BTCUSDT'}),
                'market_type': 'swap',
                'market_category': 'Crypto',
                'status': 'running',
                'name': 'Test Strategy'
            }
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_conn
        
        result = _get_strategy_by_webhook_key('abc123')
        
        self.assertEqual(result['id'], 9)
        self.assertEqual(result['status'], 'running')
        trading_config = result['trading_config']
        self.assertEqual(trading_config['webhook_key'], 'abc123')
    
    @patch('app.routes.webhook.get_db_connection')
    def test_key_not_found(self, mock_db):
        """Test returns empty dict when key not found"""
        from app.routes.webhook import _get_strategy_by_webhook_key
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                'id': 1,
                'trading_config': json.dumps({'webhook_key': 'other_key'}),
                'exchange_config': '{}',
                'market_type': 'swap',
                'market_category': 'Crypto',
                'status': 'running',
                'name': 'Other'
            }
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_conn
        
        result = _get_strategy_by_webhook_key('nonexistent_key')
        
        self.assertEqual(result, {})


class TestWebhookExchangeConfig(unittest.TestCase):
    """Test exchange config parsing"""
    
    def test_to_dict_with_string(self):
        """Test parsing JSON string"""
        json_str = '{"exchange_id": "binance", "api_key": "test123"}'
        
        if isinstance(json_str, str):
            result = json.loads(json_str)
        else:
            result = json_str
        
        self.assertEqual(result['exchange_id'], 'binance')
        self.assertEqual(result['api_key'], 'test123')
    
    def test_to_dict_with_dict(self):
        """Test dict passthrough"""
        config = {'exchange_id': 'bybit', 'secret_key': 'secret123'}
        
        if isinstance(config, str):
            result = json.loads(config)
        else:
            result = config
        
        self.assertEqual(result['exchange_id'], 'bybit')


if __name__ == '__main__':
    unittest.main()
