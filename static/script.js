document.addEventListener('DOMContentLoaded', function() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const browseBtn = document.getElementById('browseBtn');
    const previewContainer = document.getElementById('previewContainer');
    const previewImage = document.getElementById('previewImage');
    const fileName = document.getElementById('fileName');
    const convertForm = document.getElementById('convertForm');
    const convertBtn = document.getElementById('convertBtn');
    const loadingSpinner = document.getElementById('loadingSpinner');

    // File input handlers
    browseBtn.addEventListener('click', () => fileInput.click());
    
    fileInput.addEventListener('change', handleFileSelect);

    // Drag and drop handlers
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            handleFileSelect({ target: { files } });
        }
    });

    // Format selection handlers
    const formatOptions = document.querySelectorAll('input[name="format"]');
    formatOptions.forEach(option => {
        option.addEventListener('change', checkFormValidity);
    });

    // Form submission with retry logic
    convertForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        if (validateForm()) {
            showLoading();
            
            // Create form data for AJAX submission
            const formData = new FormData(convertForm);
            
            // Submit with retry logic
            submitWithRetry(formData, 0);
        }
    });
    
    function submitWithRetry(formData, retryCount) {
        const maxRetries = 3;
        // Increase timeout for background removal (5 minutes max)
        const hasRemoveBg = formData.get('remove_background') === 'on';
        const timeout = hasRemoveBg ? 300000 : (isMobile() ? 90000 : 30000); // 5min for BG removal, 90s for mobile, 30s for desktop
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);
        
        fetch('/convert', {
            method: 'POST',
            body: formData,
            signal: controller.signal
        })
        .then(response => {
            clearTimeout(timeoutId);
            
            if (response.ok) {
                return response.blob();
            } else if (response.status >= 500 && retryCount < maxRetries) {
                // Retry on server errors
                throw new Error('SERVER_ERROR_RETRY');
            } else {
                throw new Error('Conversion failed');
            }
        })
        .then(blob => {
            // Get filename from response or create one
            const originalFile = fileInput.files[0];
            const format = document.querySelector('input[name="format"]:checked').value;
            const nameWithoutExt = originalFile.name.split('.').slice(0, -1).join('.');
            const filename = `${nameWithoutExt}.${format}`;
            
            // Create download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            // Hide loading and reset form
            hideLoading();
            resetForm();
            
            // Show success message
            showSuccessMessage('Изображение успешно конвертировано!');
        })
        .catch(error => {
            clearTimeout(timeoutId);
            
            if (error.message === 'SERVER_ERROR_RETRY' && retryCount < maxRetries) {
                console.log(`Retry attempt ${retryCount + 1}/${maxRetries}`);
                setTimeout(() => submitWithRetry(formData, retryCount + 1), 2000);
            } else {
                console.error('Error:', error);
                hideLoading();
                
                if (error.name === 'AbortError') {
                    alert('Истекло время ожидания. Проверьте размер файла и интернет-соединение.');
                } else {
                    alert('Ошибка при конвертации изображения. Пожалуйста, попробуйте снова.');
                }
            }
        });
    }

    function handleFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            // Validate file type
            const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp', 'image/tiff'];
            if (!validTypes.includes(file.type) && !file.type.startsWith('image/')) {
                alert('Пожалуйста, загрузьте валидное изображение');
                resetPreview();
                return;
            }
            
            // Check file size before processing
            const maxSize = isMobile() ? 5 * 1024 * 1024 : 16 * 1024 * 1024;
            if (file.size > maxSize) {
                alert(`Файл слишком большой. Максимум ${maxSize / (1024 * 1024)}MB`);
                resetPreview();
                return;
            }
            
            const reader = new FileReader();
            
            reader.onload = function(e) {
                previewImage.src = e.target.result;
                fileName.textContent = file.name + ' (' + (file.size / 1024).toFixed(2) + ' KB)';
                previewContainer.classList.remove('hidden');
                checkFormValidity();
            };
            
            reader.onerror = function() {
                alert('Ошибка при чтении файла');
                resetPreview();
            };
            
            reader.readAsDataURL(file);
        } else {
            resetPreview();
        }
    }

    function checkFormValidity() {
        const fileSelected = fileInput.files.length > 0;
        const formatSelected = document.querySelector('input[name="format"]:checked') !== null;
        
        convertBtn.disabled = !(fileSelected && formatSelected);
    }

    function validateForm() {
        const file = fileInput.files[0];
        const format = document.querySelector('input[name="format"]:checked');
        
        if (!file) {
            alert('Пожалуйста, выберите файл');
            return false;
        }
        
        if (!format) {
            alert('Пожалуйста, выберите формат для конвертации');
            return false;
        }
        
        // Different limits for mobile and desktop
        const maxSize = isMobile() ? 5 * 1024 * 1024 : 16 * 1024 * 1024; // 5MB mobile, 16MB desktop
        
        if (file.size > maxSize) {
            const maxMB = maxSize / (1024 * 1024);
            alert(`Размер файла не должен превышать ${maxMB}MB. На мобильных устройствах максимум 5MB.`);
            return false;
        }
        
        return true;
    }
    
    function isMobile() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    }

    function showLoading() {
        convertBtn.style.display = 'none';
        loadingSpinner.classList.remove('hidden');
    }

    function hideLoading() {
        convertBtn.style.display = 'inline-flex';
        loadingSpinner.classList.add('hidden');
    }

    function resetForm() {
        fileInput.value = '';
        resetPreview();
        
        // Reset format selection
        const formatOptions = document.querySelectorAll('input[name="format"]');
        formatOptions.forEach(option => {
            option.checked = false;
        });
        
        checkFormValidity();
    }

    function showSuccessMessage(message) {
        // Create success alert
        const successDiv = document.createElement('div');
        successDiv.className = 'bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-6 mt-4';
        successDiv.textContent = message;
        
        // Insert after form
        convertForm.parentNode.insertBefore(successDiv, convertForm.nextSibling);
        
        // Remove after 3 seconds
        setTimeout(() => {
            successDiv.remove();
        }, 3000);
    }

    function resetPreview() {
        previewContainer.classList.add('hidden');
        previewImage.src = '';
        fileName.textContent = '';
        convertBtn.disabled = true;
    }

    // Initialize
    checkFormValidity();
});
