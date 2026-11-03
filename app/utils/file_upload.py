import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app
from PIL import Image

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'webp'}

# Maximum file size (16MB)
MAX_FILE_SIZE = 16 * 1024 * 1024

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_type(file_path):
    """Get MIME type of file"""
    try:
        # Simple file type detection based on extension
        ext = os.path.splitext(file_path)[1].lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.pdf': 'application/pdf'
        }
        return mime_types.get(ext, 'application/octet-stream')
    except:
        return 'application/octet-stream'

def validate_image(file_path):
    """Validate if file is a valid image"""
    try:
        with Image.open(file_path) as img:
            img.verify()
        return True
    except:
        return False

def resize_image(file_path, max_width=800, max_height=600):
    """Resize image while maintaining aspect ratio"""
    try:
        with Image.open(file_path) as img:
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # Calculate new dimensions
            width, height = img.size
            if width > max_width or height > max_height:
                ratio = min(max_width/width, max_height/height)
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Save resized image
            img.save(file_path, 'JPEG', quality=85, optimize=True)
        return True
    except Exception as e:
        print(f"Error resizing image: {e}")
        return False

def save_uploaded_file(file, upload_folder, subfolder=''):
    """
    Save uploaded file to specified folder
    Returns: (success, file_path, error_message)
    """
    try:
        if not file or not file.filename:
            return False, None, "No file selected"
        
        # Check file size
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > MAX_FILE_SIZE:
            return False, None, f"File size exceeds {MAX_FILE_SIZE // (1024*1024)}MB limit"
        
        # Check file extension
        if not allowed_file(file.filename):
            return False, None, f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        
        # Generate unique filename
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_filename = f"{uuid.uuid4().hex}{ext}"
        
        # Create upload directory
        private_subfolders = {
            'cnic', 'degrees', 'payment_screenshots', 'medical_documents',
            'live_photos', 'prescriptions', 'refund_proofs', 'payout_proofs'
        }
        actual_subfolder = subfolder
        if not actual_subfolder:
            cand = str(upload_folder).strip().rstrip('/\\')
            if cand in private_subfolders or cand in {'profile_pictures', 'blog_covers', 'qa_photos'}:
                actual_subfolder = cand
            elif not os.path.isabs(cand) and not cand.startswith(('app/', 'static/')):
                actual_subfolder = cand

        is_private = actual_subfolder in private_subfolders or (subfolder in private_subfolders)
        if is_private:
            base_folder = current_app.config.get('PRIVATE_UPLOAD_FOLDER', os.path.join(current_app.instance_path, 'private_uploads'))
        else:
            base_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join(current_app.root_path, 'static', 'uploads'))
        upload_path = os.path.join(base_folder, actual_subfolder) if actual_subfolder else base_folder
        os.makedirs(upload_path, exist_ok=True)
        
        # Save file
        file_path = os.path.join(upload_path, unique_filename)
        file.save(file_path)
        
        # Validate and resize if it's an image
        file_type = get_file_type(file_path)
        if file_type.startswith('image/'):
            if not validate_image(file_path):
                os.remove(file_path)
                return False, None, "Invalid image file"
            
            # Resize image
            resize_image(file_path)
        
        # Return relative path for database storage
        relative_path = os.path.join(actual_subfolder, unique_filename).replace('\\', '/') if actual_subfolder else unique_filename
        return True, relative_path, None
        
    except Exception as e:
        return False, None, f"Error uploading file: {str(e)}"

def delete_uploaded_file(file_path):
    """Delete uploaded file"""
    try:
        if file_path:
            clean = file_path.replace('\\', '/')
            private_base = current_app.config.get('PRIVATE_UPLOAD_FOLDER', os.path.join(current_app.instance_path, 'private_uploads'))
            priv_path = os.path.join(private_base, clean)
            if os.path.exists(priv_path):
                os.remove(priv_path)
                return True
            full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], clean)
            if os.path.exists(full_path):
                os.remove(full_path)
                return True
    except Exception as e:
        print(f"Error deleting file: {e}")
    return False

def get_file_url(file_path):
    """Get URL for uploaded file"""
    if file_path:
        return f"/static/uploads/{file_path}"
    return None
