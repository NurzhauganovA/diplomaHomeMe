#!/bin/bash
set -e

echo "================================================"
echo "  HomeMe CRM — Startup"
echo "================================================"

cd /app/crm

# Копируем db.sqlite3 в постоянный volume (только если там нет файла)
DB_TARGET="/app/data/db.sqlite3"
if [ ! -f "$DB_TARGET" ]; then
  echo "📦 Инициализация базы данных..."
  if [ -f "/app/crm/db.sqlite3" ]; then
    cp /app/crm/db.sqlite3 "$DB_TARGET"
    echo "   ✓ Данные из репозитория скопированы"
  fi
fi

# Применяем миграции
echo ""
echo "🗄️  Применение миграций..."
python manage.py migrate --noinput
echo "✅ Миграции применены"

# Создаём суперпользователя если нет
echo ""
echo "👤 Проверка admin..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@homeme.kz', 'admin123')
    print('✓ admin / admin123 создан')
else:
    print('  admin уже существует')
"

# Собираем статику
echo ""
echo "📦 Сбор статических файлов..."
python manage.py collectstatic --noinput 2>&1 | tail -3
echo "✅ Статика собрана"

echo ""
echo "🎉 HomeMe CRM готов!"
echo "   URL:   https://${SITE_DOMAIN:-sushizza.kz}"
echo "   Admin: /admin/ → admin / admin123"
echo ""
echo "🚀 Запуск Gunicorn..."
exec gunicorn crm.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
