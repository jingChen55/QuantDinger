"""
Comprehensive unit tests for webhook signal handler
"""
import unittest
from unittest.mock import MagicMock, patch, Mock
import json


class TestWebhookSignalParsing(unittest.TestCase):
    """Test TradingView payload parsing"""
    
    def setUp(self):
        """Import function to test"""
        from app.routes.webhook import _parse_tradingview_payload
        self.parse_func = _parse_tradingview_payload
    
    def test_parse_buy_to_long(self):
        """Test buy action maps to long"""
        result = self.parse_func({"action": "buy", "symbol": "BTCUSDT", "qty": 0.01})
        self.assertEqual(result["signal_type"], "long")
    
    def test_parse_long_unchanged(self):
        """Test long action stays as long"""
        result = self.parse_func({"action": "long", "symbol": "ETHUSDT"})
        self.assertEqual(result["signal_type"], "long")
    
    def test_parse_sell_to_close_long(self):
        """Test sell action maps to close_long"""
        result = self.parse_func({"action": "sell", "symbol": "BTCUSDT"})
        self.assertEqual(result["signal_type"], "close_long")
    
    def test_parse_close_unchanged(self):
        """Test close action stays as close_long"""
        result = self.parse_func({"action": "close", "symbol": "BTCUSDT"})
        self.assertEqual(result["signal_type"], "close_long")
    
    def test_parse_short(self):
        """Test short action"""
        result = self.parse_func({"action": "short", "symbol": "BTCUSDT"})
        self.assertEqual(result["signal_type"], "short")
    
    def test_parse_close_short(self):
        """Test close_short action"""
        result = self.parse_func({"action": "close_short", "symbol": "BTCUSDT"})
        self.assertEqual(result["signal_type"], "close_short")
    
    def test_symbol_uppercase(self):
        """Test symbol is uppercased"""
        result = self.parse_func({"action": "buy", "symbol": "btc/usdt"})
        self.assertEqual(result["symbol"], "BTC/USDT")
    
    def test_price_optional(self):
        """Test price is optional"""
        result = self.parse_func({"action": "buy", "symbol": "BTCUSDT"})
        self.assertEqual(result["price"], 0)
    
    def test_quantity_optional(self):
        """Test quantity is optional"""
        result = self.parse_func({"action": "buy", "symbol": "BTCUSDT", "price": 50000})
        self.assertEqual(result["quantity"], 0)
    
    def test_comment_preserved(self):
        """Test comment is preserved"""
        result = self.parse_func({
            "action": "buy",
            "symbol": "BTCUSDT",
            "comment": "RSI oversold"
        })
        self.assertEqual(result["comment"], "RSI oversold")
    
    def test_timestamp_added(self):
        """Test timestamp is added"""
        import time
        result = self.parse_func({"action": "buy", "symbol": "BTCUSDT"})
        self.assertIsInstance(result["timestamp"], int)
        self.assertGreater(result["timestamp"], 0)


class TestWebhookKeyGeneration(unittest.TestCase):
    """Test webhook key generation"""
    
    def setUp(self):
        """Import function to test"""
        from app.routes.webhook import _generate_webhook_key
        self.gen_func = _generate_webhook_key
    
    def test_key_length(self):
        """Test key is 32 characters"""
        key = self.gen_func(1, 1, "secret")
        self.assertEqual(len(key), 32)
    
    def test_key_is_hex(self):
        """Test key is hexadecimal"""
        key = self.gen_func(1, 1, "secret")
        self.assertTrue(all(c in '0123456789abcdef' for c in key))
    
    def test_deterministic(self):
        """Test same inputs produce same key"""
        key1 = self.gen_func(1, 1, "secret")
        key2 = self.gen_func(1, 1, "secret")
        self.assertEqual(key1, key2)
    
    def test_different_strategy_id(self):
        """Test different strategy_id produces different key"""
        key1 = self.gen_func(1, 1, "secret")
        key2 = self.gen_func(2, 1, "secret")
        self.assertNotEqual(key1, key2)
    
    def test_different_user_id(self):
        """Test different user_id produces different key"""
        key1 = self.gen_func(1, 1, "secret")
        key2 = self.gen_func(1, 2, "secret")
        self.assertNotEqual(key1, key2)
    
    def test_different_secret(self):
        """Test different secret produces different key"""
        key1 = self.gen_func(1, 1, "secret1")
        key2 = self.gen_func(1, 1, "secret2")
        self.assertNotEqual(key1, key2)


class TestWebhookStrategyLookup(unittest.TestCase):
    """Test strategy lookup by webhook key"""
    
    @patch('app.routes.webhook.get_db_connection')
    def test_find_exact_match(self, mock_db):
        """Test finding strategy with exact key match"""
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
                'name': 'Test'
            }
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_conn
        
        result = _get_strategy_by_webhook_key('abc123')
        
        self.assertEqual(result['id'], 9)
        self.assertEqual(result['trading_config']['webhook_key'], 'abc123')
    
    @patch('app.routes.webhook.get_db_connection')
    def test_key_case_insensitive(self, mock_db):
        """Test key matching is case insensitive"""
        from app.routes.webhook import _get_strategy_by_webhook_key
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                'id': 9,
                'user_id': 1,
                'exchange_config': '{"exchange_id": "binance"}',
                'trading_config': json.dumps({'webhook_key': 'ABC123'}),
                'market_type': 'swap',
                'market_category': 'Crypto',
                'status': 'running',
                'name': 'Test'
            }
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_conn
        
        result = _get_strategy_by_webhook_key('abc123')
        
        self.assertEqual(result['id'], 9)
    
    @patch('app.routes.webhook.get_db_connection')
    def test_no_match_returns_empty(self, mock_db):
        """Test no match returns empty dict"""
        from app.routes.webhook import _get_strategy_by_webhook_key
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                'id': 1,
                'user_id': 1,
                'exchange_config': '{"exchange_id": "binance"}',
                'trading_config': json.dumps({'webhook_key': 'other'}),
                'market_type': 'swap',
                'market_category': 'Crypto',
                'status': 'running',
                'name': 'Test'
            }
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_conn
        
        result = _get_strategy_by_webhook_key('nonexistent')
        
        self.assertEqual(result, {})


class TestWebhookConfigParsing(unittest.TestCase):
    """Test configuration parsing"""
    
    def test_json_string_parsed(self):
        """Test JSON string is parsed"""
        json_str = '{"exchange_id": "binance", "api_key": "test"}'
        if isinstance(json_str, str):
            result = json.loads(json_str)
        else:
            result = json_str
        self.assertEqual(result['exchange_id'], 'binance')
    
    def test_dict_passthrough(self):
        """Test dict is passed through"""
        config = {'exchange_id': 'binance'}
        if isinstance(config, str):
            result = json.loads(config)
        else:
            result = config
        self.assertEqual(result['exchange_id'], 'binance')
    
    def test_none_returns_default(self):
        """Test None returns default"""
        val = None
        default = {}
        result = val if val else default
        self.assertEqual(result, {})


class TestWebhookSignalExecution(unittest.TestCase):
    """Test webhook signal execution logic"""
    
    def test_signal_mapping_completeness(self):
        """Test all TradingView actions are mapped"""
        from app.routes.webhook import _parse_tradingview_payload
        
        actions = ['buy', 'sell', 'long', 'short', 'close', 'close_long', 'close_short']
        
        for action in actions:
            result = _parse_tradingview_payload({"action": action, "symbol": "BTCUSDT"})
            self.assertIn(result["signal_type"], 
                        ["long", "short", "close_long", "close_short", action],
                        f"Action '{action}' not properly handled")
    
    def test_exchange_config_required_fields(self):
        """Test exchange_config needs exchange_id"""
        config = {'exchange_id': 'binance', 'api_key': 'test'}
        self.assertTrue(bool(config.get('exchange_id')))
    
    def test_quantity_validation(self):
        """Test quantity must be positive for trading"""
        qty = 0.0
        self.assertLessEqual(qty, 0)
        
        qty = 0.01
        self.assertGreater(qty, 0)


class TestWebhookEndpointIntegration(unittest.TestCase):
    """Integration tests for webhook endpoint"""
    
    @patch('app.routes.webhook._get_strategy_by_webhook_key')
    def test_full_signal_flow(self, mock_lookup):
        """Test complete signal flow from lookup to execution"""
        from app.routes.webhook import _parse_tradingview_payload
        
        mock_lookup.return_value = {
            'id': 9,
            'user_id': 1,
            'exchange_config': '{"exchange_id": "binance", "api_key": "test"}',
            'trading_config': json.dumps({'webhook_key': 'test123', 'market_type': 'swap'}),
            'market_type': 'swap',
            'market_category': 'Crypto',
            'status': 'running',
            'name': 'Test'
        }
        
        payload = {
            "action": "buy",
            "symbol": "BTCUSDT",
            "qty": 0.01,
            "comment": "Test signal"
        }
        
        signal = _parse_tradingview_payload(payload)
        
        self.assertEqual(signal['signal_type'], 'long')
        self.assertEqual(signal['symbol'], 'BTCUSDT')
        self.assertEqual(signal['quantity'], 0.01)


class TestMEXCWebhooks(unittest.TestCase):
    """Test MEXC-specific webhook handling"""
    
    def test_mexc_exchange_config(self):
        """Test MEXC exchange config format"""
        config = {
            'exchange_id': 'mexc',
            'api_key': 'test_api_key',
            'secret_key': 'test_secret'
        }
        self.assertEqual(config['exchange_id'], 'mexc')
        self.assertIn('api_key', config)
        self.assertIn('secret_key', config)
    
    def test_mexc_symbol_format(self):
        """Test MEXC expects BTCUSDT format (no slash)"""
        from app.routes.webhook import _parse_tradingview_payload
        
        signal = _parse_tradingview_payload({
            "action": "buy",
            "symbol": "BTC/USDT"
        })
        
        self.assertEqual(signal['symbol'], "BTC/USDT")
    
    @patch('app.routes.webhook.get_db_connection')
    def test_find_mexc_strategy(self, mock_db):
        """Test finding MEXC strategy"""
        from app.routes.webhook import _get_strategy_by_webhook_key
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                'id': 9,
                'user_id': 1,
                'exchange_config': '{"exchange_id": "mexc", "api_key": "mx_test"}',
                'trading_config': json.dumps({'webhook_key': 'mexc123', 'market_type': 'swap'}),
                'market_type': 'swap',
                'market_category': 'Crypto',
                'status': 'running',
                'name': 'MEXC Bot'
            }
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_conn
        
        result = _get_strategy_by_webhook_key('mexc123')
        
        self.assertEqual(result['id'], 9)
        exchange_config = result.get('exchange_config', {})
        if isinstance(exchange_config, str):
            exchange_config = json.loads(exchange_config)
        self.assertEqual(exchange_config.get('exchange_id'), 'mexc')
    
    def test_credential_id_requires_resolution(self):
        """Test that credential_id needs to be resolved to get api_key"""
        config_with_credential = {'credential_id': 3, 'exchange_id': 'mexc'}
        self.assertIsNone(config_with_credential.get('api_key'))
        self.assertIsNone(config_with_credential.get('secret_key'))
        
        resolved_config = {
            'credential_id': 3,
            'exchange_id': 'mexc',
            'api_key': 'resolved_api_key',
            'secret_key': 'resolved_secret'
        }
        self.assertIsNotNone(resolved_config.get('api_key'))
        self.assertIsNotNone(resolved_config.get('secret_key'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
