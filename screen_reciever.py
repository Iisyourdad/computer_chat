import socket
import struct
import sys
import threading
import time
from io import BytesIO

import tkinter as tk
from PIL import Image, ImageTk

SENDER_IP = "10.247.248.102"  # Change this to the sender's IP if not provided on the command line
PORT = 50008


def recv_exact(conn: socket.socket, n: int) -> bytes | None:
    """Read exactly n bytes or return None if the connection is closed."""
    data = bytearray()
    while len(data) < n:
        chunk = conn.recv(n - len(data))
        if not chunk:
            return None
        data.extend(chunk)
    return bytes(data)


def stream_frames(host: str, on_frame):
    with socket.create_connection((host, PORT), timeout=10) as conn:
        conn.settimeout(5)
        while True:
            length_bytes = recv_exact(conn, 4)
            if not length_bytes:
                break
            frame_len = struct.unpack("!I", length_bytes)[0]
            frame_bytes = recv_exact(conn, frame_len)
            if not frame_bytes:
                break
            on_frame(frame_bytes)


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else SENDER_IP

    root = tk.Tk()
    root.title(f"Screen receiver from {host}")
    root.configure(bg="black")
    root.resizable(True, True)

    top_label = tk.Label(
        root,
        text=f"Source: {host}:{PORT}",
        font=("Segoe UI", 12, "bold"),
        bg="black",
        fg="#33ff99",
        anchor="w",
        padx=8,
        pady=4,
    )
    top_label.pack(fill="x")

    image_label = tk.Label(root, bg="black")
    image_label.pack(fill="both", expand=True)

    stop_event = threading.Event()
    latest_img = None
    initial_geometry_set = False

    def render_to_label():
        nonlocal latest_img, initial_geometry_set
        if latest_img is None:
            return
        target_w, target_h = latest_img.size
        avail_w = max(1, image_label.winfo_width())
        avail_h = max(1, image_label.winfo_height())
        scale = min(avail_w / target_w, avail_h / target_h)
        scaled_w = max(1, int(target_w * scale))
        scaled_h = max(1, int(target_h * scale))
        if (scaled_w, scaled_h) != latest_img.size:
            disp = latest_img.resize((scaled_w, scaled_h), Image.LANCZOS)
        else:
            disp = latest_img
        photo = ImageTk.PhotoImage(disp)
        image_label.configure(image=photo)
        image_label.image = photo
        if not initial_geometry_set:
            root.geometry(f"{target_w}x{target_h}")
            initial_geometry_set = True

    def on_resize(event):
        render_to_label()

    def update_frame(frame_bytes: bytes):
        nonlocal latest_img
        try:
            img = Image.open(BytesIO(frame_bytes)).convert("RGB")
        except Exception:
            return
        latest_img = img
        render_to_label()

    def network_worker():
        while not stop_event.is_set():
            try:
                stream_frames(host, lambda fb: root.after_idle(update_frame, fb))
            except Exception:
                time.sleep(1)
            else:
                time.sleep(1)

    thread = threading.Thread(target=network_worker, daemon=True)
    thread.start()
    image_label.bind("<Configure>", on_resize)

    def on_close():
        stop_event.set()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
