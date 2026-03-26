# Развертывание конвертера изображений

## Варианты развертывания

### 1. Локальный запуск (для разработки)

```bash
# Активация виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# Установка зависимостей
pip install -r requirements.txt

# Запуск
python app.py
```

### 2. Развертывание на PythonAnywhere

1. Создайте аккаунт на [PythonAnywhere](https://www.pythonanywhere.com/)
2. Создайте новое Web приложение
3. Выберите Flask и Python 3.9+
4. Загрузите файлы проекта
5. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
6. Настройте WSGI файл:
   ```python
   import sys
   sys.path.append('/home/yourusername/mysite')
   from app import app as application
   ```

### 3. Развертывание на Heroku

1. Установите Heroku CLI
2. Создайте файл `Procfile`:
   ```
   web: gunicorn app:app
   ```
3. Создайте файл `runtime.txt`:
   ```
   python-3.9.16
   ```
4. Разверните:
   ```bash
   heroku create your-app-name
   git add .
   git commit -m "Deploy"
   git push heroku main
   ```

### 4. Развертывание на VPS (DigitalOcean, Vultr)

```bash
# Установка на Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip nginx ffmpeg

# Клонирование проекта
git clone <your-repo>
cd image-converter

# Установка зависимостей
pip3 install -r requirements.txt

# Установка Gunicorn
pip3 install gunicorn

# Создание systemd сервиса
sudo nano /etc/systemd/system/image-converter.service
```

Содержимое сервиса:
```ini
[Unit]
Description=Image Converter Flask App
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/image-converter
ExecStart=/usr/local/bin/gunicorn app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Запуск сервиса
sudo systemctl daemon-reload
sudo systemctl enable image-converter
sudo systemctl start image-converter

# Настройка Nginx
sudo nano /etc/nginx/sites-available/image-converter
```

Конфигурация Nginx:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 5. Docker развертывание

Создайте `Dockerfile`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Установка ffmpeg для аудио
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
```

Создайте `docker-compose.yml`:
```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
```

Запуск:
```bash
docker-compose up -d
```

### 6. Развертывание на Render.com

1. Создайте аккаунт на [Render](https://render.com/)
2. Подключите GitHub репозиторий
3. Создайте новый Web Service
4. Укажите:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
   - Runtime: Python 3
   - Environment Variables: добавьте `FFMPEG_PATH=/usr/bin/ffmpeg` (если доступно)

**Примечание:** Render.com имеет предустановленный ffmpeg. Если аудио конвертация не работает, попробуйте использовать Docker развертывание с ffmpeg.

## Настройка для продакшена

### Безопасность
- Замените `SECRET_KEY` в `app.py` на случайную строку
- Используйте HTTPS в продакшене
- Ограничьте размер файлов

### Оптимизация
- Используйте Gunicorn вместо встроенного сервера Flask
- Настройте CDN для статических файлов
- Добавьте логирование

### Мониторинг
```python
import logging
logging.basicConfig(level=logging.INFO)
```

## Проверка развертывания

После развертывания проверьте:
1. Главная страница загружается
2. Загрузка файла работает
3. Конвертация работает
4. Скачивание файла работает
5. Адаптивный дизайн на мобильных устройствах

## Рекомендуемый вариант

Для быстрого развертывания используйте **PythonAnywhere** или **Render.com**.
Для продакшена с высокой нагрузкой - **VPS с Nginx + Gunicorn**.
