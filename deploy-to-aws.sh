#!/bin/bash
# Sunucuyu AWS EC2 Ubuntu instance'a deploy eder
# Kullanim: ./deploy-to-aws.sh <EC2_PUBLIC_IP> <PEM_DOSYA_YOLU>
#
# Ornek: ./deploy-to-aws.sh 16.16.192.26 ~/Downloads/"Ubuntu Cloud Key.pem"

set -e

if [ $# -lt 2 ]; then
    echo "Kullanim: $0 <EC2_PUBLIC_IP> <PEM_DOSYA_YOLU>"
    echo "Ornek:  $0 16.16.192.26 ~/Downloads/key.pem"
    exit 1
fi

EC2_IP="$1"
PEM_FILE="$2"
EC2_USER="ubuntu"
REMOTE_DIR="/home/$EC2_USER/chess-server"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "1) EC2'ye Python kontrol ediliyor..."
ssh -i "$PEM_FILE" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_IP" \
    "sudo apt-get update && sudo apt-get install -y python3"

echo "2) Uzak dizin olusturuluyor..."
ssh -i "$PEM_FILE" "$EC2_USER@$EC2_IP" "mkdir -p $REMOTE_DIR"

echo "3) Sunucu dosyasi yukleniyor..."
scp -i "$PEM_FILE" "$PROJECT_DIR/server.py" "$EC2_USER@$EC2_IP:$REMOTE_DIR/"

echo "4) systemd servisi kuruluyor..."
ssh -i "$PEM_FILE" "$EC2_USER@$EC2_IP" "sudo bash -c 'cat > /etc/systemd/system/chess-server.service << EOF
[Unit]
Description=Chess Game Server
After=network.target

[Service]
ExecStart=/usr/bin/python3 $REMOTE_DIR/server.py
WorkingDirectory=$REMOTE_DIR
Restart=always
User=$EC2_USER

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable chess-server
sudo systemctl restart chess-server'"

echo ""
echo "========================================="
echo "  Deploy tamamlandi!"
echo "========================================="
echo "Sunucu adresi: $EC2_IP:5002"
echo ""
echo "Sunucu adresi: $EC2_IP:5002"
echo ""
echo "Istemcilerde config.ini dosyasinda:"
echo "  ip = $EC2_IP"
echo ""
echo "Durum kontrolu:"
echo "  ssh -i \"$PEM_FILE\" $EC2_USER@$EC2_IP 'sudo systemctl status chess-server'"
echo "Loglar:"
echo "  ssh -i \"$PEM_FILE\" $EC2_USER@$EC2_IP 'sudo journalctl -u chess-server -f'"
