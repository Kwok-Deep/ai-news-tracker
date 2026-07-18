# AI 电报 · 部署指南

## 方案一：Railway（推荐，最简单）

Railway 提供免费的 Docker 部署，自动分配公网域名。

### 步骤：

1. **注册 Railway**
   - 访问 https://railway.app 用 GitHub 登录
   - 新用户有 $5 免费额度，足够运行数月

2. **创建项目**
   - 点击 "New Project" → "Deploy from GitHub repo"
   - 先将代码推送到 GitHub（见下方 Git 推送步骤）
   - 选择你的 GitHub 仓库

3. **配置环境变量**（可选）
   - 在 Settings → Variables 中添加：`PORT = 3000`

4. **获取访问地址**
   - 部署成功后，在 Settings → Networking → Generate Domain
   - 会得到类似 `ai-news-tracker.up.railway.app` 的域名
   - 手机/电脑浏览器直接访问即可

---

## 方案二：Render

Render 也支持 Docker 部署，有免费套餐。

1. 访问 https://render.com 用 GitHub 登录
2. New → Web Service → 连接 GitHub 仓库
3. 环境选 "Docker"，区域选 "Singapore"（离中国近）
4. 实例类型选 "Free"
5. 部署后会自动分配 `.onrender.com` 域名

注意：免费版 15 分钟无请求会休眠，首次访问需等待 ~30 秒唤醒。

---

## 方案三：VPS 部署（最稳定，推荐长期运行）

如果你有一台云服务器（阿里云、腾讯云、AWS 等），可以直接部署。

### 在服务器上执行：

```bash
# 1. 安装 Python 3（如果没有）
# Ubuntu/Debian:
sudo apt update && sudo apt install -y python3 python3-pip

# CentOS/RHEL:
# sudo yum install -y python3

# 2. 上传项目文件
scp -r ai-news-tracker/ user@your-server:/opt/

# 3. 在服务器上运行
cd /opt/ai-news-tracker
nohup python3 -u server.py > app.log 2>&1 &

# 4. 开放防火墙端口（默认 3000）
# sudo ufw allow 3000/tcp   # Ubuntu
# sudo firewall-cmd --add-port=3000/tcp --permanent && sudo firewall-cmd --reload  # CentOS
```

### 使用 systemd 保持后台运行：

```bash
sudo tee /etc/systemd/system/ai-news.service << 'EOF'
[Unit]
Description=AI News Telegraph
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/ai-news-tracker
ExecStart=/usr/bin/python3 -u server.py
Restart=always
RestartSec=10
Environment=PORT=3000

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now ai-news
```

访问地址：`http://你的服务器IP:3000`

---

## 方案四：Docker 部署（通用）

任何支持 Docker 的平台都可以：

```bash
# 构建镜像
docker build -t ai-news-tracker .

# 运行
docker run -d -p 3000:3000 --restart always --name ai-news ai-news-tracker
```

---

## Git 推送步骤（用于 Railway/Render）

```bash
cd ai-news-tracker
git init
git add -A
git commit -m "AI News Telegraph - multi-source real-time aggregator"

# 在 GitHub 创建仓库后：
git remote add origin https://github.com/你的用户名/ai-news-tracker.git
git branch -M main
git push -u origin main
```

---

## 本地运行

```bash
cd ai-news-tracker
python3 server.py
# 访问 http://localhost:3000
```
