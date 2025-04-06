import asyncio
import json
import websockets
from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack, RTCIceCandidate ,RTCIceServer ,RTCConfiguration
from aiortc.contrib.media import MediaPlayer, MediaRelay
from av import AudioFrame
import pyaudio
import struct

import struct
SIGNALING_SERVER = "ws://104.155.143.57:8888"

def parse_pixel_streaming_event(data: bytes):
    """Parses a Pixel Streaming RTCDataChannel event based on Epic Games Pixel Streaming DataChannel definitions."""
    if not data:
        return {"error": "Empty data"}
    
    event_id = data[0]  # First byte is the event ID
    parsed_event = {"event_id": event_id, "raw_data": data.hex()}
    
    try:
        if event_id == 0:  # IFrameRequest
            parsed_event.update({"event": "IFrameRequest"})
        elif event_id == 1:  # RequestQualityControl
            parsed_event.update({"event": "RequestQualityControl"})
        elif event_id == 60:  # KeyDown (uint8 keyCode, uint8 isRepeat)
            if len(data) >= 3:
                keycode, is_repeat = struct.unpack("BB", data[1:3])
                parsed_event.update({"event": "KeyDown", "keycode": keycode, "is_repeat": is_repeat})
        elif event_id == 61:  # KeyUp (uint8 keyCode)
            if len(data) >= 2:
                keycode = data[1]
                parsed_event.update({"event": "KeyUp", "keycode": keycode})
        elif event_id == 62:  # KeyPress (uint16 charcode)
            if len(data) >= 3:
                charcode, = struct.unpack("H", data[1:3])
                parsed_event.update({"event": "KeyPress", "charcode": charcode})
        elif event_id == 70:  # MouseEnter (no payload)
            parsed_event.update({"event": "MouseEnter"})
        elif event_id == 71:  # MouseLeave (no payload)
            parsed_event.update({"event": "MouseLeave"})
        elif event_id == 72:  # MouseDown (uint8 button, uint16 x, uint16 y)
            if len(data) >= 5:
                button, x, y = struct.unpack("<BHH", data[1:6])
                parsed_event.update({"event": "MouseDown", "button": button, "x": x, "y": y})
        elif event_id == 73:  # MouseUp (uint8 button, uint16 x, uint16 y)
            if len(data) >= 5:
                button, x, y = struct.unpack("<BHH", data[1:6])
                parsed_event.update({"event": "MouseUp", "button": button, "x": x, "y": y})
        elif event_id == 74:  # MouseMove (uint16 x, uint16 y, int16 deltaX, int16 deltaY)
            if len(data) >= 9:
                x, y, delta_x, delta_y = struct.unpack("<HHhh", data[1:9])
                parsed_event.update({"event": "MouseMove", "x": x, "y": y, "delta_x": delta_x, "delta_y": delta_y})
        elif event_id == 75:  # MouseWheel (int16 delta, uint16 x, uint16 y)
            if len(data) >= 6:
                delta, x, y = struct.unpack("<hHH", data[1:7])
                parsed_event.update({"event": "MouseWheel", "delta": delta, "x": x, "y": y})
        elif event_id == 80:  # TouchStart (uint8 numTouches, uint16 x, uint16 y, uint8 idx, uint8 force, uint8 valid)
            if len(data) >= 8:
                num_touches, x, y, idx, force, valid = struct.unpack("<BHHBBB", data[1:9])
                parsed_event.update({"event": "TouchStart", "num_touches": num_touches, "x": x, "y": y, "idx": idx, "force": force, "valid": valid})
        elif event_id == 81:  # TouchEnd
            if len(data) >= 8:
                num_touches, x, y, idx, force, valid = struct.unpack("<BHHBBB", data[1:9])
                parsed_event.update({"event": "TouchEnd", "num_touches": num_touches, "x": x, "y": y, "idx": idx, "force": force, "valid": valid})
        elif event_id == 82:  # TouchMove
            if len(data) >= 8:
                num_touches, x, y, idx, force, valid = struct.unpack("<BHHBBB", data[1:9])
                parsed_event.update({"event": "TouchMove", "num_touches": num_touches, "x": x, "y": y, "idx": idx, "force": force, "valid": valid})
        elif event_id == 90:  # GamepadButtonPressed (uint8 controllerId, uint8 button, uint8 isRepeat)
            if len(data) >= 4:
                controller_id, button, is_repeat = struct.unpack("<BBB", data[1:4])
                parsed_event.update({"event": "GamepadButtonPressed", "controller_id": controller_id, "button": button, "is_repeat": is_repeat})
        elif event_id == 91:  # GamepadButtonReleased (uint8 controllerId, uint8 button, uint8 isRepeat)
            if len(data) >= 4:
                controller_id, button, is_repeat = struct.unpack("<BBB", data[1:4])
                parsed_event.update({"event": "GamepadButtonReleased", "controller_id": controller_id, "button": button, "is_repeat": is_repeat})
        elif event_id == 92:  # GamepadAnalog (uint8 controllerId, uint8 button, double analogValue)
            if len(data) >= 11:
                controller_id, button, analog_value = struct.unpack("<BBd", data[1:11])
                parsed_event.update({"event": "GamepadAnalog", "controller_id": controller_id, "button": button, "analog_value": analog_value})
        elif event_id == 94:  # GamepadDisconnected (uint8 controllerId)
            if len(data) >= 2:
                controller_id = data[1]
                parsed_event.update({"event": "GamepadDisconnected", "controller_id": controller_id})
        else:
            parsed_event.update({"event": "Unknown"})
    except struct.error as e:
        parsed_event.update({"error": "Failed to unpack data", "exception": str(e)})
    
    return parsed_event


# 連接至 Unreal Engine Pixel Streaming Signaling Server
peer_connection_options = None  # 儲存 peerConnectionOptions 設定
relay = MediaRelay()
peer_connections = {}  # 以 playerId 為 Key 存儲 WebRTC 連線
data_channels = {}  # 以 playerId 為 Key 存儲 DataChannel

FORMAT = pyaudio.paInt16  # s16 (16-bit PCM)
CHANNELS = 1  # 單聲道
SAMPLE_RATE = 8000  # 取樣率
CHUNK = 1024  # 每個音頻幀的大小


p = pyaudio.PyAudio()
stream = p.open(format=FORMAT, channels=CHANNELS, rate=SAMPLE_RATE, input=True, frames_per_buffer=CHUNK)

class VideoStreamTrack(MediaStreamTrack):
    kind = "video"

    def __init__(self, source):
        super().__init__()
        self.source = relay.subscribe(source.video)

    async def recv(self):
        frame = await self.source.recv()
        return frame

# 用來 **傳輸** 音訊流的 track
class AudioStreamTrack(MediaStreamTrack):
    kind = "audio"

    def __init__(self):
        super().__init__()

    async def recv(self):
        audio_data = stream.read(CHUNK, exception_on_overflow=False)
        audio_frame = AudioFrame(format="s16", layout="mono", samples=CHUNK)
        audio_frame.planes[0].update(audio_data)
        return audio_frame
# 設置 Video 和 Audio track
video_source = MediaPlayer("/dev/video0")  # 攝影機來源 (Linux)
audio_track = AudioStreamTrack()  # 自訂音訊 track
video_track = VideoStreamTrack(video_source)
# 用來 **傳輸** 影片流的 track
async def create_offer(player_id, ws,pc):
    global peer_connections, data_channels


    peer_connections[player_id] = pc  # 儲存 WebRTC 連線


    pc.addTrack(video_track)
    pc.addTrack(audio_track)
    channel = pc.createDataChannel("cirrus")
    data_channels[player_id] = channel

    @channel.on("open")
    def on_open():
        print(f"✅ [Player {player_id}] DataChannel cirrus 開啟")

    @channel.on("message")
    def on_message(message):
        print(f"📩 [Player {player_id}] 收到 cirrus 訊息: {message}")

        @channel.on("message")
        def on_message(message):
            if isinstance(message, bytes):
                event = parse_pixel_streaming_event(message)
                print(f"📩 [Player {player_id}] 收到事件: {event}")
            else:
                print(f"📩 [Player {player_id}] 收到文字訊息: {message}")

    @pc.on("iceconnectionstatechange")
    async def on_ice_connection_state_change():
        print(f"🔄 [Player {player_id}] ICE 連線狀態: {pc.iceConnectionState}")
        if pc.iceConnectionState == "connected":
            print(f"✅ [Player {player_id}] ICE 連線成功！")
        elif pc.iceConnectionState == "failed":
            print(f"❌ [Player {player_id}] ICE 連線失敗，可能需要重新建立連線")

    # 監聽 WebRTC 連線狀態變更
    @pc.on("connectionstatechange")
    async def on_connection_state_change():
        print(f"🔄 [Player {player_id}] WebRTC 連線狀態: {pc.connectionState}")
        if pc.connectionState == "connected":
            print(f"✅ [Player {player_id}] WebRTC 連線成功！")
        elif pc.connectionState == "failed":
            print(f"❌ [Player {player_id}] WebRTC 連線失敗")

    # 監聽 ICE 候選者並發送到 Signaling Server
    @pc.on("icecandidate")
    async def on_ice_candidate(event):
        if event:
            ice_message = {
                "type": "iceCandidate",
                "playerId": player_id,
                "candidate": {
                    "candidate": event.candidate,
                    "sdpMid": event.sdpMid,
                    "sdpMLineIndex": event.sdpMLineIndex
                }
            }
            await ws.send(json.dumps(ice_message))
            print(f"📤 [Player {player_id}] 傳送自身 ICE 候選者: {event.candidate}")

        # 當所有 ICE 候選者都已發送完成，回應 signaling server
        elif pc.iceGatheringState == "complete":
            ice_complete_message = {
                "type": "iceCandidateComplete",
                "playerId": player_id
            }
            await ws.send(json.dumps(ice_complete_message))
            print(f"✅ [Player {player_id}] ICE 候選者傳送完畢，通知 signaling server")

    # 產生 SDP Offer
    offer = await pc.createOffer()
    
    await pc.setLocalDescription(offer)

    # 傳送 SDP Offer
    offer_message = {
        "type": "offer",
        "playerId": player_id,
        "sdp": offer.sdp
    }
    await ws.send(json.dumps(offer_message))
    print(f"📤 已回應 SDP Offer 給 Player {player_id}")

def channel_log(channel, t, message):
    print("channel(%s) %s %s" % (channel.label, t, message))
def parse_ice_servers(raw_config):
    ice_servers = []
    for server in raw_config.get("iceServers", []):
        urls = server.get("urls")
        username = server.get("username")
        credential = server.get("credential")

        # aiortc 支援 urls 是 list 或 str
        ice_server = RTCIceServer(
            urls=urls,
            username=username,
            credential=credential
        )
        ice_servers.append(ice_server)
    return RTCConfiguration(iceServers=ice_servers)
# 處理 Signaling 交換
async def signaling():
    global peer_connection_options

    async with websockets.connect(SIGNALING_SERVER) as ws:
        print("✅ 已連接至 Pixel Streaming Signaling Server")

        while True:
            message = await ws.recv()
            data = json.loads(message)
            print(f"📩 收到信令訊息: {json.dumps(data, indent=2)}")

            if data.get("type") == "config":
                peer_connection_options = data.get("peerConnectionOptions", {})
                rtc_config = parse_ice_servers(peer_connection_options)
                pc = RTCPeerConnection(configuration=rtc_config)
                print(f"📝 儲存 peerConnectionOptions: {json.dumps(peer_connection_options, indent=2)}")

            elif data.get("type") == "identify":
                response = {"type": "endpointId", "id": "PythonStreamer"}
                await ws.send(json.dumps(response))
                print("📤 已回應 identify 訊息，註冊為 PythonStreamer")

            elif data.get("type") == "playerConnected":
                player_id = data["playerId"]
                print(f"🎮 玩家 {player_id} 已連接，建立 WebRTC 連線...")
                await create_offer(player_id, ws,pc)

            elif data.get("type") == "answer":
                player_id = data["playerId"]
                if player_id in peer_connections:
                    await peer_connections[player_id].setRemoteDescription(RTCSessionDescription(data["sdp"], "answer"))
                    print(f"🔄 [Player {player_id}] 設定 Remote Description 完成")

            elif data.get("type") == "iceCandidate":
                player_id = data["playerId"]
                if player_id in peer_connections:
                    candidate_info = data["candidate"]["candidate"].split()
                    rtc_candidate = RTCIceCandidate(
                        foundation=candidate_info[0].split(":")[1],
                        component=int(candidate_info[1]),
                        protocol=candidate_info[2].lower(),
                        priority=int(candidate_info[3]),
                        ip=candidate_info[4],
                        port=int(candidate_info[5]),
                        type=candidate_info[7],
                        sdpMid=data["candidate"]["sdpMid"],
                        sdpMLineIndex=data["candidate"]["sdpMLineIndex"],

                    )

                    await peer_connections[player_id].addIceCandidate(rtc_candidate)
                    print(f"❄️ [Player {player_id}] 加入 ICE 候選者: {rtc_candidate}")

# 主程式
async def main():
    await signaling()

# 執行主程式
asyncio.run(main())
