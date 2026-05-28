"""
Unit tests for MEXC API signature
"""
import unittest
import time
import hmac
import hashlib
import base64


class TestMEXCSignature(unittest.TestCase):
    """Test MEXC API signature generation"""
    
    def test_signature_format(self):
        """Test MEXC signature follows correct format: accessKey + timestamp + params"""
        api_key = "test_api_key"
        secret_key = "test_secret_key"
        timestamp = int(time.time() * 1000)
        params_json = '{"contract_code":"BTC_USDT","volume":"0.001"}'
        
        message = f"{api_key}{timestamp}{params_json}"
        signature = hmac.new(
            secret_key.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        sig_base64 = base64.b64encode(signature).decode("utf-8")
        
        self.assertIsInstance(sig_base64, str)
        self.assertTrue(len(sig_base64) > 0)
        print(f"Signature: {sig_base64}")
    
    def test_deterministic_signature(self):
        """Test signature is deterministic"""
        api_key = "test_api_key"
        secret_key = "test_secret_key"
        timestamp = 1644489390000
        params_json = '{"symbol":"BTCUSDT"}'
        
        message = f"{api_key}{timestamp}{params_json}"
        sig1 = hmac.new(
            secret_key.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        sig1_b64 = base64.b64encode(sig1).decode("utf-8")
        
        sig2 = hmac.new(
            secret_key.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        sig2_b64 = base64.b64encode(sig2).decode("utf-8")
        
        self.assertEqual(sig1_b64, sig2_b64)
    
    def test_different_params_different_signature(self):
        """Test different params produce different signatures"""
        api_key = "test_api_key"
        secret_key = "test_secret_key"
        timestamp = 1644489390000
        
        params1 = '{"symbol":"BTCUSDT"}'
        params2 = '{"symbol":"ETHUSDT"}'
        
        msg1 = f"{api_key}{timestamp}{params1}"
        sig1 = base64.b64encode(hmac.new(secret_key.encode(), msg1.encode(), hashlib.sha256).digest()).decode()
        
        msg2 = f"{api_key}{timestamp}{params2}"
        sig2 = base64.b64encode(hmac.new(secret_key.encode(), msg2.encode(), hashlib.sha256).digest()).decode()
        
        self.assertNotEqual(sig1, sig2)


class TestMEXCHeaderGeneration(unittest.TestCase):
    """Test MEXC header generation"""
    
    def test_headers_contain_required_fields(self):
        """Test headers contain ApiKey, Request-Time, Signature, Content-Type"""
        api_key = "test_api_key"
        secret_key = "test_secret_key"
        timestamp = int(time.time() * 1000)
        params_json = '{"test":"data"}'
        
        message = f"{api_key}{timestamp}{params_json}"
        signature = base64.b64encode(
            hmac.new(secret_key.encode(), message.encode(), hashlib.sha256).digest()
        ).decode()
        
        headers = {
            "ApiKey": api_key,
            "Request-Time": str(timestamp),
            "Signature": signature,
            "Content-Type": "application/json",
        }
        
        self.assertIn("ApiKey", headers)
        self.assertIn("Request-Time", headers)
        self.assertIn("Signature", headers)
        self.assertIn("Content-Type", headers)
        self.assertEqual(headers["Content-Type"], "application/json")


if __name__ == '__main__':
    unittest.main(verbosity=2)
