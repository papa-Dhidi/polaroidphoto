from flask import Flask, render_template, request, send_file
import os
import base64
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageOps
import io
import numpy as np  # Untuk bantu deteksi lubang transparan

app = Flask(__name__, static_folder='static')

# Buat direktori simpan
desktop = Path.home() / "Desktop"
save_dir = desktop / "photoboott" / "image"
save_dir.mkdir(parents=True, exist_ok=True)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/save-photo", methods=["POST"])
def save_photo():
    try:
        data = request.json.get("image")
        frame_name = request.json.get("frame")
        image_data = data.split(",")[1]
        frame_path = Path("static/frames") / frame_name

        # Decode gambar base64 dari frontend
        img_bytes = base64.b64decode(image_data)
        user_img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")

        # Buka frame PNG transparan
        frame_img = Image.open(frame_path).convert("RGBA")
        frame_width, frame_height = frame_img.size

        # Target canvas akhir (misalnya untuk polaroid): 1080 x 1440
        target_width, target_height = 1080, 1440
        frame_img = frame_img.resize((target_width, target_height), Image.LANCZOS)

        # Deteksi lubang dari channel alpha dengan NumPy
        alpha = frame_img.getchannel("A")
        alpha_data = np.array(alpha)
        transparent_mask = alpha_data == 0

        ys, xs = np.where(transparent_mask)
        if len(xs) == 0 or len(ys) == 0:
            return "❌ Tidak ditemukan area transparan pada frame.", 400

        # Hitung koordinat lubang pada versi yang sudah di-resize
        hole_x, hole_y = xs.min(), ys.min()
        hole_r, hole_b = xs.max(), ys.max()
        hole_w = hole_r - hole_x
        hole_h = hole_b - hole_y

        # Resize dan crop otomatis agar gambar benar-benar menutupi lubang (tanpa celah)
        user_img_fitted = ImageOps.fit(user_img, (hole_w, hole_h), method=Image.LANCZOS, centering=(0.5, 0.5))

        # Tempelkan ke dalam lubang
        base = Image.new("RGBA", (target_width, target_height), (255, 255, 255, 255))
        base.paste(user_img_fitted, (hole_x, hole_y))

        # Gabungkan dengan frame
        final = Image.alpha_composite(base, frame_img)

        # Simpan ke buffer dan ke folder
        output = io.BytesIO()
        final.save(output, format="PNG")
        output.seek(0)

        filename = f"photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        full_path = save_dir / filename
        final.save(full_path)

        return send_file(output, mimetype="image/png")

    except Exception as e:
        return f"❌ Error: {e}", 500

if __name__ == "__main__":
    app.run(debug=True)
