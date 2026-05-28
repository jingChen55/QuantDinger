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
    lines = content.split('\n')

print("=== 检查 nextStep 和 handleSubmit 方法 ===\n")
for i, line in enumerate(lines, 1):
    if 'nextStep' in line or 'handleSubmit' in line or 'handleCreate' in line or 'validate' in line:
        start = max(0, i - 2)
        end = min(len(lines), i + 50)
        for j in range(start, end):
            print(f"{j+1:5d}: {lines[j]}")
        print("\n" + "="*80 + "\n")
