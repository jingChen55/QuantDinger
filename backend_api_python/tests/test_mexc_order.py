"""
MEXC 下单功能单元测试

测试 MexcClient 的下单功能，包括：
- open_long / open_short (开仓)
- close_long / close_short (平仓)
- 市价单 / 限价单

需要配置环境变量：
- MEXC_API_KEY
- MEXC_SECRET_KEY

运行方式：
    export MEXC_API_KEY="your_api_key"
    export MEXC_SECRET_KEY="your_secret_key"
    python3 -m pytest tests/test_mexc_order.py -v -s
"""
import unittest
import json
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_mexc_credentials():
    """从环境变量获取 MEXC API 密钥"""
    api_key = os.getenv("MEXC_API_KEY", "").strip()
    secret_key = os.getenv("MEXC_SECRET_KEY", "").strip()
    return api_key, secret_key


class TestMexcOrder(unittest.TestCase):
    """测试 MEXC 下单功能"""

    @classmethod
    def setUpClass(cls):
        """从环境变量获取凭证"""
        cls.api_key, cls.secret_key = get_mexc_credentials()
        if not cls.api_key or not cls.secret_key:
            raise unittest.SkipTest("MEXC_API_KEY 或 MEXC_SECRET_KEY 未配置")

    def setUp(self):
        """每个测试前创建新客户端"""
        from app.services.live_trading.mexc import MexcClient

        self.client = MexcClient(
            api_key=self.api_key,
            secret_key=self.secret_key,
            market_type="swap",
        )
        self.symbol = "BTC_USDT"

    def test_01_ping(self):
        """测试连接 MEXC API"""
        print(f"\n{'='*70}")
        print("测试 1: PING MEXC API")
        print(f"{'='*70}")

        result = self.client.ping()
        print(f"  ping result: {result}")

        self.assertTrue(result, "MEXC API 连接失败")
        print("  ✅ 连接成功")

    def test_02_get_balance(self):
        """测试获取账户余额"""
        print(f"\n{'='*70}")
        print("测试 2: 获取账户余额")
        print(f"{'='*70}")

        balance = self.client.get_balance()
        print(f"  balance: {balance}")

        self.assertIn("USDT", balance, "USDT 余额不存在")
        self.assertGreater(balance["USDT"], 0, "USDT 余额为 0")
        print(f"  ✅ USDT 余额: {balance['USDT']}")

    def test_03_get_positions(self):
        """测试获取持仓"""
        print(f"\n{'='*70}")
        print("测试 3: 获取持仓")
        print(f"{'='*70}")

        positions = self.client.get_positions()
        print(f"  positions count: {len(positions)}")
        for pos in positions[:3]:
            print(f"    {pos}")

        print(f"  ✅ 获取成功")

    def test_04_open_long_market(self):
        """测试市价开多单"""
        print(f"\n{'='*70}")
        print("测试 4: 市价开多单 (open_long)")
        print(f"{'='*70}")

        quantity = 0.001
        print(f"  symbol: {self.symbol}")
        print(f"  quantity: {quantity}")
        print(f"  type: market")

        try:
            result = self.client.open_long(self.symbol, quantity, price=None)
            print(f"\n  结果:")
            print(f"    exchange_order_id: {result.exchange_order_id}")
            print(f"    filled: {result.filled}")
            print(f"    avg_price: {result.avg_price}")
            print(f"    raw: {result.raw}")

            self.assertTrue(len(result.exchange_order_id) > 0, "order_id 不应为空")
            self.assertEqual(result.exchange_id, "mexc")
            print(f"\n  ✅ 市价开多成功！order_id: {result.exchange_order_id}")
        except Exception as e:
            print(f"\n  ❌ 市价开多失败: {e}")
            raise

    def test_05_open_short_market(self):
        """测试市价开空单"""
        print(f"\n{'='*70}")
        print("测试 5: 市价开空单 (open_short)")
        print(f"{'='*70}")

        quantity = 0.001
        print(f"  symbol: {self.symbol}")
        print(f"  quantity: {quantity}")
        print(f"  type: market")

        try:
            result = self.client.open_short(self.symbol, quantity, price=None)
            print(f"\n  结果:")
            print(f"    exchange_order_id: {result.exchange_order_id}")
            print(f"    filled: {result.filled}")
            print(f"    avg_price: {result.avg_price}")

            self.assertTrue(len(result.exchange_order_id) > 0, "order_id 不应为空")
            print(f"\n  ✅ 市价开空成功！order_id: {result.exchange_order_id}")
        except Exception as e:
            print(f"\n  ❌ 市价开空失败: {e}")
            raise

    def test_06_close_long_market(self):
        """测试市价平多单"""
        print(f"\n{'='*70}")
        print("测试 6: 市价平多单 (close_long)")
        print(f"{'='*70}")

        quantity = 0.001
        print(f"  symbol: {self.symbol}")
        print(f"  quantity: {quantity}")

        try:
            result = self.client.close_long(self.symbol, quantity, price=None)
            print(f"\n  结果:")
            print(f"    exchange_order_id: {result.exchange_order_id}")
            print(f"    filled: {result.filled}")

            self.assertTrue(len(result.exchange_order_id) > 0, "order_id 不应为空")
            print(f"\n  ✅ 市价平多成功！order_id: {result.exchange_order_id}")
        except Exception as e:
            print(f"\n  ❌ 市价平多失败: {e}")
            raise

    def test_07_close_short_market(self):
        """测试市价平空单"""
        print(f"\n{'='*70}")
        print("测试 7: 市价平空单 (close_short)")
        print(f"{'='*70}")

        quantity = 0.001
        print(f"  symbol: {self.symbol}")
        print(f"  quantity: {quantity}")

        try:
            result = self.client.close_short(self.symbol, quantity, price=None)
            print(f"\n  结果:")
            print(f"    exchange_order_id: {result.exchange_order_id}")
            print(f"    filled: {result.filled}")

            self.assertTrue(len(result.exchange_order_id) > 0, "order_id 不应为空")
            print(f"\n  ✅ 市价平空成功！order_id: {result.exchange_order_id}")
        except Exception as e:
            print(f"\n  ❌ 市价平空失败: {e}")
            raise

    def test_08_open_long_limit(self):
        """测试限价开多单"""
        print(f"\n{'='*70}")
        print("测试 8: 限价开多单 (open_long with price)")
        print(f"{'='*70}")

        quantity = 0.001
        price = 50000.0
        print(f"  symbol: {self.symbol}")
        print(f"  quantity: {quantity}")
        print(f"  price: {price}")

        try:
            result = self.client.open_long(self.symbol, quantity, price=price)
            print(f"\n  结果:")
            print(f"    exchange_order_id: {result.exchange_order_id}")
            print(f"    avg_price: {result.avg_price}")

            self.assertTrue(len(result.exchange_order_id) > 0, "order_id 不应为空")
            print(f"\n  ✅ 限价开多成功！order_id: {result.exchange_order_id}")
        except Exception as e:
            print(f"\n  ❌ 限价开多失败: {e}")
            raise

    def test_09_cancel_order(self):
        """测试取消订单"""
        print(f"\n{'='*70}")
        print("测试 9: 取消订单")
        print(f"{'='*70}")

        quantity = 0.001
        price = 60000.0
        print(f"  先下限价开多单...")
        print(f"  symbol: {self.symbol}")
        print(f"  quantity: {quantity}")
        print(f"  price: {price}")

        try:
            result = self.client.open_long(self.symbol, quantity, price=price)
            order_id = result.exchange_order_id
            print(f"  订单 ID: {order_id}")

            if order_id:
                print(f"\n  取消订单...")
                cancel_result = self.client.cancel_order(self.symbol, order_id)
                print(f"  取消结果: {cancel_result}")
                self.assertTrue(cancel_result, "取消订单失败")
                print(f"  ✅ 取消订单成功")
        except Exception as e:
            print(f"\n  ❌ 取消订单失败: {e}")
            raise

    def test_10_get_order(self):
        """测试查询订单"""
        print(f"\n{'='*70}")
        print("测试 10: 查询订单")
        print(f"{'='*70}")

        quantity = 0.001
        price = 45000.0
        print(f"  先下限价开多单...")
        print(f"  symbol: {self.symbol}")
        print(f"  quantity: {quantity}")
        print(f"  price: {price}")

        try:
            result = self.client.open_long(self.symbol, quantity, price=price)
            order_id = result.exchange_order_id
            print(f"  订单 ID: {order_id}")

            if order_id:
                print(f"\n  查询订单...")
                order_info = self.client.get_order(self.symbol, order_id)
                print(f"  订单信息: {json.dumps(order_info, indent=2, ensure_ascii=False)[:500]}")
                self.assertIsNotNone(order_info, "查询订单失败")
                print(f"  ✅ 查询订单成功")
        except Exception as e:
            print(f"\n  ❌ 查询订单失败: {e}")
            raise


def run_tests():
    """运行所有测试"""
    print("\n" + "="*70)
    print("🔬 MEXC 下单功能单元测试")
    print("="*70 + "\n")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestMexcOrder))

    runner = unittest.TextTestRunner(verbosity=0, resultclass=unittest.TextTestResult)
    result = runner.run(suite)

    print("\n" + "="*70)
    if result.wasSuccessful():
        print("🎉 所有 MEXC 下单测试通过！")
    else:
        print("❌ 测试失败")
        for test, traceback in result.failures:
            print(f"\n失败: {test}")
            print(traceback)
    print("="*70 + "\n")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)