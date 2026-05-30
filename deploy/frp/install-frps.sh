#!/bin/bash
# ============================================
# 服务器 frps 安装脚本
# 用法：
#   1. 在本机下载 frp 安装包，放到本脚本同目录
#   2. scp -r deploy/frp root@<SERVER_IP>:/tmp/
#   3. ssh 到服务器: cd /tmp/frp && bash install-frps.sh
# ============================================
set -e

FRP_VERSION="0.61.2"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TGZ_FILE="${SCRIPT_DIR}/frp_${FRP_VERSION}_linux_amd64.tar.gz"

echo "===== 1. 安装 frp ${FRP_VERSION} ====="

if [ -f "$TGZ_FILE" ]; then
    echo "发现本地安装包: $(basename "$TGZ_FILE")，跳过下载"
else
    echo "未找到本地安装包，尝试下载..."
    # GitHub 镜像列表（阿里云服务器优先用镜像）
    MIRRORS=(
        "https://ghproxy.net/https://github.com/fatedier/frp/releases/download/v${FRP_VERSION}/frp_${FRP_VERSION}_linux_amd64.tar.gz"
        "https://gh-proxy.com/https://github.com/fatedier/frp/releases/download/v${FRP_VERSION}/frp_${FRP_VERSION}_linux_amd64.tar.gz"
        "https://github.com/fatedier/frp/releases/download/v${FRP_VERSION}/frp_${FRP_VERSION}_linux_amd64.tar.gz"
    )
    for url in "${MIRRORS[@]}"; do
        echo "尝试: $url"
        if curl -fsSL --connect-timeout 10 --max-time 120 -o "$TGZ_FILE" "$url"; then
            echo "下载成功"
            break
        fi
        echo "失败，尝试下一个..."
        rm -f "$TGZ_FILE"
    done
    if [ ! -f "$TGZ_FILE" ]; then
        echo "❌ 所有下载源均失败！"
        echo "请在本机下载后放到脚本同目录："
        echo "  https://github.com/fatedier/frp/releases/download/v${FRP_VERSION}/frp_${FRP_VERSION}_linux_amd64.tar.gz"
        exit 1
    fi
fi

cd /tmp
tar xzf "$TGZ_FILE"
cp "frp_${FRP_VERSION}_linux_amd64/frps" /usr/local/bin/frps
chmod +x /usr/local/bin/frps
rm -rf "frp_${FRP_VERSION}_linux_amd64"

echo "===== 2. 创建目录 & 配置文件 ====="
mkdir -p /etc/frp
cp "${SCRIPT_DIR}/frps.toml" /etc/frp/frps.toml

echo "===== 3. 创建 systemd 服务 ====="
cat > /etc/systemd/system/frps.service << 'SYSTEMD'
[Unit]
Description=frp Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/frps -c /etc/frp/frps.toml
Restart=on-failure
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
SYSTEMD

echo "===== 4. 启动 frps ====="
systemctl daemon-reload
systemctl enable frps
systemctl start frps

echo "===== 5. 验证 ====="
sleep 2
systemctl status frps --no-pager
ss -tlnp | grep -E "7000|7500"

# 尝试获取公网 IP（优先），fallback 到内网 IP
PUBLIC_IP=$(curl -s --connect-timeout 3 ifconfig.me 2>/dev/null || curl -s --connect-timeout 3 icanhazip.com 2>/dev/null || hostname -I | awk '{print $1}')

echo ""
echo "✅ frps 安装完成！"
echo "   frps 端口:  7000 (frpc 连接用)"
echo "   Dashboard:  http://${PUBLIC_IP}:7500 (admin / admin123)"
echo ""
echo "   ⚠️  如果 Dashboard 无法访问，检查阿里云安全组是否放行 7500 端口"
echo "   ⚠️  安全起见，建议修改 /etc/frp/frps.toml 中的 auth.token 和 dashboard 密码"
