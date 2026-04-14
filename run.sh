#!/bin/bash

# ================================================
# Security Camera — IR Lab
# Run Script
# ================================================

echo ""
echo "============================================="
echo " Security Camera — IR Lab"
echo "============================================="

# Check config file
if [ ! -f "config.py" ]; then
    echo "[ERROR] config.py nahi mila!"
    echo "Run: cp config.example.py config.py"
    echo "Phir apni values bharo"
    exit 1
fi

# Kill any existing servers
echo "[*] Purane servers band kar raha hai..."
fuser -k 8080/tcp 2>/dev/null
fuser -k 9090/tcp 2>/dev/null
sleep 1

# Start WebRTC server
echo "[*] WebRTC server start ho raha hai..."
cd "$(dirname "$0")"
python3 server.py &
SERVER_PID=$!
echo "[+] Server PID: $SERVER_PID"

# Wait for server to start
sleep 3

# Start web app
echo "[*] Web app start ho raha hai..."
cd web && python3 -m http.server 9090 &
WEB_PID=$!
echo "[+] Web PID: $WEB_PID"

# Get Pi IP
IP=$(hostname -I | awk '{print $1}')

echo ""
echo "============================================="
echo " SYSTEM READY!"
echo "============================================="
echo " Web App : http://$IP:9090"
echo " API     : http://$IP:8080"
echo " Health  : http://$IP:8080/health"
echo "============================================="
echo ""
echo " Ctrl+C se band karo"
echo ""

# Wait and handle Ctrl+C
trap "echo 'Shutting down...'; kill $SERVER_PID $WEB_PID 2>/dev/null; exit 0" INT
wait
