#!/bin/bash
# =============================================================================
# IAM Guardian - EC2 Setup Script
# Run as root (or with sudo) on a fresh Ubuntu 22.04 instance.
# =============================================================================

set -e
exec > /var/log/iam-guardian-setup.log 2>&1

# ── Variables ────────────────────────────────────────────────────────────────
GITHUB_REPO_URL="https://github.com/Sasivar/IAM_Guardian.git"
MASTER_BUCKET="iam-guardian-master-bucket"   # Change to your actual bucket name
AWS_REGION="ap-south-1"                      # Change to your actual region

echo "======================================"
echo " IAM Guardian Setup Starting"
echo "======================================"

# ── 1. System update and base dependencies ───────────────────────────────────
echo "[1/8] Updating system and installing base dependencies..."
apt-get update -y
apt-get upgrade -y
apt-get install -y python3-pip python3-venv git curl ca-certificates gnupg

# ── 2. Install Node.js v20 via NodeSource ────────────────────────────────────
echo "[2/8] Installing Node.js v20..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs
echo "Node version : $(node -v)"
echo "NPM version  : $(npm -v)"

# ── 3. Get EC2 public IP ─────────────────────────────────────────────────────
echo "[3/8] Fetching EC2 public IP..."

# Try IMDSv2 first (token-based), fall back to IMDSv1
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" 2>/dev/null || true)

if [ -n "$TOKEN" ]; then
  PUBLIC_IP=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" \
    http://169.254.169.254/latest/meta-data/public-ipv4)
else
  PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
fi

# Validate it looks like an IP address, otherwise hit public fallback
if ! echo "$PUBLIC_IP" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$'; then
  echo "WARNING: Metadata service failed. Got: $PUBLIC_IP"
  echo "Trying fallback via checkip.amazonaws.com..."
  PUBLIC_IP=$(curl -s https://checkip.amazonaws.com | tr -d '[:space:]')
fi

echo "Public IP: $PUBLIC_IP"

# ── 4. Clone GitHub repository ───────────────────────────────────────────────
echo "[4/8] Cloning IAM Guardian repository..."
cd /home/ubuntu
git clone "$GITHUB_REPO_URL" iam-guardian
chown -R ubuntu:ubuntu /home/ubuntu/iam-guardian

# ── 5. Create backend .env file ──────────────────────────────────────────────
echo "[5/8] Creating backend .env file..."
cat > /home/ubuntu/iam-guardian/backend/.env << EOF
MASTER_BUCKET=${MASTER_BUCKET}
AWS_REGION=${AWS_REGION}
EOF
chown ubuntu:ubuntu /home/ubuntu/iam-guardian/backend/.env

# ── 6. Create required __init__.py files ─────────────────────────────────────
echo "[6/8] Creating __init__.py files..."
touch /home/ubuntu/iam-guardian/backend/collector/__init__.py
touch /home/ubuntu/iam-guardian/backend/agent/__init__.py
touch /home/ubuntu/iam-guardian/backend/reports/__init__.py
chown -R ubuntu:ubuntu /home/ubuntu/iam-guardian/backend/

# ── 7. Set up Python virtual environment and install dependencies ─────────────
echo "[7/8] Setting up Python virtual environment..."
cd /home/ubuntu/iam-guardian/backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install fastapi uvicorn boto3 python-dotenv reportlab

# ── 8. Build React frontend ───────────────────────────────────────────────────
echo "[8/8] Building React frontend..."

APP_JS="/home/ubuntu/iam-guardian/frontend/src/App.js"
REPLACE_IP="$PUBLIC_IP" python3 << 'PYEOF'
import re, os
path = os.environ.get('APP_JS', '/home/ubuntu/iam-guardian/frontend/src/App.js')
new_ip = os.environ['REPLACE_IP']
with open(path, 'r') as f:
    content = f.read()
updated = re.sub(r'const API = "http://[^"]*:8000"',
                 'const API = "http://' + new_ip + ':8000"', content)
with open(path, 'w') as f:
    f.write(updated)
print('Updated App.js with IP:', new_ip)
PYEOF

cd /home/ubuntu/iam-guardian/frontend
npm install
npm run build
chown -R ubuntu:ubuntu /home/ubuntu/iam-guardian/frontend

# ── Start backend (FastAPI / Uvicorn) ────────────────────────────────────────
echo "Starting backend on port 8000..."
cd /home/ubuntu/iam-guardian/backend
source venv/bin/activate
# Using < /dev/null ensures background process won't hang waiting for stdin
nohup uvicorn main:app --host 0.0.0.0 --port 8000 < /dev/null > /home/ubuntu/backend.log 2>&1 &
echo "Backend PID: $!"

# ── Start frontend (React build served via Python HTTP) ──────────────────────
echo "Starting frontend on port 3000..."
cd /home/ubuntu/iam-guardian/frontend/build
nohup python3 -m http.server 3000 < /dev/null > /home/ubuntu/frontend.log 2>&1 &
echo "Frontend PID: $!"

echo "======================================"
echo " IAM Guardian Setup Complete!"
echo " Dashboard : http://$PUBLIC_IP:3000"
echo " API       : http://$PUBLIC_IP:8000"
echo " Setup log : /var/log/iam-guardian-setup.log"
echo " Backend log: /home/ubuntu/backend.log"
echo " Frontend log: /home/ubuntu/frontend.log"
echo "======================================"
