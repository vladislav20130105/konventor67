from flask import Flask, render_template, request, send_file, flash, redirect, url_for
import os
import tempfile
from io import BytesIO
from werkzeug.utils import secure_filename
from PIL import Image
try:
    from rembg import remove
    HAS_REMBG = True
except ImportError:
    HAS_REMBG = False

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

ALLOWED_EXTENSIONS = {
    'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'tif', 'webp', 'ico', 'cur',
    'ppm', 'pgm', 'pbm', 'pnm', 'psd', 'eps', 'pdf', 'svg', 'tga', 
    'jp2', 'j2k', 'jpf', 'jpx', 'pcx', 'dib', 'fpx', 'iff', 'lbm', 
    'sgi', 'rgb', 'rgba', 'bw', 'ras', 'sun', 'xbm', 'xpm', 'im', 
    'msp', 'pcd', 'cut', 'gbr', 'pat', 'pct', 'pic', 'pict', 
    'png', 'pns', 'psp', 'pxr', 'sct', 'tga', 'tif', 'wmf', 'emf'
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_image():
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return {'error': 'No file provided'}, 400
        
        file = request.files['file']
        if file.filename == '':
            return {'error': 'No file selected'}, 400
        
        if not allowed_file(file.filename):
            return {'error': 'File type not allowed'}, 400
        
        # Get requested format
        format_type = request.form.get('format', '').lower()
        if not format_type or format_type not in ALLOWED_EXTENSIONS:
            return {'error': 'Invalid format'}, 400
        
        # Check if background removal is requested
        remove_bg = request.form.get('remove_background') == 'on'
        if remove_bg and not HAS_REMBG:
            return {'error': 'Background removal feature is not available. Please try again later.'}, 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
            file.save(temp_file.name)
            temp_input = temp_file.name
        
        # Convert image using PIL
        img = Image.open(temp_input)
        
        # Remove background if requested
        if remove_bg:
            try:
                # Remove background - rembg returns PNG bytes
                with open(temp_input, 'rb') as f:
                    img_data = f.read()
                img_no_bg_bytes = remove(img_data)
                # Convert bytes to PIL Image
                img = Image.open(BytesIO(img_no_bg_bytes))
                img.load()  # Force load to prevent file handle issues
                # Force format to PNG for transparency
                format_type = 'png'
            except Exception as e:
                print(f'Background removal error: {str(e)}')
                return {'error': f'Failed to remove background: {str(e)}'}, 500
        
        # Convert RGBA to RGB if needed for formats that don't support alpha
        if format_type in ['jpg', 'jpeg', 'bmp']:
            if img.mode == 'RGBA':
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[3])  # Use alpha channel
                img = rgb_img
            elif img.mode == 'LA':
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img.convert('RGB'), mask=img.split()[1])  # Use alpha channel
                img = rgb_img
            elif img.mode == 'P':
                # Palette mode - convert to RGB
                if 'transparency' in img.info:
                    img = img.convert('RGBA')
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    rgb_img.paste(img, mask=img.split()[3])
                    img = rgb_img
                else:
                    img = img.convert('RGB')
            elif img.mode not in ('RGB', 'L'):
                # Convert any other mode to RGB
                img = img.convert('RGB')
        
        # Save converted file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{format_type}') as temp_out_file:
            temp_output = temp_out_file.name
        
        # Map format to PIL format name
        format_map = {
            'jpg': 'JPEG',
            'jpeg': 'JPEG',
            'png': 'PNG',
            'gif': 'GIF',
            'bmp': 'BMP',
            'webp': 'WebP',
            'tiff': 'TIFF',
            'tif': 'TIFF',
            'ico': 'ICO',
            'pdf': 'PDF',
        }
        
        pil_format = format_map.get(format_type, format_type.upper())
        
        # Set quality for optimized formats
        if format_type in ['jpg', 'jpeg', 'webp']:
            img.save(temp_output, format=pil_format, quality=85, optimize=True)
        else:
            img.save(temp_output, format=pil_format)
        
        # Send file for download
        response = send_file(
            temp_output,
            mimetype=f'image/{format_type}',
            as_attachment=True,
            download_name=f'converted.{format_type}'
        )
        
        # Clean up temp files
        try:
            os.remove(temp_input)
            os.remove(temp_output)
        except:
            pass
        
        return response
    
    except Exception as e:
        print(f'Conversion error: {str(e)}')
        return {'error': f'Conversion failed: {str(e)}'}, 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
