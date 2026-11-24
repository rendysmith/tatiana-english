# tatiana-english

Сайт репетитора по английскому языку Татьяны Красноперовой.

Статический сайт для публикации на **GitHub Pages**: стили, скрипты, картинки
и шрифты лежат локально, серверная часть не нужна.

Сайт создан компанией ZR — [zeroroutine.ai](https://zeroroutine.ai).

## Структура

```
index.html                 — главная (одностраничник)
consent/index.html         — согласие на обработку персональных данных
oferta/index.html          — договор-оферта
policy/index.html          — политика конфиденциальности
404.html                   — страница для несуществующих адресов
assets/
  css/style.css            — все стили сайта
  css/google-fonts.css     — подключение локальных шрифтов Manrope
  js/main.js               — меню, карусель отзывов, форма записи
  images/                  — картинки сайта (webp)
  fonts/                   — Manrope и Cormorant Garamond (woff2)
.nojekyll                  — отключает обработку Jekyll на GitHub Pages
robots.txt
```

## Публикация на GitHub Pages

1. Запушьте ветку `main` в репозиторий на GitHub.
2. **Settings → Pages → Build and deployment**: *Deploy from a branch*,
   ветка `main`, папка `/ (root)`, **Save**.
3. Через 1–2 минуты сайт будет доступен по адресу
   `https://<username>.github.io/<repo>/`.

## Связь

Записи через форму нет: на сайте только ссылки на WhatsApp (`https://wa.me/79061168417`) и Telegram (`https://t.me/Tatyana2612_K`). Они заданы прямо в `index.html`.
