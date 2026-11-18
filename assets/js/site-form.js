/* Отправка заявки без серверов: формирует сообщение и открывает
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
