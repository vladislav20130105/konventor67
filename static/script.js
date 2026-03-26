document.addEventListener('DOMContentLoaded', function() {
        // Tooltip for eraser icon (desktop only)
        const eraserIcon = document.getElementById('eraserIcon');
        if (eraserIcon) {
            // Show tooltip only on desktop
            eraserIcon.addEventListener('mouseenter', function() {
                if (window.innerWidth > 1024) {
                    eraserIcon.setAttribute('title', 'Удалить фон');
                } else {
                    eraserIcon.removeAttribute('title');
                }
            });
            // Remove tooltip on mouseleave for mobile
            eraserIcon.addEventListener('mouseleave', function() {
                if (window.innerWidth <= 1024) {
                    eraserIcon.removeAttribute('title');
                }
            });
        }
    // Theme toggle
    const themeToggle = document.getElementById('themeToggle');
    const html = document.documentElement;
    
    // Load theme from localStorage
    const savedTheme = localStorage.getItem('theme') || 'light';
    if (savedTheme === 'dark') {
        html.classList.add('dark');
        themeToggle.innerHTML = '<i class="fas fa-sun text-lg"></i>';
    }
    
    themeToggle.addEventListener('click', function() {
        if (html.classList.contains('dark')) {
            html.classList.remove('dark');
            localStorage.setItem('theme', 'light');
            themeToggle.innerHTML = '<i class="fas fa-moon text-lg"></i>';
        } else {
            html.classList.add('dark');
            localStorage.setItem('theme', 'dark');
            themeToggle.innerHTML = '<i class="fas fa-sun text-lg"></i>';
        }
    });
    
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

    // Background removal toggle handler
    const removeBackgroundCheckbox = document.getElementById('removeBackground');
    removeBackgroundCheckbox.addEventListener('change', function() {
        const formatLabels = document.querySelectorAll('label.format-option');
        
        formatLabels.forEach(label => {
            const input = label.querySelector('input[name="format"]');
            const div = label.querySelector('div');
            const format = input.value.toLowerCase();
            
            if (this.checked) {
                // Only allow PNG and JPEG
                if (format === 'png' || format === 'jpeg') {
                    input.disabled = false;
                    div.classList.remove('opacity-50', 'cursor-not-allowed');
                    label.classList.remove('opacity-50', 'cursor-not-allowed');
                } else {
                    input.disabled = true;
                    div.classList.add('opacity-50');
                    label.classList.add('opacity-50', 'cursor-not-allowed');
                }
            } else {
                // Enable all formats
                input.disabled = false;
                div.classList.remove('opacity-50', 'cursor-not-allowed');
                label.classList.remove('opacity-50', 'cursor-not-allowed');
            }
        });
        
        checkFormValidity();
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
            } else {
                // Try to parse error message from response
                return response.json().then(data => {
                    const error = new Error(data.error || 'Conversion failed');
                    error.statusCode = response.status;
                    throw error;
                }).catch(() => {
                    if (response.status >= 500 && retryCount < maxRetries) {
                        throw new Error('SERVER_ERROR_RETRY');
                    }
                    throw new Error('Conversion failed');
                });
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
            const fileType = file.type.startsWith('audio/') ? 'Аудиофайл' : 'Изображение';
            showSuccessMessage(`${fileType} успешно конвертировано!`);
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
                    showErrorMessage('Истекло время ожидания. Проверьте размер файла и интернет-соединение.');
                } else if (error.message) {
                    showErrorMessage(error.message);
                } else {
                    showErrorMessage('Ошибка при конвертации файла. Пожалуйста, попробуйте снова.');
                }
            }
        });
    }

    function handleFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            // Validate file type - support both images and audio
            const validImageTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp', 'image/tiff'];
            const validAudioTypes = ['audio/wav', 'audio/mp3', 'audio/mpeg', 'audio/ogg', 'audio/flac', 'audio/aac', 'audio/mp4', 'audio/m4a'];
            const validTypes = [...validImageTypes, ...validAudioTypes];
            
            if (!validTypes.includes(file.type) && !file.type.startsWith('image/') && !file.type.startsWith('audio/')) {
                showErrorMessage('Пожалуйста, загрузите валидное изображение или аудиофайл');
                resetPreview();
                return;
            }

            // Автоматически выделять radio по расширению
            const ext = file.name.split('.').pop().toLowerCase();
            const radio = document.querySelector(`input[name="format"][value="${ext}"]`);
            if (radio) {
                radio.checked = true;
            }

            // Check file size before processing
            const maxSize = isMobile() ? 5 * 1024 * 1024 : 16 * 1024 * 1024;
            if (file.size > maxSize) {
                showErrorMessage(`Файл слишком большой. Максимум ${maxSize / (1024 * 1024)}MB`);
                resetPreview();
                return;
            }

            const reader = new FileReader();

            reader.onload = function(e) {
                // Show preview for images, show info for audio
                if (file.type.startsWith('image/')) {
                    previewImage.src = e.target.result;
                    previewImage.style.display = 'block';
                } else if (file.type.startsWith('audio/')) {
                    // Hide image and show audio icon
                    previewImage.style.display = 'none';
                    // You could add an audio icon here if needed
                }
                
                fileName.textContent = file.name + ' (' + (file.size / 1024).toFixed(2) + ' KB)';
                previewContainer.classList.remove('hidden');
                checkFormValidity();
            };

            reader.onerror = function() {
                showErrorMessage('Ошибка при чтении файла');
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
            showErrorMessage('Пожалуйста, выберите файл');
            return false;
        }
        
        if (!format) {
            showErrorMessage('Пожалуйста, выберите формат для конвертации');
            return false;
        }
        
        // Different limits for mobile and desktop
        const maxSize = isMobile() ? 5 * 1024 * 1024 : 16 * 1024 * 1024; // 5MB mobile, 16MB desktop
        
        if (file.size > maxSize) {
            const maxMB = maxSize / (1024 * 1024);
            showErrorMessage(`Размер файла не должен превышать ${maxMB}MB. На мобильных устройствах максимум 5MB.`);
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
        successDiv.innerHTML = `<i class="fas fa-check-circle mr-2"></i>${message}`;
        
        // Insert after form
        convertForm.parentNode.insertBefore(successDiv, convertForm.nextSibling);
        
        // Remove after 5 seconds
        setTimeout(() => {
            successDiv.remove();
        }, 5000);
    }
    
    function showErrorMessage(message) {
        // Create error alert
        const errorDiv = document.createElement('div');
        errorDiv.className = 'bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6 mt-4';
        errorDiv.innerHTML = `<i class="fas fa-exclamation-circle mr-2"></i>${message}`;
        
        // Insert after form
        convertForm.parentNode.insertBefore(errorDiv, convertForm.nextSibling);
        
        // Auto-remove after 8 seconds
        setTimeout(() => {
            errorDiv.remove();
        }, 8000);
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
