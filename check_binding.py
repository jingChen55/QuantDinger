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
    content = f.read()

print("=== 检查 Wizard 如何使用 configComponent ===\n")
lines = content.split('\n')
for i, line in enumerate(lines, 1):
    if 'configComponent' in line or 'strategyConfig' in line:
        start = max(0, i - 5)
        end = min(len(lines), i + 20)
        for j in range(start, end):
            print(f"{j+1:5d}: {lines[j]}")
        print("\n" + "="*80 + "\n")
