from flask import Flask, render_template, request, send_file, flash, redirect, url_for
import os
import tempfile
from io import BytesIO
from werkzeug.utils import secure_filename
from PIL import Image
import numpy as np
try:
    import cv2
    HAS_BG_REMOVAL = True
except ImportError:
    HAS_BG_REMOVAL = False

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
        if remove_bg and not HAS_BG_REMOVAL:
            return {'error': 'Background removal feature is not available. Please try again later.'}, 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
            file.save(temp_file.name)
            temp_input = temp_file.name
        
        # Convert image using PIL
        img = Image.open(temp_input)
        
        # Remove background if requested using advanced morphological operations
        if remove_bg:
            try:
                # Convert PIL Image to OpenCV format
                cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                
                # Convert to HSV for better color detection
                hsv = cv2.cvtColor(cv_img, cv2.COLOR_BGR2HSV)
                
                # Create initial mask using GrabCut for better results
                mask = np.zeros(cv_img.shape[:2], np.uint8)
                bgd_model = np.zeros((1, 65), np.float64)
                fgd_model = np.zeros((1, 65), np.float64)
                
                h, w = cv_img.shape[:2]
                rect = (5, 5, w - 5, h - 5)
                
                # Apply GrabCut with more iterations
                cv2.grabCut(cv_img, mask, rect, bgd_model, fgd_model, 10, cv2.GC_INIT_WITH_RECT)
                
                # Refine mask with morphological operations
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')
                
                # Apply morphological closing to fill holes
                mask2 = cv2.morphologyEx(mask2, cv2.MORPH_CLOSE, kernel, iterations=2)
                # Apply morphological opening to remove noise
                mask2 = cv2.morphologyEx(mask2, cv2.MORPH_OPEN, kernel, iterations=1)
                
                # Apply Gaussian blur to smooth edges
                mask2 = cv2.GaussianBlur(mask2, (5, 5), 0)
                
                # Convert mask to alpha channel (0-255)
                alpha = (mask2 * 255).astype('uint8')
                
                # Convert to PIL RGBA
                img_rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
                img_pil = Image.fromarray(img_rgb).convert('RGBA')
                
                # Apply alpha channel
                img_pil.putalpha(Image.fromarray(alpha))
                img = img_pil
                
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
