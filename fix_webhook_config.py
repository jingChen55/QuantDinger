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
    # 列出目录内容
    configs_dir = os.path.join(frontend_dir, 'src', 'views', 'trading-bot', 'components', 'configs')
    if os.path.exists(configs_dir):
        print(f"Contents of {configs_dir}:")
        for item in os.listdir(configs_dir):
            print(f"  {item}")
    exit()

print(f"Found WebhookConfig at: {webhook_config_path}")
print(f"File exists: {os.path.exists(webhook_config_path)}")
