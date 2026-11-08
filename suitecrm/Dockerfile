FROM php:8.3-apache-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcurl4-openssl-dev libicu-dev libpng-dev libjpeg62-turbo-dev \
    libfreetype6-dev libzip-dev libxml2-dev libonig-dev unzip \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j4 curl gd intl mbstring mysqli pdo_mysql soap zip opcache \
    && a2enmod rewrite headers expires \
    && rm -rf /var/lib/apt/lists/*
COPY apache.conf /etc/apache2/sites-available/000-default.conf
COPY suitecrm.ini /usr/local/etc/php/conf.d/suitecrm.ini
COPY suitecrm-8.10.2.zip /tmp/suitecrm.zip
RUN unzip -q /tmp/suitecrm.zip -d /var/www/html \
    && rm /tmp/suitecrm.zip \
    && chown -R www-data:www-data /var/www/html \
    && chmod +x /var/www/html/bin/console
WORKDIR /var/www/html
