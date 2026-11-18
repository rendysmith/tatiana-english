#!/usr/bin/env python3
"""
Собирает статическую копию сайта tatiana-krasnoperova.tilda.ws
для публикации на GitHub Pages.

Что делает:
  1. Скачивает страницы и все ресурсы (CSS, JS, картинки, шрифты).
  2. Переписывает абсолютные ссылки на локальные относительные.
  3. Убирает тильдовскую статистику, fallback-скрипт и загрузку
     телефонной маски с geo.tildaapi.
  4. Отключает тильдовскую отправку формы (tilda-forms.js) — вместо неё
     подключается assets/js/site-form.js (WhatsApp / Telegram).

Запуск:
    python3 -I tools/build_site.py
    SITE_URL="https://user.github.io/repo/" python3 -I tools/build_site.py
"""
import hashlib
import os
import pathlib
import posixpath
import re
import sys
import time
from urllib.parse import unquote, urlparse

import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://tatiana-krasnoperova.tilda.ws"

# Публичный адрес сайта. Если пусто — canonical/og:url/og:image удаляются,
# чтобы не оставлять ссылок на tilda.ws. Задайте и пересоберите после деплоя.
SITE_URL = os.environ.get("SITE_URL", "").strip()
if SITE_URL and not SITE_URL.endswith("/"):
    SITE_URL += "/"

# Исходная страница -> путь в репозитории
PAGES = {
    "/": "index.html",
    "/consent": "consent/index.html",
    "/oferta": "oferta/index.html",
    "/policy": "policy/index.html",
}

ASSET_HOSTS = {
    "static.tildacdn.com",
    "thb.tildacdn.com",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
}

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

URL_RE = re.compile(r"https?://[A-Za-z0-9._~:/?#\[\]@!$&*+,;=%-]+")
SCRIPT_RE = re.compile(r"<script\b[^>]*>.*?</script>", re.S | re.I)
CSS_URL_RE = re.compile(r"url\(\s*(['\"]?)([^)'\"]+)\1\s*\)")

session = requests.Session()
session.headers.update({"User-Agent": UA, "Accept-Language": "ru,en;q=0.8"})


def fetch(url: str) -> bytes:
    last_error = None
    for attempt in range(3):
        try:
            r = session.get(url, timeout=60)
            if r.status_code == 200 and r.content:
                return r.content
            last_error = f"HTTP {r.status_code}, {len(r.content)} bytes"
        except requests.RequestException as exc:  # сеть/таймаут
            last_error = str(exc)
        time.sleep(1 + attempt)
    raise RuntimeError(f"Не удалось скачать {url}: {last_error}")


def sanitize(path: str) -> str:
    name = path.strip("/").replace("/", "__")
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return name or hashlib.sha1(path.encode()).hexdigest()[:12]


def local_path_for(url: str) -> str:
    """Возвращает путь файла в репозитории (от корня)."""
    parsed = urlparse(url)
    host = parsed.netloc
    path = unquote(parsed.path)

    if host == "fonts.googleapis.com":
        return "assets/css/google-fonts.css"

    if host == "fonts.gstatic.com":
        # Google Fonts иногда отдаёт ссылки без расширения — это всё равно woff2.
        ext = pathlib.PurePosixPath(path).suffix or ".woff2"
        return "assets/fonts/" + hashlib.sha1(url.encode()).hexdigest()[:16] + ext

    name = posixpath.basename(path)
    if host == "static.tildacdn.com":
        if path.startswith("/ws/project11970899/"):
            return "assets/project/" + name
        for prefix, folder in (("/css/", "css"), ("/js/", "js"), ("/img/", "img")):
            if path.startswith(prefix):
                return f"assets/{folder}/{name}"
        if path.startswith("/lib/"):
            return "assets/lib/" + path[len("/lib/") :].lstrip("/")

    # Картинки проекта и превью thb.tildacdn.com
    return f"assets/images/{host.split('.')[0]}__{sanitize(path)}"


def collect_urls(text: str) -> set:
    found = set()
    for match in URL_RE.finditer(text):
        url = match.group(0).rstrip(".,;")
        parsed = urlparse(url)
        if parsed.netloc in ASSET_HOSTS and (parsed.path or parsed.query):
            found.add(url)
    return found


def remove_script_blocks(html: str, keywords) -> str:
    def repl(match):
        block = match.group(0)
        return "" if any(k in block for k in keywords) else block

    return SCRIPT_RE.sub(repl, html)


def strip_tilda_runtime(html: str) -> str:
    # Статистика Tilda, fallback на neo.tildacdn.com, форма/маска телефона.
    html = remove_script_blocks(
        html,
        (
            "tilda-stat-1.0.min.js",
            "tilda-phone-mask-1.1.min.js",
            "tilda-forms-1.0.min.js",
            "tilda-fallback-1.0.min.js",
        ),
    )
    # Служебные поля тильдовской формы.
    html = re.sub(r"<input[^>]*name=[\"']formservices\[\][\"'][^>]*>", "", html)
    html = re.sub(r"<input[^>]*name=[\"']tildaspec-formname[\"'][^>]*>", "", html)
    html = re.sub(r"\s*data-formactiontype=[\"'][^\"']*[\"']", "", html)
    # DNS-prefetch/preconnect на внешние хосты больше не нужны.
    html = re.sub(
        r"<link[^>]*rel=[\"'](?:dns-prefetch|preconnect)[\"'][^>]*>", "", html
    )
    # canonical/og:url/og:image на tilda.ws.
    html = re.sub(
        r"<link[^>]*rel=[\"']canonical[\"'][^>]*>", "", html
    )
    html = re.sub(
        r"<meta[^>]*property=[\"']og:url[\"'][^>]*>", "", html
    )
    # Схема tel: в исходнике записана с заглавной буквы.
    html = html.replace('href="Tel:', 'href="tel:').replace("href='Tel:", "href='tel:")
    if not SITE_URL:
        html = re.sub(
            r"<meta[^>]*property=[\"']og:image[\"'][^>]*>", "", html
        )
    return html


def download_assets(urls: set) -> dict:
    """Скачивает URL и рекурсивно ресурсы из CSS. Возвращает url -> путь."""
    mapping = {}
    queue = sorted(urls)
    seen_css = set()

    while queue:
        url = queue.pop(0)
        if url in mapping:
            continue
        local = local_path_for(url)
        try:
            content = fetch(url)
        except RuntimeError as exc:
            print(f"  ! {exc}", file=sys.stderr)
            continue
        target = ROOT / local
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        mapping[url] = local
        print(f"  + {local}  ({len(content)} B)")

        if local.endswith(".css") and local not in seen_css:
            seen_css.add(local)
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                continue
            for match in CSS_URL_RE.finditer(text):
                sub = match.group(2).strip()
                if sub in seen_css:
                    continue
                if sub.startswith("http"):
                    parsed = urlparse(sub)
                    if parsed.netloc in ASSET_HOSTS:
                        seen_css.add(sub)
                        if sub not in mapping and sub not in queue:
                            queue.append(sub)

    return mapping


def rewrite_css(mapping: dict) -> None:
    for url, local in mapping.items():
        if not local.endswith(".css"):
            continue
        path = ROOT / local
        text = path.read_text(encoding="utf-8")
        css_dir = posixpath.dirname(local)

        def repl(match):
            raw = match.group(2).strip()
            if raw in mapping:
                rel = posixpath.relpath(mapping[raw], css_dir)
                return f"url('{rel}')"
            return match.group(0)

        path.write_text(CSS_URL_RE.sub(repl, text), encoding="utf-8")


def page_link(url: str, page_dir: str) -> str:
    """Относительная ссылка на внутреннюю страницу."""
    path = urlparse(url).path
    if path in ("", "/"):
        target_dir = "."
    else:
        target_dir = path.strip("/")
    rel = posixpath.relpath(target_dir, page_dir)
    return "./" if rel == "." else rel.rstrip("/") + "/"


def tweak_reviews_slider(html: str) -> str:
    """Отзывы: 3 карточки в ряд на десктопе (2 на планшете, 1 на телефоне).

    Tilda берёт количество карточек из data-slider-items-in-row, а высоту
    подгоняет под активную карточку — при трёх в ряд это обрезало бы текст,
    поэтому корректную высоту отключаем.
    """
    pattern = re.compile(
        r"<div[^>]*id=\"carousel_856649241\"[^>]*>", re.S
    )

    def repl(match):
        tag = match.group(0)
        tag = tag.replace(
            'data-slider-correct-height="true"',
            'data-slider-correct-height="false"',
        )
        if "data-slider-items-in-row" not in tag:
            tag = tag.replace(
                "data-slider-transition=",
                'data-slider-items-in-row="3" data-slider-transition=',
                1,
            )
        return tag

    return pattern.sub(repl, html, count=1)


def rewrite_html(html: str, out_path: str, mapping: dict) -> str:
    page_dir = posixpath.dirname(out_path) or "."

    # Дата-URI и шрифты: сначала точные URL, длинные раньше коротких.
    for url in sorted(mapping, key=len, reverse=True):
        rel = posixpath.relpath(mapping[url], page_dir)
        html = html.replace(url, rel)

    # Внутренние ссылки.
    for path in ("/consent", "/oferta", "/policy"):
        url = BASE + path
        html = html.replace(url, page_link(url, page_dir))
    # Корень сайта — после вложенных путей.
    html = html.replace(BASE, "./" if page_dir == "." else "../")

    if SITE_URL:
        page_path = "" if out_path == "index.html" else posixpath.dirname(out_path) + "/"
        canonical = SITE_URL + page_path
        html = html.replace(
            "</head>",
            f'<link rel="canonical" href="{canonical}">'
            f'<meta property="og:url" content="{canonical}">'
            "</head>",
            1,
        )

    # lang у <html>.
    html = html.replace("<html>", '<html lang="ru">', 1)
    return tweak_reviews_slider(html)


def add_site_assets(html: str, out_path: str) -> str:
    page_dir = posixpath.dirname(out_path) or "."
    prefix = "" if page_dir == "." else posixpath.relpath(".", page_dir) + "/"
    head = (
        f'<link rel="stylesheet" href="{prefix}assets/css/site-custom.css">'
    )
    script = f'<script src="{prefix}assets/js/site-form.js" defer></script>'
    html = html.replace("</head>", head + "</head>", 1)
    html = html.replace("</body>", script + "</body>", 1)
    return html


FORM_JS = r"""/* Отправка заявки без серверов: формирует сообщение и открывает
   WhatsApp (с текстом) или Telegram (текст копируется в буфер). */
(function () {
  'use strict';

  var WHATSAPP_PHONE = '79061168417';
  var TELEGRAM_USER = 'Tatyana2612_K';
  var form = document.querySelector('form.js-form-proccess');
  if (!form) return;

  var successBox = form.querySelector('.js-successbox');
  var inputsBox = form.querySelector('.t-form__inputsbox');
  var nameInput = form.querySelector('input[name="Name"]');
  var phoneInput = form.querySelector('input[name="Phone"]');
  var emailInput = form.querySelector('input[name="Email"]');
  var agree = form.querySelector('input[name="Checkbox"]');

  function digits(value) {
    return (value || '').replace(/\D/g, '');
  }

  function setError(input, message) {
    if (!input) return;
    var group = input.closest('.t-input-group');
    if (!group) return;
    var box = group.querySelector('.t-input-error');
    group.classList.toggle('t-input-group_error', Boolean(message));
    if (box) {
      box.textContent = message || '';
      box.style.display = message ? 'block' : 'none';
    }
    input.setAttribute('aria-invalid', message ? 'true' : 'false');
  }

  function clearError(input) {
    setError(input, '');
  }

  function formatPhone() {
    var d = digits(phoneInput.value).slice(0, 11);
    if (!d) return;
    if (d.charAt(0) === '8') d = '7' + d.slice(1);
    if (d.charAt(0) !== '7') d = '7' + d;
    d = d.slice(0, 11);
    var out = '+7';
    if (d.length > 1) out += ' (' + d.slice(1, 4);
    if (d.length >= 5) out += ') ' + d.slice(4, 7);
    if (d.length >= 8) out += '-' + d.slice(7, 9);
    if (d.length >= 10) out += '-' + d.slice(9, 11);
    phoneInput.value = out;
  }

  function buildMessage() {
    var lines = [
      'Заявка с сайта',
      '',
      'Имя: ' + (nameInput ? nameInput.value.trim() : ''),
      'Телефон: ' + (phoneInput ? phoneInput.value.trim() : ''),
    ];
    var email = emailInput ? emailInput.value.trim() : '';
    if (email) lines.push('Email: ' + email);
    lines.push('', 'Дата: ' + new Date().toLocaleString('ru-RU'));
    return lines.join('\n');
  }

  function showSuccess(name, message) {
    var waUrl = 'https://wa.me/' + WHATSAPP_PHONE + '?text=' + encodeURIComponent(message);
    var tgUrl = 'https://t.me/' + TELEGRAM_USER;
    if (successBox) {
      successBox.innerHTML =
        '<div class="site-form-success">' +
          '<div class="site-form-success__title">Спасибо, ' + escapeHtml(name) + '!</div>' +
          '<p>Заявка сформирована. Отправьте её в удобный мессенджер — я отвечу в ближайшее время.</p>' +
          '<div class="site-form-success__actions">' +
            '<a class="t-btn site-form-btn site-form-btn_wa" href="' + waUrl + '" target="_blank" rel="noopener">Отправить в WhatsApp</a>' +
            '<a class="t-btn site-form-btn site-form-btn_tg" href="' + tgUrl + '" target="_blank" rel="noopener">Открыть Telegram</a>' +
          '</div>' +
          '<p class="site-form-success__hint">Для Telegram текст заявки уже скопирован — просто вставьте его в чат.</p>' +
        '</div>';
      successBox.style.display = 'block';
    }
    if (inputsBox) inputsBox.style.display = 'none';

    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(message).catch(function () {});
    }
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, function (c) {
      return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c];
    });
  }

  if (phoneInput) {
    phoneInput.addEventListener('input', formatPhone);
    phoneInput.addEventListener('blur', formatPhone);
  }
  [nameInput, phoneInput, emailInput, agree].forEach(function (input) {
    if (!input) return;
    var event = input.type === 'checkbox' ? 'change' : 'input';
    input.addEventListener(event, function () { clearError(input); });
  });

  form.addEventListener(
    'submit',
    function (event) {
      event.preventDefault();
      event.stopImmediatePropagation();

      var name = nameInput ? nameInput.value.trim() : '';
      var phoneDigits = phoneInput ? digits(phoneInput.value) : '';
      var email = emailInput ? emailInput.value.trim() : '';
      var valid = true;

      if (name.length < 2) {
        setError(nameInput, 'Укажите ваше имя');
        valid = false;
      }
      if (phoneDigits.length < 10) {
        setError(phoneInput, 'Укажите номер телефона');
        valid = false;
      }
      if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        setError(emailInput, 'Проверьте адрес электронной почты');
        valid = false;
      }
      if (agree && !agree.checked) {
        setError(agree, 'Примите условия договора и политики');
        valid = false;
      }
      if (!valid) return;

      var message = buildMessage();
      showSuccess(name, message);
    },
    true
  );
})();
"""

CUSTOM_CSS = """/* Дополнения к стилям Tilda для формы без бэкенда. */
/* Стандартный зелёный блок «Спасибо» Tilda заменяем нейтральным:
   на нём зелёная кнопка WhatsApp иначе сливается с фоном. */
.t-form__successbox {
  padding: 0 !important;
  color: #343434 !important;
  background: transparent !important;
  text-align: center;
}
.t-input-error {
  display: none;
  margin-top: 6px;
  color: #d93025;
  font-size: 14px;
  line-height: 1.35;
}
.t-input-group_error .t-input {
  border-color: #d93025 !important;
}
.site-form-success {
  padding: 8px 0 4px;
  text-align: center;
}
.site-form-success__title {
  margin-bottom: 10px;
  font-size: 22px;
  font-weight: 700;
}
.site-form-success p {
  margin: 0 0 16px;
  font-size: 15px;
  line-height: 1.5;
}
.site-form-success__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
  margin-bottom: 14px;
}
.site-form-btn {
  display: inline-block;
  padding: 12px 20px;
  border-radius: 8px;
  color: #fff !important;
  font-size: 15px;
  font-weight: 600;
  text-decoration: none;
  background: #25d366;
}
.site-form-btn_tg {
  background: #2aabee;
}
.site-form-success__hint {
  margin: 0;
  font-size: 13px;
  opacity: .7;
}

/* --- Слайдер отзывов: 3 карточки в ряд и заметные стрелки --- */
#rec856649241 .t-slds__main {
  box-sizing: border-box;
  padding-left: 84px;
  padding-right: 84px;
}
#rec856649241 .t-slds__items-wrapper {
  display: flex !important;
  align-items: stretch;
}
#rec856649241 .t-slds__item {
  display: flex;
  box-sizing: border-box;
  padding: 0 12px;
}
#rec856649241 .t-slds__item > .t-width {
  display: flex;
  width: 100%;
  height: 100%;
}
#rec856649241 .t-slds__item .t-slds__wrapper {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  box-sizing: border-box;
  padding: 28px 26px 30px !important;
  background: #ffffff;
  border-radius: 18px;
  box-shadow: 0 10px 30px rgba(52, 52, 52, .07);
}
#rec856649241 .t726__text {
  flex: 1 1 auto;
  margin-bottom: 22px !important;
  font-size: 16px;
  line-height: 1.55;
}
#rec856649241 .t726__bgimg {
  margin-top: auto;
}
#rec856649241 .t726__title {
  margin-top: 12px;
}

#rec856649241 .t-slds__arrow-withbg {
  width: 54px !important;
  height: 54px !important;
  background-color: #343434 !important;
  box-shadow: 0 6px 18px rgba(52, 52, 52, .22);
}
#rec856649241 .t-slds__arrow-withbg:hover,
#rec856649241 .t-slds__arrow-withbg:focus-visible {
  background-color: #64deff !important;
}
#rec856649241 .t-slds__arrow-withbg svg polyline {
  stroke: #ffffff;
  stroke-width: 1.8;
}
#rec856649241 .t-slds__arrow-withbg:hover svg polyline,
#rec856649241 .t-slds__arrow-withbg:focus-visible svg polyline {
  stroke: #343434;
}
#rec856649241 .t-slds__arrow_body {
  width: 14px !important;
}
#rec856649241 .t-slds__arrow-left {
  left: 0;
}
#rec856649241 .t-slds__arrow-right {
  right: 0;
}

@media (max-width: 960px) {
  #rec856649241 .t-slds__main {
    max-width: 960px;
    padding-left: 64px;
    padding-right: 64px;
  }
  #rec856649241 .t-slds__arrow-withbg {
    width: 48px !important;
    height: 48px !important;
  }
  #rec856649241 .t-slds__item .t-slds__wrapper {
    padding: 24px 22px 26px !important;
  }
  #rec856649241 .t726__text {
    font-size: 15px;
  }
}

@media (max-width: 640px) {
  #rec856649241 .t-slds__main {
    padding-left: 46px;
    padding-right: 46px;
  }
  #rec856649241 .t-slds__arrow-withbg {
    width: 42px !important;
    height: 42px !important;
  }
  #rec856649241 .t-slds__arrow-left {
    left: 0;
  }
  #rec856649241 .t-slds__arrow-right {
    right: 0;
  }
  #rec856649241 .t-slds__item {
    padding: 0 6px;
  }
}
"""


def write_support_files() -> None:
    (ROOT / "assets/js/site-form.js").write_text(FORM_JS, encoding="utf-8")
    (ROOT / "assets/css/site-custom.css").write_text(CUSTOM_CSS, encoding="utf-8")
    (ROOT / ".nojekyll").write_text("", encoding="utf-8")
    (ROOT / "robots.txt").write_text(
        "User-agent: *\nAllow: /\n" + (f"\nSitemap: {SITE_URL}sitemap.xml\n" if SITE_URL else ""),
        encoding="utf-8",
    )
    if SITE_URL:
        urls = "".join(
            f"  <url><loc>{SITE_URL}{'' if p == 'index.html' else posixpath.dirname(p) + '/'}</loc></url>\n"
            for p in PAGES.values()
        )
        (ROOT / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{urls}</urlset>\n",
            encoding="utf-8",
        )


def main() -> int:
    print("Скачиваю страницы…")
    pages = {}
    for path in PAGES:
        url = BASE + path
        html = fetch(url).decode("utf-8")
        html = strip_tilda_runtime(html)
        pages[path] = html
        print(f"  + {url}  ({len(html)} B)")

    urls = set()
    for html in pages.values():
        urls |= collect_urls(html)
    print(f"Ресурсов найдено: {len(urls)}")

    print("Скачиваю ресурсы…")
    mapping = download_assets(urls)

    print("Переписываю CSS…")
    rewrite_css(mapping)

    print("Переписываю HTML…")
    for path, html in pages.items():
        out_path = PAGES[path]
        html = rewrite_html(html, out_path, mapping)
        html = add_site_assets(html, out_path)
        target = ROOT / out_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")
        print(f"  + {out_path}  ({len(html)} B)")

    write_support_files()
    print("Готово.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
