from flask import Flask, request, render_template, send_file
import os
from PIL import Image
import io

def get_size_format(b, factor=1024, suffix="B"):
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if b < factor:
            return f"{b:.2f}{unit}{suffix}"
        b /= factor
    return f"{b:.2f}Y{suffix}"

def compress_img(img_stream, new_size_ratio=1.0, quality=95, width=None, height=None, output_format="webp"):
    img = Image.open(img_stream)
    if new_size_ratio < 1.0:
        img = img.resize((int(img.size[0] * new_size_ratio), int(img.size[1] * new_size_ratio)), Image.Resampling.LANCZOS)
    elif width and height:
        img = img.resize((width, height), Image.Resampling.LANCZOS)
    elif width:
        w_percent = (width / float(img.size[0]))
        h_size = int((float(img.size[1]) * float(w_percent)))
        img = img.resize((width, h_size), Image.Resampling.LANCZOS)
    output = io.BytesIO()
    if output_format.lower() == "jpg" or output_format.lower() == "jpeg":
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")  # JPEG does not support transparency
        img.save(output, format="JPEG", quality=quality, optimize=True)
    elif output_format.lower() == "webp":
        if img.mode in ("P", "LA") or (img.mode == "RGBA"):
            img = img.convert("RGBA")
        img.save(output, format="WEBP", quality=quality, optimize=True)
    elif output_format.lower() == "png":
        img.save(output, format="PNG", quality=quality, optimize=True)
    else:
        img.save(output, format=img.format, quality=quality, optimize=True)
    output.seek(0)
    return output

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    note = "WebP and PNG preserve transparency (invisible backgrounds). JPEG does NOT preserve transparency; transparent areas become solid."
    estimated_sizes = None
    if request.method == 'POST':
        files = request.files.getlist('image')
        quality = int(request.form.get('quality', 80))
        width = int(request.form.get('width', 670))
        fmt = request.form.get('format', 'webp')
        if len(files) == 1:
            file = files[0]
            img_bytes = file.read()
            sizes = {}
            for f in ['webp', 'png', 'jpeg']:
                out = compress_img(io.BytesIO(img_bytes), quality=quality, width=width, output_format=f)
                sizes[f] = len(out.getvalue())
            estimated_sizes = {k: get_size_format(v) for k, v in sizes.items()}
            compressed = compress_img(io.BytesIO(img_bytes), quality=quality, width=width, output_format=fmt)
            return send_file(compressed, download_name=f"compressed.{fmt}", as_attachment=True)
        else:
            import zipfile
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in files:
                    filename = file.filename
                    img_bytes = file.read()
                    compressed = compress_img(io.BytesIO(img_bytes), quality=quality, width=width, output_format=fmt)
                    ext = fmt if fmt != 'jpeg' else 'jpg'
                    zipf.writestr(f"{os.path.splitext(filename)[0]}_compressed.{ext}", compressed.getvalue())
            zip_buffer.seek(0)
            return send_file(zip_buffer, download_name="compressed_images.zip", as_attachment=True)
    return render_template('index.html', note=note, estimated_sizes=estimated_sizes)

if __name__ == '__main__':
    app.run(debug=True)
