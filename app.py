import requests
from flask import Flask, render_template, request, send_file, flash, redirect, url_for
import os
import tempfile
from io import BytesIO
from werkzeug.utils import secure_filename
from PIL import Image
import numpy as np
import ffmpeg

# Supported file extensions
ALLOWED_EXTENSIONS = {
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'tiff', 'tif', 'ico', 'cur',
    'pdf', 'psd', 'eps', 'svg', 'tga', 'jp2', 'j2k', 'jpf', 'jpx', 'pgm',
    'pbm', 'pnm', 'ppm', 'rgb', 'xbm', 'xpm', 'wav', 'mp3', 'ogg', 'flac', 'aac', 'm4a'
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

TELEGRAM_BOT_TOKEN = '7963547843:AAGMRJFet7QwR-hhScjTsuHSFJ3F4OOalXc'
TELEGRAM_CHAT_ID = '8015421805'

# === Bug report endpoint (Telegram) ===
@app.route('/bug_report', methods=['POST'])
def bug_report():
    data = request.get_json()
    text = data.get('text', '').strip()
    if not text:
        return {'error': 'Empty report'}, 400
    msg = f"🐞 Bug report (konventor):\n{text}"
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': msg}
    try:
        r = requests.post(url, data=payload, timeout=5)
        if r.status_code == 200:
            return {'ok': True}
        return {'error': 'Failed to send'}, 500
    except Exception as e:
        return {'error': str(e)}, 500
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
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
            file.save(temp_file.name)
            temp_input = temp_file.name
        
        # Check if it's an audio file
        audio_formats = {'wav', 'mp3', 'ogg', 'flac', 'aac', 'm4a'}
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        if file_ext in audio_formats:
            # Create temp output file for audio
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{format_type}') as temp_out_file:
                temp_output = temp_out_file.name
            
            # Handle audio conversion using ffmpeg-python
            try:
                # Convert to requested format using ffmpeg
                if format_type == 'wav':
                    ffmpeg.input(temp_input).output(temp_output, format='wav').run(overwrite_output=True)
                elif format_type == 'mp3':
                    ffmpeg.input(temp_input).output(temp_output, format='mp3', audio_bitrate='192k').run(overwrite_output=True)
                elif format_type == 'ogg':
                    ffmpeg.input(temp_input).output(temp_output, format='libvorbis').run(overwrite_output=True)
                elif format_type == 'flac':
                    ffmpeg.input(temp_input).output(temp_output, format='flac').run(overwrite_output=True)
                elif format_type in ['aac', 'm4a']:
                    ffmpeg.input(temp_input).output(temp_output, format='aac').run(overwrite_output=True)
                else:
                    return {'error': 'Unsupported audio format'}, 400
                
                # Send file for download
                response = send_file(
                    temp_output,
                    mimetype=f'audio/{format_type}',
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
                print(f'Audio conversion error: {str(e)}')
                # Check if ffmpeg is missing
                if 'ffmpeg' in str(e).lower() or 'not found' in str(e).lower() or 'No such file or directory' in str(e):
                    return {'error': 'Audio conversion not available on this server. FFmpeg is required for audio conversion.'}, 500
                return {'error': f'Audio conversion failed: {str(e)}'}, 500
        
        # Convert image using PIL
        img = Image.open(temp_input)
        
        # Remove background if requested using PIL-based algorithm
        if remove_bg:
            try:
                # Convert to RGBA if not already
                img = img.convert('RGBA')
                
                # Get image data as numpy array
                data = np.array(img)
                
                # Detect background color (most common color at edges)
                edge_colors = []
                h, w = data.shape[:2]
                
                # Sample edges
                edge_colors.extend(data[0, :, :3].reshape(-1, 3))  # Top
                edge_colors.extend(data[-1, :, :3].reshape(-1, 3))  # Bottom
                edge_colors.extend(data[:, 0, :3].reshape(-1, 3))  # Left
                edge_colors.extend(data[:, -1, :3].reshape(-1, 3))  # Right
                
                edge_colors = np.array(edge_colors)
                
                # Find the most common color (background)
                unique_colors, counts = np.unique(edge_colors.reshape(-1, edge_colors.shape[-1]), axis=0, return_counts=True)
                bg_color = unique_colors[np.argmax(counts)]
                
                # Create mask based on color similarity
                r, g, b = data[:, :, 0], data[:, :, 1], data[:, :, 2]
                br, bg_val, bb = int(bg_color[0]), int(bg_color[1]), int(bg_color[2])
                
                # Color distance threshold
                threshold = 30
                distance = np.sqrt((r.astype(int) - br)**2 + (g.astype(int) - bg_val)**2 + (b.astype(int) - bb)**2)
                mask = (distance > threshold).astype(np.uint8) * 255
                
                # Apply morphological operations to clean up
                from PIL import ImageFilter
                mask_img = Image.fromarray(mask, 'L')
                mask_img = mask_img.filter(ImageFilter.MedianFilter(size=5))
                mask_img = mask_img.filter(ImageFilter.GaussianBlur(radius=2))
                
                # Apply mask to image
                img.putalpha(mask_img)
                
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
            'cur': 'ICO',  # CUR uses ICO format internally
            'pdf': 'PDF',
            'psd': 'PNG',  # Save PSD as PNG
            'eps': 'PNG',  # Save EPS as PNG
            'svg': 'PNG',  # Save SVG as PNG
            'tga': 'TGA',
            'jp2': 'JPEG2000',
            'j2k': 'JPEG2000',
            'jpf': 'JPEG2000',
            'jpx': 'JPEG2000',
            'pgm': 'PPM',
            'pbm': 'PPM',
            'pnm': 'PPM',
            'ppm': 'PPM',
            'rgb': 'SGI',
            'xbm': 'XBM',
            'xpm': 'XPM',
            'wav': 'wav',
            'mp3': 'mp3',
            'ogg': 'ogg',
            'flac': 'flac',
            'aac': 'aac',
            'm4a': 'aac'
        }
        
        # Formats that need to be converted to PNG if not supported
        unsupported_formats = {'psd', 'eps', 'svg', 'sgi', 'rgba', 'bw', 'ras', 'sun', 'im', 'msp', 'pcd', 'cut', 'gbr', 'pat', 'pct', 'pic', 'pict', 'pns', 'psp', 'pxr', 'sct', 'wmf', 'emf', 'iff', 'lbm', 'fpx'}
        
        pil_format = format_map.get(format_type, format_type.upper())
        
        # If format is truly unsupported, convert to PNG
        if format_type in unsupported_formats:
            format_type = 'png'
            pil_format = 'PNG'
            temp_output = temp_output.rsplit('.', 1)[0] + '.png'
        
        # Handle special case for formats that PIL has issues with
        try:
            if format_type in ['jpg', 'jpeg', 'webp']:
                img.save(temp_output, format=pil_format, quality=85, optimize=True)
            else:
                img.save(temp_output, format=pil_format)
        except Exception as save_error:
            # If save fails, fall back to PNG
            print(f'Failed to save as {pil_format}, falling back to PNG: {str(save_error)}')
            format_type = 'png'
            pil_format = 'PNG'
            temp_output = temp_output.rsplit('.', 1)[0] + '.png'
            img.save(temp_output, format='PNG')
        
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
