import os

base = "/Users/k7/code/github.com/QuantDinger"

# 找到frontend目录
frontend_dir = None
for item in os.listdir(base):
    if 'frontend' in item.lower() and os.path.isdir(os.path.join(base, item)):
        frontend_dir = os.path.join(base, item)
        break

if not frontend_dir:
    print("No frontend directory found")
    exit()

webhook_config_path = os.path.join(frontend_dir, 'src', 'views', 'trading-bot', 'components', 'configs', 'WebhookConfig.vue')

if not os.path.exists(webhook_config_path):
    print(f"WebhookConfig file not found: {webhook_config_path}")
    exit()

with open(webhook_config_path, 'r', encoding='utf-8') as f:
    lines = f.read().split('\n')

print("=== 检查 WebhookConfig 的 props 和 data ===\n")
print("当前 props 声明（找到第 166-195 行）：")
for i in range(165, 200):
    if i < len(lines):
        print(f"{i+1:5d}: {lines[i]}")
