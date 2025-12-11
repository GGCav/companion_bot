#!/bin/bash

set -e

echo "======================================"
echo "Companion Bot Setup"
echo "======================================"

if [[ ! -f /proc/cpuinfo ]] || ! grep -q "Raspberry Pi" /proc/cpuinfo; then
    echo "Warning: This script is designed for Raspberry Pi"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

echo "Installing system dependencies..."
sudo apt-get install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    python3-setuptools \
    portaudio19-dev \
    libportaudio2 \
    libasound2-dev \
    libatlas-base-dev \
    libhdf5-dev \
    libopenblas-dev \
    liblapack-dev \
    gfortran \
    libopencv-dev \
    python3-opencv \
    libcamera-dev \
    libcamera-apps \
    cmake \
    build-essential \
    git \
    i2c-tools \
    python3-smbus \
    espeak \
    libespeak-dev

echo "Enabling I2C and Camera interfaces..."
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_camera 0

echo "Installing pigpio..."
wget https://github.com/joan2937/pigpio/archive/master.zip
unzip master.zip
cd pigpio-master
make
sudo make install
cd ..
rm -rf pigpio-master master.zip

sudo systemctl enable pigpiod
sudo systemctl start pigpiod

echo "Creating Python virtual environment..."
python3 -m venv venv

source venv/bin/activate

pip install --upgrade pip setuptools wheel

echo "Installing Python packages..."
pip install -r requirements.txt

echo "Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

echo "Downloading Ollama model..."
ollama pull llama3.2:3b

echo "Downloading Whisper model..."
python3 -c "import whisper; whisper.load_model('base')"

echo "Creating data directories..."
mkdir -p data/{users,conversations,logs}
mkdir -p assets/{animations,sounds}

chmod +x main.py
chmod 755 scripts/*.py 2>/dev/null || true

echo "Creating systemd service..."
sudo tee /etc/systemd/system/companion-bot.service > /dev/null <<EOF
[Unit]
Description=Companion Bot Service
After=network.target pigpiod.service ollama.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/python main.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload

echo ""
echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Review and adjust config/settings.yaml for your hardware"
echo "3. Run tests: python -m pytest tests/"
echo "4. Start bot: python main.py"
echo ""
echo "Optional: Enable auto-start on boot:"
echo "  sudo systemctl enable companion-bot"
echo "  sudo systemctl start companion-bot"
echo ""
echo "View logs:"
echo "  sudo journalctl -u companion-bot -f"
echo ""
