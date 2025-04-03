# 📹 Pixel Streaming from Webcam (Python)

This is a minimal example for sending webcam video/audio from the browser to an Unreal Engine Pixel Streaming setup using Python and WebRTC.

---

## 🧪 How to Try It — Step by Step

1. ✅ **Install Node.js**  
   You’ll need Node.js to run the Pixel Streaming Signalling Server.  
   Download it from: [https://nodejs.org](https://nodejs.org)

2. ✅ **Run the Pixel Streaming Signalling Server**  
   Navigate to the Pixel Streaming infrastructure folder, and launch the local signaling server:

   ```bash
   cd PixelStreamingInfrastructure-UE5.3/SignallingWebServer/platform_scripts/bash
   ./run_local.sh
   ```

3. ✅ **Install Python dependencies**  
   Make sure you have Python 3.8+ installed. Then install the required packages:

   ```bash
   pip install websockets aiortc pyaudio
   ```

4. ✅ **Start the webcam streamer**  
   Run the script that captures your webcam and sends the stream to Pixel Streaming:

   ```bash
   python pixel_straming_from_webcam.py
   ```

5. ✅ **Open your browser**  
   Go to the Pixel Streaming frontend (default address):

   ```
   http://localhost
   ```

   You should now see your webcam stream being sent into the Pixel Streaming session!

---

