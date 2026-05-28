## podman 部署

```bash

cd ~/quantdinger

# 1. 准备环境文件
cp backend_api_python/env.example backend_api_python/.env

# 2. 生成密钥（如果还没做过）
./scripts/generate-secret-key.sh

# 3. 使用预构建镜像（从 GHCR 拉取）
podman compose -f docker-compose.ghcr.yml pull

# 4. 启动
podman compose -f docker-compose.ghcr.yml up -d
```