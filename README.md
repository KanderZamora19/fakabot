# 🤖 Fakabot

> 专业的 Telegram 自动发卡机器人 | Docker 一键部署 | 全自动发货

[![License](https://img.shields.io/badge/license-Commercial-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)]()
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://t.me/sonhshu)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)]()

**适用场景**：知识付费 · 虚拟商品 · 在线课程 · 软件授权 · 会员订阅

🎬 **在线演示**: [@fakawan_bot](https://t.me/fakawan_bot) | 📱 **联系客服**: [@sonhshu](https://t.me/sonhshu)

---

## ✨ 核心特性

<table>
<tr>
<td width="50%">

### 💳 支付系统
- 支付宝当面付
- 微信 Native 支付
- USDT (TOKEN188)
- USDT (柠檬支付)

### 🎯 自动发货
- 支付成功自动发货
- 群组邀请链接
- 卡密/激活码
- 库存自动管理

</td>
<td width="50%">

### ⚡ 性能优化
- Redis 缓存
- 性能提升 10-100 倍
- 频率限制
- 自动降级

### 🎨 管理后台
- 实时数据统计
- 订单管理
- 商品管理
- 用户管理

</td>
</tr>
</table>

---

## 🚀 快速开始

### Docker 一键部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/GUGEGEBAIDU/fakabot.git
cd fakabot

# 2. 配置文件
cp config.json.example config.json
vim config.json  # 填写 Bot Token、管理员 ID

# 3. 保存授权码
echo "你的授权码" > license.key

# 4. 启动服务
docker-compose up -d
```

**就这么简单！** 5分钟搞定 ✅

<details>
<summary>📖 查看详细部署教程</summary>

### 环境要求

- Docker & Docker Compose
- 服务器（1核2GB 以上）
- Telegram Bot Token

### 详细步骤

#### 1. 购买授权码

联系客服：[@sonhshu](https://t.me/sonhshu)

#### 2. 创建 Telegram Bot

1. 找 [@BotFather](https://t.me/BotFather)
2. 发送 `/newbot`
3. 获取 Bot Token

#### 3. 获取管理员 ID

1. 找 [@userinfobot](https://t.me/userinfobot)
2. 获取你的 Telegram ID

#### 4. 配置支付接口

- **支付宝/微信**: 申请商户号和密钥
- **USDT**: 注册 TOKEN188 或柠檬支付

#### 5. 编辑配置文件

```json
{
  "BOT_TOKEN": "你的Bot Token",
  "ADMIN_ID": 你的Telegram ID,
  "DOMAIN": "https://你的域名.com",
  "PAYMENTS": {
    "alipay": { "enabled": true, ... },
    "wxpay": { "enabled": true, ... },
    "usdt_token188": { "enabled": true, ... }
  }
}
```

#### 6. 启动服务

```bash
docker-compose up -d
```

#### 7. 验证运行

在 Telegram 搜索你的机器人，发送 `/start`

</details>

---

## 📖 使用文档

<details>
<summary>🔧 管理员操作</summary>

### 添加商品

```
/admin → 商品管理 → 添加商品
```

填写：商品名称、价格、描述、发货内容

### 管理库存

```
/admin → 商品管理 → 库存管理
```

批量导入卡密（文本文件，每行一个）

### 查看订单

```
/admin → 订单管理
```

查看今日订单、历史订单、订单详情

### 数据统计

```
/admin → 数据统计
```

查看今日收入、本月收入、订单数量

</details>

<details>
<summary>👥 用户购买流程</summary>

### 1. 用户发送 `/start`

显示商品列表

### 2. 选择商品

点击商品 → 查看详情 → 点击购买

### 3. 选择支付方式

支付宝 / 微信 / USDT

### 4. 完成支付

扫码支付 → 自动发货 → 收到商品

### 5. 查询订单

发送 `/orders` 查看历史订单

</details>

<details>
<summary>🐳 Docker 命令</summary>

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose stop

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f

# 更新代码
git pull && docker-compose up -d --build

# 备份数据
tar -czf backup.tar.gz data/ config.json license.key
```

</details>

<details>
<summary>⚙️ 高级配置</summary>

### 配置域名和 SSL

```bash
# 安装 Certbot
apt install certbot -y

# 申请证书
certbot certonly --standalone -d 你的域名.com
```

### 配置 Nginx 反向代理

```nginx
server {
    listen 80;
    server_name 你的域名.com;
    
    location / {
        proxy_pass http://127.0.0.1:58001;
        proxy_set_header Host $host;
    }
}
```

### 配置 Redis 密码

```bash
# 编辑 Redis 配置
vim /etc/redis/redis.conf

# 添加密码
requirepass 你的密码

# 重启 Redis
systemctl restart redis
```

</details>

---

## 💰 订阅价格

| 套餐 | 价格 | 优惠 | 推荐 |
|------|------|------|------|
| 月付 | 50 USDT/月 | - | 试用 |
| 季付 | 135 USDT/季 | 10% | ⭐ 推荐 |
| 年付 | 510 USDT/年 | 15% | 最划算 |

### 购买方式

**联系客服**: [@sonhshu](https://t.me/sonhshu)

**支付方式**: USDT (TRC20)
```
TDZM5DSSq8SrB8QTSBHyNwrcTswtCjKs9t
```

> 💡 支付后请提供交易哈希和 Telegram 用户名

---

## ❓ 常见问题

<details>
<summary><b>Q: 可以试用吗？</b></summary>

A: 建议先购买月付（50 USDT）试用一个月，满意后再升级年付。首次购买 7 天内不满意可全额退款。

</details>

<details>
<summary><b>Q: 需要什么配置的服务器？</b></summary>

A: 最低 1核1GB，推荐 1核2GB。月费约 $5-10。

</details>

<details>
<summary><b>Q: 必须要域名吗？</b></summary>

A: 不是必须的，但强烈推荐。域名可以配置 SSL，更安全。

</details>

<details>
<summary><b>Q: 支持哪些支付方式？</b></summary>

A: 机器人支持支付宝、微信、USDT。购买授权使用 USDT (TRC20)。

</details>

<details>
<summary><b>Q: 授权码会过期吗？</b></summary>

A: 是的，月付30天，季付90天，年付365天。到期前7天会自动提醒。

</details>

<details>
<summary><b>Q: 如何续费？</b></summary>

A: 联系客服，支付续费金额，获得新授权码，替换 license.key 文件即可。

</details>

<details>
<summary><b>Q: 包含技术支持吗？</b></summary>

A: 是的，所有订阅都包含技术支持，响应时间通常 1-24 小时。

</details>

<details>
<summary><b>Q: 数据如何备份？</b></summary>

A: 定期备份 `data/` 目录、`config.json` 和 `license.key` 文件。

</details>

---

## 📞 联系我们

- **Telegram**: [@sonhshu](https://t.me/sonhshu)
- **演示机器人**: [@fakawan_bot](https://t.me/fakawan_bot)
- **GitHub**: [GUGEGEBAIDU/fakabot](https://github.com/GUGEGEBAIDU/fakabot)

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

[开始使用](#-快速开始) · [查看演示](https://t.me/fakawan_bot) · [联系客服](https://t.me/sonhshu)

</div>
