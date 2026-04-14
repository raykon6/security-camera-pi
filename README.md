# Security Camera - IR Lab

A professional IoT security camera system built with Raspberry Pi 5, WebRTC, and Anedya IoT platform.

## Features
- Live video streaming via WebRTC (1920x1080)
- Phone as IP camera using IP Webcam app
- JWT authentication
- Anedya IoT integration - logs and TURN relay
- Professional web dashboard
- Snapshot capture
- Auto-reconnect on network drop
- Disconnect button

## Hardware Required
- Raspberry Pi 5
- Android phone with IP Webcam app
- WiFi network / Mobile hotspot

## Tech Stack
- Python - aiortc, aiohttp, OpenCV, PyJWT, requests
- WebRTC for low latency streaming
- Anedya IoT Platform for logs and relay
- HTML CSS JavaScript for frontend

## Quick Setup

### 1. Install dependencies
pip3 install -r requirements.txt --break-system-packages
pip3 install git+https://github.com/anedyaio/anedya-dev-sdk-python.git --break-system-packages
### 2. Configure credentials
cp config.example.py config.py
nano config.py
### 3. Start phone camera
- Install IP Webcam app on Android
- Start server in app
- Note the IP address shown
### 4. Run server
python3 server.py &
cd web && python3 -m http.server 9090

### 5. Access dashboard
http://PI_IP:9090

## Project Architecture
Android Phone (IP Webcam)
|
| MJPEG stream
v
Raspberry Pi 5

WebRTC Server (aiortc)
JWT Auth
Anedya IoT SDK
|
| Anedya TURN Relay
v
Browser (Anywhere)
Live Dashboard
1920x1080 stream
Event logs


## Security Features
- JWT token based authentication
- TLS encryption via Anedya TURN relay
- CORS protection
- No port forwarding needed
- Credentials in separate config file

## Anedya Integration
- Device logs sent to Anedya dashboard
- TURN relay for secure remote access
- Events tracked: login, viewer connect, camera status

## API Endpoints
- POST /login - JWT authentication
- POST /offer - WebRTC SDP exchange
- GET /health - Server status

## GitHub
https://github.com/raykon6/security-camera-pi
