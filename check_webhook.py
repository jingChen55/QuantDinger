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

print("=== 检查 WebhookConfig 的 props 和 v-model ===\n")
for i, line in enumerate(lines, 1):
    if 'props:' in line or 'model:' in line or 'v-model' in line or 'emit' in line:
        start = max(0, i - 2)
        end = min(len(lines), i + 20)
        for j in range(start, end):
            print(f"{j+1:5d}: {lines[j]}")
        print("\n" + "="*80 + "\n")
