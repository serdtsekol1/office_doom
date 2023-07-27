python -m venv venv
venv\Scripts\activate
pip install -r r.txt
python manage.py runserver

1. Гитхаб
2. Скопирувати ссилку ссх( в кнопци код)
2.1 Якшо нема ссх ключа
cmd
ssh-keygen
жати ентер багато раз
Зайти на гитхаб - https://github.com/settings/keys
Нью ССХ Кей
зайти в путь який дало
найти файл з ПАБ В кинци
скопирувати все шо внутри файла
вставити в кей на гити
назвати(тайтл)
3. cmd
cd /d куда буде новий проект.
git clone git@github.com:serdtsekol1/office_doom.git .
(З ТОЧКОЙ В КИНЦИ)
4. Зайти в проект старий
Спиздити оттуда .env(Щас його не буде, спиздити його з мого компа)
clien_secret.json
media(папку)
db.sqlite3

5. Зробити
python -m venv venv
venv\Scripts\activate
pip install -r r.txt
python manage.py makemigrations
python manage.py migrate

и все. Вуаля.