from flask import Flask, render_template, request, send_file, flash, redirect, url_for
import os
import tempfile
from werkzeug.utils import secure_filename

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
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
            file.save(temp_file.name)
            temp_input = temp_file.name
        
        # Convert image using PIL
        from PIL import Image
        img = Image.open(temp_input)
        
        # Convert RGBA to RGB if needed for formats that don't support alpha
        if format_type in ['jpg', 'jpeg', 'bmp'] and img.mode in ('RGBA', 'LA', 'P'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = rgb_img
        
        # Save converted file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{format_type}') as temp_out_file:
            temp_output = temp_out_file.name
        
        # Set quality for optimized formats
        if format_type in ['jpg', 'jpeg', 'webp']:
            img.save(temp_output, format=format_type.upper() if format_type != 'jpg' else 'JPEG', quality=85, optimize=True)
        else:
            img.save(temp_output, format=format_type.upper())
        
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
