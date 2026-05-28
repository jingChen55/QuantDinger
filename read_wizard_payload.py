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

wizard_path = os.path.join(frontend_dir, 'src', 'views', 'trading-bot', 'components', 'BotCreateWizard.vue')

if not os.path.exists(wizard_path):
    print(f"Wizard file not found: {wizard_path}")
    exit()

with open(wizard_path, 'r', encoding='utf-8') as f:
    lines = f.read().split('\n')

print("=== buildWebhookPayload 方法（找到第1386-1500行）===\n")
for i in range(1385, min(1500, len(lines))):
    print(f"{i+1:5d}: {lines[i]}")
