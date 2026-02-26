# Alpha-Q 1Panel 部署指南

## 前置条件

- 1Panel 已安装并运行
- Docker 和 Docker Compose 已配置
- OpenResty (Nginx) 已通过 1Panel 安装
- 已登录 Docker Hub：`docker login`

---

## 一、构建并推送镜像

在项目根目录执行：

```bash
./build.sh
```

可选参数：
- `--no-cache` — 强制重新构建所有层
- `--backend-only` — 仅构建后端
- `--frontend-only` — 仅构建前端

构建完成后，镜像将推送至 Docker Hub：
- `fuzhouxing/alpha-q-backend:latest`
- `fuzhouxing/alpha-q-frontend:latest`

---

## 二、准备数据库文件

确保 `data/alpha_q_master.db` 存在于项目根目录。如果尚未生成，先运行数据脚本：

```bash
cd scripts
python 01_fetch_yfinance_and_calc.py
python 02_merge_to_master.py
```

生成的 `data/alpha_q_master.db` 将被 docker-compose 挂载为只读卷。

---

## 三、启动服务

在项目根目录执行：

```bash
docker-compose up -d
```

验证服务状态：

```bash
docker-compose ps
docker-compose logs -f
```

健康检查：
- 后端：`curl http://localhost:8041/api/v1/tickers`
- 前端：`curl http://localhost:8040/_stcore/health`

---

## 四、1Panel OpenResty 反向代理配置

### 4.1 创建网站

1. 登录 1Panel 控制面板
2. 导航至 **网站** → **创建网站**
3. 配置：
   - **域名**：`alpha-q.yourdomain.com`（或使用 IP 直接访问）
   - **类型**：反向代理
   - **代理地址**：`http://127.0.0.1:8040`

### 4.2 高级配置（可选）

如果需要同时暴露前端和后端 API，可配置路径路由：

进入网站 → **配置文件** → 编辑 Nginx 配置，添加：

```nginx
server {
    listen 80;
    server_name alpha-q.yourdomain.com;

    # 前端 (Streamlit)
    location / {
        proxy_pass http://127.0.0.1:8040;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    # 后端 API (FastAPI)
    location /api/ {
        proxy_pass http://127.0.0.1:8041/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**注意**：
- Streamlit 需要 WebSocket 支持（`Upgrade` 和 `Connection` 头）
- `proxy_read_timeout 86400` 防止长时间连接超时

### 4.3 HTTPS 配置（推荐）

1. 在 1Panel 网站设置中启用 **SSL**
2. 选择 **Let's Encrypt** 自动申请证书
3. 强制 HTTPS 重定向

---

## 五、服务管理

### 停止服务
```bash
docker-compose down
```

### 重启服务
```bash
docker-compose restart
```

### 查看日志
```bash
docker-compose logs -f alpha-q-backend
docker-compose logs -f alpha-q-frontend
```

### 更新镜像
```bash
docker-compose pull
docker-compose up -d
```

---

## 六、故障排查

### 前端无法连接后端

检查 Docker 网络：
```bash
docker network inspect alpha_q_net
```

确认两个容器在同一网络，且后端容器名为 `alpha-q-backend`。

### 数据库文件权限错误

确保 `data/alpha_q_master.db` 可读：
```bash
chmod 644 data/alpha_q_master.db
```

### 端口冲突

如果 8040 或 8041 已被占用，修改 `docker-compose.yml` 中的端口映射：
```yaml
ports:
  - "8042:8000"  # 改为其他端口
```

同时更新 OpenResty 配置中的 `proxy_pass` 地址。

---

## 七、生产环境建议

1. **数据库备份**：定期备份 `data/alpha_q_master.db`
2. **日志轮转**：配置 Docker 日志驱动限制日志大小
3. **监控**：使用 1Panel 内置监控或 Prometheus + Grafana
4. **防火墙**：仅开放 80/443 端口，8040/8041 仅限内网访问
5. **定期更新**：定期重新运行 `scripts/01_*.py` 和 `02_*.py` 更新数据

---

## 附录：完整架构图

```
Internet
   ↓
OpenResty (1Panel) :80/:443
   ↓
   ├─→ / → Streamlit Frontend :8040 (容器内 :8501)
   └─→ /api/ → FastAPI Backend :8041 (容器内 :8000)
                    ↓
              alpha_q_master.db (只读挂载)
```

---

**部署完成后访问**：`http://alpha-q.yourdomain.com` 或 `http://your-server-ip`
