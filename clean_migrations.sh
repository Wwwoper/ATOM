#!/bin/bash

# Функция для поиска файлов миграций
find_migrations() {
    find . -path "*/migrations/*.py" \
        -not -name "__init__.py" \
        -not -path "./venv/*" \
        -not -path "./env/*" \
        -not -path "./.venv/*" \
        -not -path "./.env/*" \
        -not -path "./virtualenv/*" \
        -not -path "./virtual/*"
}

# Показать файлы, которые будут удалены
echo "Следующие файлы миграций будут удалены:"
find_migrations

# Запросить подтверждение
read -p "Вы уверены, что хотите удалить эти файлы? (y/n) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]
then
    # Удаление файлов миграций
    find_migrations -exec rm -f {} +
    
    # Удаление скомпилированных файлов миграций
    find . -path "*/migrations/*.pyc" \
        -not -path "./venv/*" \
        -not -path "./env/*" \
        -not -path "./.venv/*" \
        -not -path "./.env/*" \
        -not -path "./virtualenv/*" \
        -not -path "./virtual/*" \
        -exec rm -f {} +
        
    echo "Файлы миграций успешно удалены"
else
    echo "Операция отменена"
fi 