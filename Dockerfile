FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    apache2 \
    libapache2-mod-wsgi-py3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /var/www/flask-todolist

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Konfigurasi Apache
COPY app.conf /etc/apache2/sites-available/000-default.conf
RUN a2enmod wsgi && a2ensite 000-default

EXPOSE 80
CMD ["/usr/sbin/apache2ctl", "-D", "FOREGROUND"]