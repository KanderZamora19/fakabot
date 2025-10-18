# 🤖 Fakabot - 专业的 Telegram 自动发卡机器人

[![License](https://img.shields.io/badge/license-Commercial-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)]()
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://t.me/sonhshu)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)]()

<div align="center">

### 🚀 专业的 Telegram 自动发卡机器人

**全自动发卡系统** | 支持多种支付方式 | 订单自动处理 | Redis 高性能缓存

💳 支付宝 | 💳 微信 | 💰 USDT | 🚀 Docker 一键部署

</div>

**适用场景**：知识付费 · 虚拟商品 · 在线课程 · 软件授权 · 会员订阅

---

## 🎬 在线演示

**体验演示机器人**：[@fakawan_bot](https://t.me/fakawan_bot)

> 💡 演示机器人展示完整功能，但需要授权码才能实际使用。

---

## ⚠️ 重要说明

本项目需要**授权码**才能运行。代码已内置授权验证系统，无法绕过。

- ✅ 授权码采用签名验证，无法伪造
- ✅ 到期前7天自动提醒
- ✅ 到期后自动停止运行
- ✅ 支持远程续费，无需重新部署

---

## 💰 订阅价格

| 套餐 | 价格 | 优惠 |
|------|------|------|
| 月付 | 50 USDT/月 | - |
| 季付 | 135 USDT/季 | 10% |
| 年付 | 510 USDT/年 | 15% |

---

## 🚀 快速部署

### 🐳 方式一：Docker 一键部署（推荐）⭐

**最简单的部署方式，5分钟搞定！**

#### 前提条件

- 已安装 Docker 和 Docker Compose
- 已购买授权码

#### 一键部署命令

```bash
# 1. 克隆项目
git clone https://github.com/GUGEGEBAIDU/fakabot.git
cd fakabot

# 2. 复制配置文件
cp config.json.example config.json

# 3. 编辑配置（填写 Bot Token、管理员 ID 等）
vim config.json

# 4. 保存授权码
echo "你的授权码" > license.key

# 5. 一键启动
docker-compose up -d

# 6. 查看日志
docker-compose logs -f
```

#### Docker Compose 配置

项目已包含 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  fakabot:
    build: .
    container_name: fakabot
    restart: unless-stopped
    volumes:
      - ./config.json:/app/config.json
      - ./license.key:/app/license.key
      - ./data:/app/data
    ports:
      - "58001:58001"
    environment:
      - TZ=Asia/Shanghai
    networks:
      - fakabot-network

  redis:
    image: redis:7-alpine
    container_name: fakabot-redis
    restart: unless-stopped
    volumes:
      - redis-data:/data
    networks:
      - fakabot-network

volumes:
  redis-data:

networks:
  fakabot-network:
    driver: bridge
```

#### 常用 Docker 命令

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose stop

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f

# 查看状态
docker-compose ps

# 停止并删除容器
docker-compose down

# 更新代码后重新构建
git pull
docker-compose up -d --build
```

#### 优势

- ✅ **一键部署** - 无需手动安装依赖
- ✅ **环境隔离** - 不影响系统环境
- ✅ **自动重启** - 崩溃自动恢复
- ✅ **易于更新** - 一条命令更新
- ✅ **包含 Redis** - 自动配置缓存

---

### 📦 方式二：传统部署

#### 📋 环境要求

- **操作系统**: Linux (Ubuntu 20.04+) / macOS
- **Python**: 3.11+
- **内存**: 最低 1GB，推荐 2GB+
- **硬盘**: 最低 10GB
- **网络**: 需要访问 Telegram API

### 第1步：购买授权码

**联系购买**：
- 📱 Telegram: https://t.me/sonhshu
- 💰 价格：50 USDT/月起
- ⏰ 响应时间：通常 1 小时内

**购买流程**：
1. 联系客服
2. 选择套餐（月付/季付/年付）
3. 支付 USDT
4. 获得授权码

### 第2步：准备服务器

#### 方案A：使用云服务器（推荐）

**推荐服务商**：
- 阿里云轻量应用服务器（¥24/月）
- 腾讯云轻量应用服务器（¥25/月）
- Vultr（$5/月）
- DigitalOcean（$6/月）

**配置建议**：
- CPU: 1核
- 内存: 2GB
- 硬盘: 20GB
- 带宽: 1Mbps

#### 方案B：本地运行

如果只是测试，可以在本地电脑运行。

### 第3步：克隆项目

```bash
# SSH 登录服务器
ssh root@你的服务器IP

# 克隆项目
git clone https://github.com/GUGEGEBAIDU/fakabot.git
cd fakabot
```

### 第4步：安装依赖

```bash
# 更新系统
apt update && apt upgrade -y

# 安装 Python 3.11
apt install python3.11 python3.11-pip -y

# 安装项目依赖
pip3 install -r requirements.txt

# 安装 Redis（可选，用于缓存）
apt install redis-server -y
systemctl start redis
systemctl enable redis
```

### 第5步：配置机器人

#### 5.1 创建 Telegram Bot

1. 在 Telegram 搜索 [@BotFather](https://t.me/BotFather)
2. 发送 `/newbot`
3. 输入机器人名称（例如：`我的发卡机器人`）
4. 输入机器人用户名（例如：`my_faka_bot`）
5. 获得 Bot Token（例如：`123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`）

#### 5.2 获取你的 Telegram ID

1. 在 Telegram 搜索 [@userinfobot](https://t.me/userinfobot)
2. 发送任意消息
3. 获得你的 ID（例如：`123456789`）

#### 5.3 配置支付接口

**支付宝/微信**：
- 申请支付宝当面付或微信支付
- 获取 AppID、商户号、密钥

**USDT**：
- 注册 TOKEN188 或柠檬支付
- 获取 API Key 和商户号

#### 5.4 编辑配置文件

```bash
cp config.json.example config.json
vim config.json
```

**配置示例**：

```json
{
  "BOT_TOKEN": "你的Bot Token",
  "ADMIN_ID": 你的Telegram ID,
  "DOMAIN": "https://你的域名.com",
  
  "PAYMENTS": {
    "alipay": {
      "enabled": true,
      "app_id": "你的支付宝AppID",
      "private_key": "你的私钥",
      "public_key": "支付宝公钥"
    },
    "wxpay": {
      "enabled": true,
      "mch_id": "你的商户号",
      "api_key": "你的API密钥"
    },
    "usdt_token188": {
      "enabled": true,
      "api_key": "你的API Key",
      "merchant_id": "你的商户号"
    }
  },
  
  "REDIS": {
    "enabled": true,
    "host": "localhost",
    "port": 6379
  }
}
```

### 第6步：配置域名（可选但推荐）

#### 6.1 购买域名

- 阿里云：https://wanwang.aliyun.com
- 腾讯云：https://dnspod.cloud.tencent.com
- Namecheap：https://www.namecheap.com

**价格**：约 ¥50-100/年

#### 6.2 配置 DNS

添加 A 记录：
- 主机记录：`@` 或 `bot`
- 记录类型：`A`
- 记录值：`你的服务器IP`
- TTL：`600`

#### 6.3 配置 SSL 证书（推荐）

```bash
# 安装 Certbot
apt install certbot -y

# 申请证书
certbot certonly --standalone -d 你的域名.com

# 证书路径
# /etc/letsencrypt/live/你的域名.com/fullchain.pem
# /etc/letsencrypt/live/你的域名.com/privkey.pem
```

### 第7步：保存授权码

```bash
# 在项目目录下
cd /root/fakabot

# 保存授权码
echo "你的授权码" > license.key

# 示例：
# echo "C001|1738310400|abc123def456..." > license.key
```

### 第8步：启动机器人

#### 方式A：直接运行（测试用）

```bash
python3 bot.py
```

#### 方式B：后台运行（推荐）

```bash
# 使用 nohup
nohup python3 bot.py > bot.log 2>&1 &

# 查看日志
tail -f bot.log
```

#### 方式C：使用 systemd（最推荐）

```bash
# 创建服务文件
vim /etc/systemd/system/fakabot.service
```

**服务文件内容**：

```ini
[Unit]
Description=Fakabot Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/fakabot
ExecStart=/usr/bin/python3 /root/fakabot/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**启动服务**：

```bash
# 重载配置
systemctl daemon-reload

# 启动服务
systemctl start fakabot

# 设置开机自启
systemctl enable fakabot

# 查看状态
systemctl status fakabot

# 查看日志
journalctl -u fakabot -f
```

### 第9步：验证运行

1. 在 Telegram 搜索你的机器人
2. 发送 `/start`
3. 如果看到欢迎消息，说明运行成功！

**授权验证成功提示**：
```
✅ 授权验证通过
📝 客户ID: C001
📅 到期时间: 2025-11-18
⏰ 剩余天数: 30 天
```

---

## 🐳 Docker 部署详解

### 安装 Docker

#### Ubuntu/Debian

```bash
# 更新包索引
sudo apt update

# 安装依赖
sudo apt install apt-transport-https ca-certificates curl software-properties-common -y

# 添加 Docker 官方 GPG 密钥
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# 添加 Docker 仓库
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装 Docker
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io docker-compose-plugin -y

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker

# 验证安装
docker --version
docker compose version
```

#### CentOS/RHEL

```bash
# 安装依赖
sudo yum install -y yum-utils

# 添加 Docker 仓库
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# 安装 Docker
sudo yum install docker-ce docker-ce-cli containerd.io docker-compose-plugin -y

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker
```

### Docker 部署步骤

#### 1. 克隆项目

```bash
git clone https://github.com/GUGEGEBAIDU/fakabot.git
cd fakabot
```

#### 2. 配置文件

```bash
# 复制配置文件
cp config.json.example config.json

# 编辑配置
vim config.json
```

**最小配置示例**：

```json
{
  "BOT_TOKEN": "你的Bot Token",
  "ADMIN_ID": 你的Telegram ID,
  "DOMAIN": "https://你的域名.com",
  "REDIS": {
    "enabled": true,
    "host": "redis",
    "port": 6379
  }
}
```

#### 3. 保存授权码

```bash
echo "你的授权码" > license.key
```

#### 4. 启动服务

```bash
# 后台启动
docker-compose up -d

# 查看日志
docker-compose logs -f fakabot
```

#### 5. 验证运行

```bash
# 查看容器状态
docker-compose ps

# 应该看到两个容器运行中：
# fakabot        Up
# fakabot-redis  Up
```

### Docker 常见问题

**Q: 如何更新机器人？**

```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker-compose up -d --build
```

**Q: 如何查看日志？**

```bash
# 实时查看日志
docker-compose logs -f

# 查看最近100行
docker-compose logs --tail=100

# 只查看机器人日志
docker-compose logs -f fakabot
```

**Q: 如何备份数据？**

```bash
# 备份数据目录
tar -czf fakabot-backup-$(date +%Y%m%d).tar.gz data/ config.json license.key

# 恢复数据
tar -xzf fakabot-backup-20250118.tar.gz
```

**Q: 如何重启服务？**

```bash
# 重启所有服务
docker-compose restart

# 只重启机器人
docker-compose restart fakabot
```

**Q: 如何进入容器调试？**

```bash
# 进入机器人容器
docker-compose exec fakabot sh

# 查看文件
ls -la

# 退出容器
exit
```

**Q: 端口被占用怎么办？**

```bash
# 修改 docker-compose.yml 中的端口
ports:
  - "58002:58001"  # 改成其他端口
```

### Docker 性能优化

#### 限制资源使用

编辑 `docker-compose.yml`：

```yaml
services:
  fakabot:
    # ... 其他配置
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

#### 使用 Docker 网络

```bash
# 创建自定义网络
docker network create fakabot-net

# 在 docker-compose.yml 中使用
networks:
  default:
    external:
      name: fakabot-net
```

---

## ✨ 核心功能

### 💳 支付系统

支持 **4 种主流支付方式**：

1. **支付宝**
   - 当面付
   - 扫码支付
   - 自动到账确认

2. **微信支付**
   - Native 支付
   - 扫码支付
   - 实时回调

3. **USDT (TOKEN188)**
   - TRC20/ERC20
   - 自动监控到账
   - 链上验证

4. **USDT (柠檬支付)**
   - 多链支持
   - 秒级确认
   - 低手续费

### 🎯 自动发货

- ✅ **支付成功自动发货** - 无需人工干预
- ✅ **多种发货方式**：
  - Telegram 群组邀请链接
  - 卡密/激活码
  - 下载链接
  - 自定义文本
- ✅ **库存管理** - 自动扣减，库存不足提醒
- ✅ **防重复发货** - 订单去重机制

### 📊 订单管理

- ✅ **完整订单记录** - 用户、商品、金额、时间
- ✅ **订单状态追踪** - 待付款、已付款、已发货、已完成
- ✅ **订单查询** - 用户可查询历史订单
- ✅ **退款处理** - 支持订单退款
- ✅ **数据导出** - Excel 格式导出

### 👥 用户管理

- ✅ **用户信息记录** - Telegram ID、用户名、购买记录
- ✅ **用户分组** - VIP、普通用户、黑名单
- ✅ **购买统计** - 用户消费金额、购买次数
- ✅ **用户黑名单** - 防止恶意用户

### 🛍️ 商品管理

- ✅ **多商品支持** - 无限商品数量
- ✅ **商品分类** - 自定义分类
- ✅ **价格设置** - 灵活定价
- ✅ **库存管理** - 实时库存监控
- ✅ **商品上下架** - 随时控制销售

### ⚡ 性能优化

- ✅ **Redis 缓存** - 性能提升 10-100 倍
- ✅ **订单预加载** - 用户无感知等待
- ✅ **频率限制** - 防刷单、防攻击
- ✅ **自动降级** - Redis 故障不影响业务

### 🔒 安全特性

- ✅ **支付签名验证** - 防止伪造订单
- ✅ **金额验证** - 防止金额篡改
- ✅ **防重复支付** - 订单去重
- ✅ **IP 限流** - 防止恶意攻击
- ✅ **数据加密** - 敏感信息加密存储

### 🎨 管理后台

- ✅ **实时统计** - 今日订单、收入、用户数
- ✅ **数据可视化** - 图表展示
- ✅ **快速操作** - 一键发货、退款
- ✅ **日志查询** - 完整操作日志
- ✅ **系统设置** - 灵活配置

---

## 📞 购买授权

### 联系方式

- **Telegram**: [@sonhshu](https://t.me/sonhshu)
- **演示机器人**: [@fakawan_bot](https://t.me/fakawan_bot)

### 支付方式

**USDT (TRC20)**：
```
TDZM5DSSq8SrB8QTSBHyNwrcTswtCjKs9t
```

> 💡 支付后请联系客服，提供交易哈希和 Telegram 用户名

---

## 📖 使用教程

### 管理员操作

#### 1. 添加商品

```
发送给机器人：
/admin → 商品管理 → 添加商品

填写信息：
- 商品名称：VIP会员
- 商品价格：99
- 商品描述：VIP会员，享受专属权益
- 发货内容：https://t.me/+xxx（群组邀请链接）
```

#### 2. 管理库存

```
/admin → 商品管理 → 库存管理

批量导入卡密：
发送文本文件，每行一个卡密
```

#### 3. 查看订单

```
/admin → 订单管理

可以查看：
- 今日订单
- 历史订单
- 待处理订单
- 订单详情
```

#### 4. 数据统计

```
/admin → 数据统计

查看：
- 今日收入
- 本月收入
- 订单数量
- 用户数量
```

### 用户购买流程

#### 1. 用户发送 `/start`

机器人显示：
```
👋 欢迎使用自动发卡机器人！

📦 商品列表：
1. VIP会员 - 99 USDT
2. 高级课程 - 199 USDT

点击商品查看详情
```

#### 2. 选择商品

用户点击商品 → 显示详情 → 点击购买

#### 3. 选择支付方式

```
💳 请选择支付方式：
- 支付宝
- 微信支付
- USDT
```

#### 4. 完成支付

- 扫码支付
- 支付成功后自动发货
- 收到商品内容

#### 5. 查询订单

```
发送：/orders

查看历史订单和购买记录
```

---

## 🔧 高级配置

### 配置 Webhook（推荐）

使用 Webhook 比轮询更高效：

```python
# 在 config.json 中
{
  "WEBHOOK": {
    "enabled": true,
    "url": "https://你的域名.com/webhook",
    "port": 8443
  }
}
```

### 配置 Redis 缓存

```bash
# 安装 Redis
apt install redis-server -y

# 配置 Redis
vim /etc/redis/redis.conf

# 设置密码（可选）
requirepass 你的密码

# 重启 Redis
systemctl restart redis
```

### 配置反向代理（Nginx）

```nginx
server {
    listen 80;
    server_name 你的域名.com;
    
    location / {
        proxy_pass http://127.0.0.1:58001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 数据备份

```bash
# 备份数据库
cp fakabot.db fakabot.db.backup

# 定时备份（每天凌晨3点）
crontab -e

# 添加：
0 3 * * * cp /root/fakabot/fakabot.db /root/backup/fakabot_$(date +\%Y\%m\%d).db
```

---

## ❓ 常见问题

### 购买相关

**Q: 可以试用吗？**  
A: 建议先购买月付（50 USDT）试用一个月，满意后再升级年付。

**Q: 授权码会过期吗？**  
A: 是的，月付30天，季付90天，年付365天。到期前7天会自动提醒。

**Q: 可以退款吗？**  
A: 首次购买7天内不满意可申请全额退款。

**Q: 包含技术支持吗？**  
A: 是的，所有订阅都包含技术支持，响应时间通常 1-24 小时。

**Q: 续费如何操作？**  
A: 联系客服，支付续费金额，获得新授权码，替换 license.key 文件即可。

### 技术相关

**Q: 需要什么配置的服务器？**  
A: 最低 1核1GB，推荐 1核2GB。月费约 $5-10。

**Q: 必须要域名吗？**  
A: 不是必须的，但强烈推荐。域名可以配置 SSL，更安全。

**Q: 支持哪些支付方式？**  
A: 机器人支持支付宝、微信、USDT (TOKEN188)、USDT (柠檬支付)。购买授权使用 USDT (TRC20)。

**Q: 可以自定义界面吗？**  
A: 可以，修改配置文件中的文案和按钮即可。

**Q: 支持多语言吗？**  
A: 目前支持中文，可以自行翻译配置文件实现多语言。

**Q: 数据存储在哪里？**  
A: 使用 SQLite 数据库，存储在 fakabot.db 文件中。

**Q: 如何备份数据？**  
A: 定期备份 fakabot.db 文件和 config.json 配置文件。

**Q: 授权码丢了怎么办？**  
A: 联系客服，提供购买记录，可以重新发送授权码。

### 使用相关

**Q: 如何添加商品？**  
A: 发送 /admin → 商品管理 → 添加商品。

**Q: 如何查看收入？**  
A: 发送 /admin → 数据统计。

**Q: 支持自动发货吗？**  
A: 是的，支付成功后自动发货，无需人工干预。

**Q: 可以设置优惠券吗？**  
A: 可以，在管理后台设置优惠码和折扣。

**Q: 支持分销吗？**  
A: 当前版本不支持，后续版本会添加。

---

## 🔒 授权保护

本项目采用内置授权验证，代码中嵌入了授权检查逻辑。

**无法绕过的原因**：
- ✅ 授权检查嵌入在每个文件中
- ✅ 删除授权检查会导致程序崩溃
- ✅ 授权码采用签名验证，无法伪造
- ✅ 破解成本远高于购买价格

---

## 📄 许可证

本项目为商业软件，采用订阅制授权。

未经授权，禁止：
- 反编译或反向工程
- 分发或转售
- 删除版权声明
- 商业使用（需购买授权）

---

<div align="center">

**专业的 Telegram 自动发卡解决方案**

Made with ❤️ by Fakabot Team

</div>
