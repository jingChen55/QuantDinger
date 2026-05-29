"""
快速验证 MEXC 客户端下单功能

运行前设置环境变量：
    export MEXC_API_KEY="你的API密钥"
    export MEXC_SECRET_KEY="你的API秘钥"

测试内容：
1. ping - 连通性检查
2. 签名生成 - 验证签名算法是否正确
3. 获取余额 - 验证认证是否通过
4. 市价开多单 - 验证下单功能
"""

import os
import sys
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.live_trading.mexc import MexcClient


def main():
    api_key = os.getenv("MEXC_API_KEY", "").strip()
    secret_key = os.getenv("MEXC_SECRET_KEY", "").strip()

    if not api_key or not secret_key:
        print("❌ 缺少 MEXC_API_KEY 或 MEXC_SECRET_KEY 环境变量")
        print("   请运行:")
        print("   export MEXC_API_KEY='your_api_key'")
        print("   export MEXC_SECRET_KEY='your_secret_key'")
        return

    print("\n" + "=" * 70)
    print("🔍 MEXC 下单功能验证")
    print("=" * 70)
    print(f"  API Key: {api_key[:8]}...{api_key[-4:]}")
    print(f"  Secret: {secret_key[:4]}...{secret_key[-4:]}")
    print()

    # 测试永续合约
    client_swap = MexcClient(
        api_key=api_key,
        secret_key=secret_key,
        market_type="swap",
    )

    # ===== 测试 1: ping =====
    print("-" * 70)
    print("测试 1: PING API")
    try:
        result = client_swap.ping()
        print(f"  ping() = {result}")
        if result:
            print("  ✅ 连接成功")
        else:
            print("  ❌ 连接失败")
    except Exception as e:
        print(f"  ❌ 连接异常: {e}")

    # ===== 测试 2: 签名验证 =====
    print("\n" + "-" * 70)
    print("测试 2: 签名生成验证")
    try:
        timestamp = int(time.time() * 1000)
        body_json = '{"symbol":"BTC_USDT","side":1}'
        headers = client_swap._headers("/api/v1/private/order/create", body_json)

        print(f"  Timestamp: {timestamp}")
        print(f"  Headers: {json.dumps(headers, indent=4)}")

        # MEXC 永续正确的签名格式应该是:
        # message = HTTP_METHOD + "\n" + REQUEST_PATH + "\n" + TIMESTAMP + "\n" + BODY
        # 但代码实现的是: message = API_KEY + TIMESTAMP + BODY
        # 这里做一个简单检测
        sig = headers.get("Signature", "")
        print(f"  Signature (base64): {sig[:20]}...")

        if sig and len(sig) > 20:
            print("  ⚠️  签名已生成，但需验证算法是否与 MEXC 官方一致")
        print("  ℹ️  正确格式应为: HMAC_SHA256(secret, 'POST\\n/api/v1/private/order/create\\n{TIMESTAMP}\\n{BODY}')")
    except Exception as e:
        print(f"  ❌ 签名异常: {e}")

    # ===== 测试 3: 获取余额 =====
    print("\n" + "-" * 70)
    print("测试 3: 获取账户余额 (需签名认证)")
    try:
        balance = client_swap.get_balance()
        print(f"  get_balance() = {balance}")
        if balance.get("USDT", 0) > 0:
            print(f"  ✅ 认证成功，USDT 余额: {balance['USDT']}")
        else:
            print("  ⚠️  余额为 0 或认证失败（可能签名算法不匹配）")
    except Exception as e:
        print(f"  ❌ 获取余额异常: {e}")
        print("     这通常意味着签名验证失败")

    # ===== 测试 4: 获取持仓 =====
    print("\n" + "-" * 70)
    print("测试 4: 获取持仓")
    try:
        positions = client_swap.get_positions()
        print(f"  持仓数量: {len(positions)}")
        for pos in positions[:3]:
            print(f"    {pos}")
        print("  ✅ 获取成功")
    except Exception as e:
        print(f"  ❌ 获取持仓异常: {e}")

    # ===== 测试 5: 市价开多单 =====
    print("\n" + "-" * 70)
    print("测试 5: 市价开多单 (0.001 BTC/USDT)")
    try:
        result = client_swap.open_long("BTC_USDT", 0.001, price=None)
        print(f"  exchange_order_id: {result.exchange_order_id}")
        print(f"  filled: {result.filled}")
        print(f"  avg_price: {result.avg_price}")
        print(f"  raw: {result.raw}")

        if result.exchange_order_id:
            print(f"\n  ✅ 下单成功！order_id: {result.exchange_order_id}")
            order_id = result.exchange_order_id
        else:
            print("\n  ❌ 下单失败：order_id 为空")
            order_id = None
    except Exception as e:
        print(f"  ❌ 下单异常: {e}")
        order_id = None

    # ===== 测试 6: 平仓 =====
    if order_id:
        print("\n" + "-" * 70)
        print("测试 6: 市价平多单")
        try:
            time.sleep(1)  # 等待上一单成交
            result = client_swap.close_long("BTC_USDT", 0.001, price=None)
            print(f"  exchange_order_id: {result.exchange_order_id}")
            print(f"  filled: {result.filled}")
            if result.exchange_order_id:
                print(f"  ✅ 平仓成功！order_id: {result.exchange_order_id}")
            else:
                print("  ❌ 平仓失败：order_id 为空")
        except Exception as e:
            print(f"  ❌ 平仓异常: {e}")

    # ===== 测试 7: 现货交易 =====
    print("\n" + "-" * 70)
    print("测试 7: 现货市价开多 (0.01 BTC)")
    try:
        client_spot = MexcClient(
            api_key=api_key,
            secret_key=secret_key,
            market_type="spot",
        )
        result = client_spot.open_long("BTC_USDT", 0.01, price=None)
        print(f"  exchange_order_id: {result.exchange_order_id}")
        print(f"  raw: {result.raw}")
        if result.exchange_order_id:
            print(f"  ✅ 现货下单成功！order_id: {result.exchange_order_id}")
        else:
            print("  ⚠️  order_id 为空")
    except Exception as e:
        print(f"  ❌ 现货下单异常: {e}")

    print("\n" + "=" * 70)
    print("验证完成")
    print("=" * 70)


if __name__ == "__main__":
    main()