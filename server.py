import asyncio
import datetime
import logging
import threading
import time
import numpy as np
import cv2
import jwt
import anedya
import requests
from av import VideoFrame
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack, RTCConfiguration, RTCIceServer

from config import (
    CAM_USERNAME, CAM_PASSWORD, CAM_SECRET,
    PHONE_CAMERA_URL,
    ANEDYA_NODE_ID, ANEDYA_CONN_KEY,
    SERVER_PORT
)

pcs           = set()
anedya_status = "not_started"
anedya_client = None

TURN_CONFIG = RTCConfiguration(iceServers=[
    RTCIceServer(urls="stun:stun.l.google.com:19302"),
    RTCIceServer(
        urls="turn:turn1.ap-in-1.anedya.io",
        username="7ZdnauGR2Xzs:1776161882",
        credential="8e1b032cce2eeb60a3252ee0b239072fb0c5c7bce230e4f47110efb614c0dd5f"
    )
])


def log_to_anedya(message):
    try:
        url = "https://device.ap-in-1.anedya.io/v1/logs/submitLogs"
        headers = {
            "Content-Type": "application/json",
            "deviceid": ANEDYA_NODE_ID,
            "authorization": ANEDYA_CONN_KEY
        }
        payload = {"data": [{"log": message, "timestamp": 0}]}
        r = requests.post(url, json=payload, headers=headers, timeout=5)
        if r.status_code == 200:
            print(f"[Anedya] Log sent: {message}")
        else:
            print(f"[Anedya] Log failed: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"[Anedya] Log error: {e}")


def init_anedya():
    global anedya_status, anedya_client
    try:
        config = anedya.AnedyaConfig()
        config.set_deviceid(ANEDYA_NODE_ID)
        config.set_connection_key(ANEDYA_CONN_KEY)
        config.connection_mode = anedya.ConnectionMode.HTTP
        config.set_region("ap-in-1")
        anedya_client = anedya.AnedyaClient(config)
        anedya_status = "connected"
        print("[Anedya] Ready!")
        log_to_anedya("Security camera started")
    except Exception as e:
        anedya_status = "error"
        print(f"[Anedya] Error: {e}")


class PhoneCameraTrack(VideoStreamTrack):
    kind = "video"

    def __init__(self):
        super().__init__()
        print(f"[Camera] Connecting: {PHONE_CAMERA_URL}")
        self.cap = cv2.VideoCapture(PHONE_CAMERA_URL)
        if not self.cap.isOpened():
            print("[Camera] ERROR — Phone camera nahi mili!")
        else:
            print("[Camera] Connected!")
            log_to_anedya("Camera connected")

    async def recv(self):
        pts, time_base = await self.next_timestamp()
        ret, frame = self.cap.read()
        if not ret:
            print("[Camera] Reconnecting...")
            self.cap.release()
            await asyncio.sleep(2)
            self.cap = cv2.VideoCapture(PHONE_CAMERA_URL)
            frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        vf = VideoFrame.from_ndarray(frame, format="rgb24")
        vf.pts = pts
        vf.time_base = time_base
        return vf


def make_token(username):
    payload = {
        "sub": username,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    }
    return jwt.encode(payload, CAM_SECRET, algorithm="HS256")


def valid_token(request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return False
    try:
        jwt.decode(auth[7:], CAM_SECRET, algorithms=["HS256"])
        return True
    except Exception:
        return False


async def handle_login(request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Bad request"}, status=400)
    if data.get("username") == CAM_USERNAME and \
       data.get("password") == CAM_PASSWORD:
        token = make_token(data["username"])
        print(f"[Auth] Login OK — {data['username']}")
        log_to_anedya(f"User login: {data['username']}")
        return web.json_response({"token": token})
    print("[Auth] Failed login")
    log_to_anedya("Failed login attempt")
    return web.json_response({"error": "Wrong credentials"}, status=401)


async def handle_offer(request):
    if not valid_token(request):
        return web.json_response({"error": "Unauthorized"}, status=401)
    try:
        params = await request.json()
    except Exception:
        return web.json_response({"error": "Bad request"}, status=400)
    pc = RTCPeerConnection(configuration=TURN_CONFIG)
    pcs.add(pc)
    print(f"[WebRTC] Viewer connected. Total: {len(pcs)}")
    log_to_anedya(f"New viewer. Total: {len(pcs)}")

    @pc.on("connectionstatechange")
    async def on_state():
        print(f"[WebRTC] State: {pc.connectionState}")
        if pc.connectionState in ["failed", "closed", "disconnected"]:
            await pc.close()
            pcs.discard(pc)
            log_to_anedya(f"Viewer left. Total: {len(pcs)}")

    pc.addTrack(PhoneCameraTrack())
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    return web.json_response({
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type
    })


async def handle_health(request):
    return web.json_response({
        "status": "running",
        "camera": "phone_ip_cam",
        "connections": len(pcs),
        "anedya_status": anedya_status,
        "local_url": f"http://10.169.220.157:{SERVER_PORT}"
    })


@web.middleware
async def cors_mw(request, handler):
    if request.method == "OPTIONS":
        resp = web.Response(status=200)
    else:
        try:
            resp = await handler(request)
        except Exception as e:
            print(f"[Error] {e}")
            resp = web.json_response({"error": "Server error"}, status=500)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
    return resp


async def on_shutdown(app):
    print("[Server] Shutting down...")
    log_to_anedya("Camera server stopped")
    await asyncio.gather(*[pc.close() for pc in pcs])
    pcs.clear()


def main():
    print("\n" + "="*45)
    print(" Security Camera — IR Lab")
    print("="*45)
    t = threading.Thread(target=init_anedya, daemon=True, name="Anedya")
    t.start()
    time.sleep(2)
    app = web.Application(middlewares=[cors_mw])
    app.on_shutdown.append(on_shutdown)
    app.router.add_post("/login", handle_login)
    app.router.add_post("/offer", handle_offer)
    app.router.add_get("/health", handle_health)
    app.router.add_options("/login", lambda r: web.Response())
    app.router.add_options("/offer", lambda r: web.Response())
    logging.basicConfig(level=logging.WARNING)
    print(f" URL    : http://10.169.220.157:{SERVER_PORT}")
    print(f" Health : http://10.169.220.157:{SERVER_PORT}/health")
    print("="*45 + "\n")
    web.run_app(app, host="0.0.0.0", port=SERVER_PORT, print=None)


if __name__ == "__main__":
    main()
