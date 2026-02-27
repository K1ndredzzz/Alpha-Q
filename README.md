# Alpha-Q

**Alpha-Q Fundamental Quant Dashboard** 是一个极客风格的量化分析与异动预警平台，专门用于从历史财务报表与基于 LLM 提取的财报非结构化（NLP）信号中发掘投资洞察。

## ✨ 核心特性

- 📈 **M1 数据透视板 (Hard Numbers)**: 快速计算并可视化 Piotroski F-Score (财务健康度) 与 Altman Z-Score (破产风险)，并提供 DuPont ROE 杜邦分析拆解。
- 📊 **M2 异动时间轴 (Soft Tone)**: 基于文本分析的瀑布流，揭示财报中高管的情绪变化 (Sentiment Score)、宏观担忧 (Macro Concerns) 演变以及 CapEx 语气的突变。
- 🚩 **M3 交叉验证红旗 (The Red Flag Matrix)**: 将硬性财务恶化与软性文本警告（如流动性危机、管理层负面情绪等）交叉验证，生成 5 级严重性的风险预警卡片。

## 🏗️ 系统架构

本项目采用 **双阶段架构 (Two-Phase Architecture)** 设计，以确保完全脱机并降低云端 API 依赖：

1. **Phase 1 (Offline DB Fusion)**: 本地 Python 脚本 (`scripts/`) 使用 `yfinance` 抓取过去 18 年的财务数据，并将其与本地存储的 NLP 数据集 (`data/insights.jsonl`) 进行 INNER JOIN 合并，输出一个极度干净的只读 SQLite 数据库。
2. **Phase 2 (Dockerized Dashboard)**: 采用纯净的脱机上云模式，通过 Docker Compose 部署两个微服务：
   - **Backend**: 基于 FastAPI 和 SQLAlchemy 的无状态 RESTful API (Port: 8041)
   - **Frontend**: 基于 Streamlit 与 Plotly 的暗黑主题交互式仪表盘 (Port: 8040)

## 🚀 快速开始 (本地运行)

### 前置条件
- Docker & Docker Compose
- Python 3.11+ (如需本地生成数据)

### 部署与启动

1. **克隆项目**
   ```bash
   git clone https://github.com/K1ndredzzz/Alpha-Q.git
   cd Alpha-Q
   ```

2. **一键构建镜像**
   执行构建脚本生成前端与后端镜像：
   ```bash
   ./build.sh
   ```

3. **启动容器服务**
   ```bash
   docker-compose up -d
   ```

4. **访问平台**
   打开浏览器访问: [http://localhost:8040](http://localhost:8040)

## 📁 目录结构

```text
Alpha-Q/
├── backend/                  # FastAPI 后端源码及 Dockerfile
├── frontend/                 # Streamlit 前端源码及 Dockerfile
├── scripts/                  # 数据采集、合并与 Mock 脚本
├── data/                     # (需生成) SQLite 数据库文件存放处
├── stocks.toml               # Ticker 层级与财年配置文件
├── docker-compose.yml        # Docker 编排配置
├── build.sh                  # 镜像构建与推送脚本
├── DEPLOYMENT.md             # 生产环境 (1Panel/OpenResty) 部署指南
└── Alpha-Q Fundamental Quant Dashboard.md  # 系统设计提示词总纲
```

## ⚠️ 注意事项
- 项目依赖本地预处理好的数据卷 (`data/alpha_q_master.db`)。如果你没有数据，可参考代码中的 `scripts/01_mock_financials.py` 生成基于现有 NLP insights 文件的测试集。
- 完整的生产环境部署配置 (Nginx 反向代理、HTTPS) 请参阅 [`DEPLOYMENT.md`](./DEPLOYMENT.md)。

---
*Built as a Killer Portfolio Project for Quantitative Research / Full-Stack Data Analysis.*
