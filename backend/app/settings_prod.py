from app.settings import *

DEBUG = False

# 数据库连接的密码和 IP 地址
# 生产环境使用 docker-compose 中的 MySQL 服务，HOST 为服务名 mysql，
# 密码为学号，由 docker-compose.yml 中 MYSQL_ROOT_PASSWORD 指定
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "thss",
        "USER": "root",
        "PASSWORD": "2024013307",
        "HOST": "mysql",
        "PORT": "3306",
        # MySQL 服务端已设置为 utf8mb4，连接层同样指定，避免中文乱码
        "OPTIONS": {"charset": "utf8mb4"},
    }
}
