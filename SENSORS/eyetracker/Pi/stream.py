# This script is intended to run on the Raspberry Pi.
# Save it on the Raspberry Pi (e.g. /home/user/stream.py) and execute it there.
# The MJPEG video stream will be available from another device on the same network.

from flask import Flask, Response
from picamera2 import Picamera2
import cv2

app = Flask(__name__)

picam2 = Picamera2()

config = picam2.create_video_configuration(
    main={"size": (1280, 720), "format": "RGB888"},
    controls={"FrameRate": 30}
)

picam2.configure(config)
picam2.start()


def generate():
    while True:
        frame = picam2.capture_array()

        _, jpeg = cv2.imencode(
            ".jpg",
            frame,
            [cv2.IMWRITE_JPEG_QUALITY, 85]
        )

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n'
            + jpeg.tobytes() +
            b'\r\n'
        )


@app.route("/")
def index():
    return """
    <html>
        <body style="margin:0;background:black">
            <img src="/video" width="100%">
        </body>
    </html>
    """


@app.route("/video")
def video():
    return Response(
        generate(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


app.run(host="0.0.0.0", port=5000, threaded=True)
