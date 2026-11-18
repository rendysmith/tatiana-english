# tatiana-english

Статическая копия сайта **https://tatiana-krasnoperova.tilda.ws/** — репетитор
по английскому языку Татьяна Красноперова.

Сайт собран для публикации на **GitHub Pages** и не требует серверов, базы данных
и обращений к Tilda: стили, скрипты, картинки и шрифты лежат локально.

## Структура

```
index.html                 — главная (одностраничник)
consent/index.html         — согласие на обработку персональных данных
oferta/index.html          — договор-оферта
policy/index.html          — политика конфиденциальности
404.html                   — страница для несуществующих адресов
assets/
  css/                     — стили Tilda + локальные шрифты Google Fonts
  js/                      — скрипты Tilda + site-form.js (форма)
  project/                 — стили/скрипты конкретных страниц Tilda
  images/                  — картинки сайта
  fonts/                   — Manrope (woff2)
tools/build_site.py        — скрипт сборки из исходного сайта Tilda
.nojekyll                  — отключает обработку Jekyll на GitHub Pages
robots.txt
```

## Публикация на GitHub Pages

1. Создайте репозиторий на GitHub (например, `tatiana-english`) и запушьте ветку `main`:

   ```bash
   git add .
   git commit -m "Готовый статический сайт"
   git push -u origin main
   ```

2. В репозитории откройте **Settings → Pages**.
3. В блоке **Build and deployment** выберите **Deploy from a branch**,
   ветку `main`, папку `/ (root)` и нажмите **Save**.
4. Через 1–2 минуты сайт будет доступен по адресу
   `https://<username>.github.io/<repo>/`.

Файл `.nojekyll` уже добавлен — без него GitHub Pages может игнорировать часть
файлов с подчёркиваниями.

### Канонический адрес и соцсети

Пока `SITE_URL` не задан, из HTML удалены `canonical`, `og:url` и `og:image`
(чтобы нигде не осталось ссылок на `tilda.ws`). После публикации пересоберите
сайт с реальным адресом:

```bash
SITE_URL="https://username.github.io/tatiana-english/" python3 -I tools/build_site.py
git add . && git commit -m "Канонический адрес" && git push
```

Будут добавлены `canonical`, `og:url`, `og:image`, `sitemap.xml` и `Sitemap`
в `robots.txt`.

### Свой домен (необязательно)

В **Settings → Pages → Custom domain** укажите домен, и GitHub создаст файл
`CNAME`. Затем пересоберите сайт с `SITE_URL="https://ваш-домен.ru/"`.

## Форма записи

Tilda-форма не может отправлять данные на GitHub Pages, поэтому она заменена
на локальный обработчик `assets/js/site-form.js`:

1. Пользователь заполняет имя, телефон и (необязательно) email, принимает условия.
2. Скрипт проверяет поля и показывает экран «Спасибо».
3. Кнопка **«Отправить в WhatsApp»** открывает чат с уже заполненным текстом заявки.
4. Кнопка **«Открыть Telegram»** открывает чат; текст заявки предварительно
   копируется в буфер обмена.

Контакты задаются в начале `assets/js/site-form.js`:

```js
var WHATSAPP_PHONE = '79061168417';   // номер без + и пробелов
var TELEGRAM_USER = 'Tatyana2612_K';  // username в Telegram
```

После изменения скрипта пересоберите проект (`tools/build_site.py`), иначе
изменения затрутся — исходник лежит в скрипте сборки.

## Что было убрано из исходного сайта

* `tilda-stat-1.0.min.js` — статистика Tilda.
* `tilda-fallback-1.0.min.js` — резервная загрузка с `neo.tildacdn.com`.
* `tilda-forms-1.0.min.js` — отправка формы на серверы Tilda.
* `tilda-phone-mask-1.1.min.js` — маска телефона, которая определяла страну
  через `geo.tildaapi.com`. Заменена собственной маской в `site-form.js`.
* Поля `formservices[]`, `tildaspec-formname` и `data-formactiontype`.
* `dns-prefetch`/`preconnect` на внешние домены.

Все остальные визуальные скрипты Tilda (анимации, слайдер, попапы, ленивая
загрузка картинок) сохранены локально и работают как раньше.

## Как обновить контент

Скрипт заново скачивает страницы и ресурсы с текущего сайта Tilda:

```bash
python3 -I tools/build_site.py
```

Требуется Python 3 и пакет `requests`. Скрипт также можно запускать с
`SITE_URL` (см. выше). После сборки проверьте дифф и запушьте изменения.

## Локальная проверка

```bash
python3 -m http.server 8765
```

Откройте `http://127.0.0.1:8765/`. Именно через HTTP, а не `file://` —
так пути и скрипты ведут себя так же, как на GitHub Pages.

## Примечание

Внизу страниц сохранён блок «Made on Tilda» — он был на исходном сайте и
является частью разметки Tilda. Если проект Tilda будет закрыт, ссылку можно
удалить, но по условиям бесплатного тарифа Tilda её удаление нежелательно.
