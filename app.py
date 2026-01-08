# app.py - ВЕРСИЯ С НАСТРАИВАЕМЫМИ КНОПКАМИ И GITHUB SECRETS
import requests
import time
import json
import os
import re

print("=" * 50)
print("🤖 PIRAJOK BOT - ВЕРСИЯ С НАСТРАИВАЕМЫМИ КНОПКАМИ")
print("=" * 50)


# ================== КОНФИГУРАЦИЯ ==================
def get_bot_token():
    """Получение токена бота из переменных окружения GitHub"""
    token = os.getenv('BOT_TOKEN')
    
    if not token:
        print("⚠️  Токен бота не найден!")
        print("Установите переменную окружения BOT_TOKEN")
        print("На GitHub: Settings → Secrets → BOT_TOKEN")
        exit()
    
    return token


def get_admin_id():
    """Получение ID админа из переменных окружения GitHub"""
    admin_id = os.getenv('ADMIN_ID')
    
    if admin_id:
        return admin_id
    
    # Если ADMIN_ID не установлен в окружении, попробуем получить из конфига
    print("ℹ️  ADMIN_ID не найден в переменных окружения, проверяю config.json...")
    return None


def load_config():
    config_file = 'config.json'

    if not os.path.exists(config_file):
        print(f"❌ Файл {config_file} не найден!")
        exit()

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Ошибка загрузки конфигурации: {e}")
        exit()


BOT_TOKEN = get_bot_token()
CONFIG = load_config()

# Получаем настройки кнопок из конфига
BUTTONS = CONFIG['buttons']

# Получаем ID получателя: сначала из окружения, потом из конфига
ADMIN_FROM_ENV = get_admin_id()
if ADMIN_FROM_ENV:
    RECIPIENT_ID = ADMIN_FROM_ENV
    print(f"✅ Получатель из переменных окружения: ID {RECIPIENT_ID}")
else:
    # Проверяем конфиг
    if 'recipient' in CONFIG and 'telegram_id' in CONFIG['recipient']:
        RECIPIENT_ID = CONFIG['recipient']['telegram_id']
        print(f"✅ Получатель из config.json: ID {RECIPIENT_ID}")
    else:
        print("❌ Не указан telegram_id получателя!")
        print("Установите переменную ADMIN_ID в секретах GitHub")
        print("Или укажите recipient.telegram_id в config.json")
        exit()

# Проверяем корректность ID
if not RECIPIENT_ID or not str(RECIPIENT_ID).isdigit():
    print(f"❌ Некорректный telegram_id: {RECIPIENT_ID}")
    print("ID должен содержать только цифры")
    exit()

# ================== ПРОВЕРКА БОТА ==================
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
try:
    resp = requests.get(f"{BASE_URL}/getMe", timeout=10)
    bot_data = resp.json()
    if bot_data.get('ok'):
        print(f"✅ Бот @{bot_data['result']['username']} готов к работе!")
    else:
        print("❌ Ошибка бота")
        exit()
except Exception as e:
    print(f"❌ Ошибка проверки бота: {e}")
    exit()

# ================== НОМЕР ЗАКАЗА ==================
order_number = 1
last_order_file = 'last_order.txt'
if os.path.exists(last_order_file):
    try:
        with open(last_order_file, 'r') as f:
            order_number = int(f.read().strip()) + 1
    except:
        pass

print(f"📊 Следующий заказ: #{order_number}")
print(f"📋 Кнопка 'Меню': {BUTTONS['menu']}")
print(f"🚚 Кнопка 'Доставка': {BUTTONS['delivery']}")
print(f"🛒 Кнопка 'Заказать': {BUTTONS['order']}")
print("=" * 50)
print("🚀 Бот запущен! (версия с GitHub Secrets)")
print("⏹️  Ctrl+C для остановки")
print("=" * 50)

# ================== КОНСТАНТЫ ==================
ORDERS_FILE = 'orders_history.json'


# ================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==================
def validate_phone(phone):
    cleaned = re.sub(r'[^\d+]', '', str(phone))
    if len(cleaned) < 10:
        return False
    digits = cleaned.lstrip('+')
    return digits.isdigit()


def get_menu_text():
    menu_config = CONFIG['menu']
    menu_text = f"{menu_config['title']}:\n\n"

    for section_key, section_data in menu_config['sections'].items():
        menu_text += f"{section_data['title']}\n"
        for item in section_data['items']:
            menu_text += f"• {item['name']} - {item['price']}₽\n"
        menu_text += "\n"

    return menu_text.strip()


def get_contacts_text():
    contacts = CONFIG['contacts']
    return f"{contacts['title']}:\n\n📍 Адрес: {contacts['address']}\n📱 Телефон: {contacts['phone']}\n⏰ Работаем: {contacts['working_hours']}\n📧 Email: {contacts['email']}"


def get_about_text():
    about = CONFIG['about']
    about_text = f"{about['title']}:\n\n{about['description']}\n\n"
    for feature in about['features']:
        about_text += f"✅ {feature}\n"
    return about_text.strip()


def save_order_number(num):
    try:
        with open(last_order_file, 'w') as f:
            f.write(str(num))
    except:
        pass


def send_message(chat_id, text, keyboard=None):
    data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
    if keyboard:
        data['reply_markup'] = json.dumps(keyboard)

    try:
        response = requests.post(f"{BASE_URL}/sendMessage", json=data, timeout=10)
        return response.status_code == 200
    except:
        return False


def send_order_to_admin(order_num, client_name, client_id, phone, address, order_text, order_type, payment_method):
    type_icon = "🚚" if order_type == "Доставка" else "🛒"
    type_text = "ДОСТАВКА" if order_type == "Доставка" else "САМОВЫВОЗ"

    message = f"🆕 ЗАКАЗ #{order_num} ДЛЯ PIRAJOK\n"
    message += f"{type_icon} Тип: {type_text}\n"

    if order_type == "Доставка":
        payment_icon = "💵" if payment_method == "Наличные" else "💳"
        payment_text = "Наличными" if payment_method == "Наличные" else "КАРТОЙ"
        message += f"{payment_icon} Оплата: {payment_text}\n\n"

        if payment_method == "Картой":
            message += "🚨 ВНИМАНИЕ ВОДИТЕЛЮ: ОПЛАТА КАРТОЙ\n"
            message += "Нужно сказать водителю про оплату картой!\n\n"
    else:
        message += "\n"

    message += f"👤 Клиент: {client_name}\n"
    message += f"📱 Телефон: {phone}\n"

    if order_type == "Доставка":
        message += f"📍 Адрес: {address}\n"

    message += f"📱 Telegram: <a href='tg://user?id={client_id}'>Написать клиенту</a>\n"
    message += f"⏰ Время: {time.strftime('%H:%M %d.%m')}\n\n"
    message += f"📦 ЗАКАЗ:\n{order_text}\n\n"
    message += f"🔢 Номер: #{order_num}\n"
    message += f"✅ Статус: Новый"

    return send_message(RECIPIENT_ID, message)


# ================== КЛАВИАТУРЫ (ИСПОЛЬЗУЮТ КНОПКИ ИЗ КОНФИГА) ==================
def get_main_keyboard():
    """Главная клавиатура с кнопками из конфига"""
    return {
        'keyboard': [
            [BUTTONS['menu']],
            [BUTTONS['delivery'], BUTTONS['order']],
            [BUTTONS['contacts'], BUTTONS['about']],
            [BUTTONS['cancel_order']]
        ],
        'resize_keyboard': True
    }


def get_cancel_keyboard():
    """Клавиатура отмены"""
    return {
        'keyboard': [
            [BUTTONS['cancel']]
        ],
        'resize_keyboard': True
    }


def get_payment_keyboard():
    """Клавиатура выбора оплаты"""
    return {
        'keyboard': [
            [BUTTONS['cash'], BUTTONS['card']],
            [BUTTONS['cancel']]
        ],
        'resize_keyboard': True
    }


# ================== УПРАВЛЕНИЕ ЗАКАЗАМИ ==================
def load_orders():
    if not os.path.exists(ORDERS_FILE):
        return {}

    try:
        with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}


def save_order_to_history(order_num, client_name, client_id, phone, address, order_text, order_type, payment_method):
    orders = load_orders()

    orders[str(order_num)] = {
        'client_name': str(client_name).strip()[:100],
        'client_id': client_id,
        'phone': str(phone).strip()[:20],
        'address': str(address).strip()[:200],
        'order_text': str(order_text).strip()[:500],
        'order_type': order_type,
        'payment_method': payment_method,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'active'
    }

    try:
        with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(orders, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False


# ================== ОСНОВНОЙ ЦИКЛ ==================
user_states = {}
last_id = 0

try:
    while True:
        try:
            url = f"{BASE_URL}/getUpdates?offset={last_id + 1}&timeout=20"
            resp = requests.get(url, timeout=25)
            data = resp.json()

            if data.get('result'):
                for update in data['result']:
                    last_id = update['update_id']

                    if 'message' in update:
                        msg = update['message']
                        chat_id = msg['chat']['id']
                        text = msg.get('text', '').strip()
                        name = msg['chat'].get('first_name', 'Клиент')

                        if not text:
                            continue

                        print(f"👤 {name}: {text}")

                        # КОМАНДЫ - сравниваем с кнопками из конфига
                        if text == '/start':
                            user_states.pop(chat_id, None)
                            welcome_msg = f"👋 Привет, {name}!\n\nДобро пожаловать в PIRAJOK 🍔\nВыберите действие:"
                            send_message(chat_id, welcome_msg, get_main_keyboard())

                        elif text == BUTTONS['menu']:
                            send_message(chat_id, get_menu_text())

                        elif text == BUTTONS['delivery']:
                            user_states[chat_id] = {
                                'state': 'choosing_payment',
                                'name': name,
                                'order_type': 'Доставка',
                                'payment_method': '',
                                'phone': '',
                                'address': '',
                                'order_text': ''
                            }
                            send_message(chat_id, CONFIG['messages']['delivery_info'], get_payment_keyboard())

                        elif text == BUTTONS['order']:
                            user_states[chat_id] = {
                                'state': 'waiting_for_phone',
                                'name': name,
                                'order_type': 'Заказать',
                                'payment_method': 'Наличные',
                                'phone': '',
                                'address': 'Самовывоз',
                                'order_text': ''
                            }
                            send_message(chat_id, CONFIG['messages']['order_start'], get_cancel_keyboard())

                        elif text == BUTTONS['contacts']:
                            send_message(chat_id, get_contacts_text())

                        elif text == BUTTONS['about']:
                            send_message(chat_id, get_about_text())

                        elif text == BUTTONS['cancel_order']:
                            send_message(chat_id, "❌ Функция отмены временно недоступна", get_main_keyboard())

                        elif text.lower() in ['отмена', 'отменить', 'cancel', 'стоп'] or text == BUTTONS['cancel']:
                            if chat_id in user_states:
                                send_message(chat_id, CONFIG['messages']['order_canceled'], get_main_keyboard())
                                user_states.pop(chat_id, None)

                        elif text == BUTTONS['cash']:
                            if chat_id in user_states and user_states[chat_id]['state'] == 'choosing_payment':
                                user_states[chat_id]['payment_method'] = 'Наличные'
                                user_states[chat_id]['state'] = 'waiting_for_phone'
                                send_message(chat_id, CONFIG['messages']['payment_cash'], get_cancel_keyboard())

                        elif text == BUTTONS['card']:
                            if chat_id in user_states and user_states[chat_id]['state'] == 'choosing_payment':
                                user_states[chat_id]['payment_method'] = 'Картой'
                                user_states[chat_id]['state'] = 'waiting_for_phone'
                                send_message(chat_id, CONFIG['messages']['payment_card'], get_cancel_keyboard())

                        elif chat_id in user_states and user_states[chat_id]['state'] == 'waiting_for_phone':
                            if not validate_phone(text):
                                send_message(chat_id,
                                             "❌ Введите корректный номер телефона:\n"
                                             "Пример: +7 (999) 123-45-67")
                                continue

                            user_states[chat_id]['phone'] = text

                            if user_states[chat_id]['order_type'] == 'Заказать':
                                user_states[chat_id]['state'] = 'waiting_for_order'
                                send_message(chat_id,
                                             f"✅ Телефон: {text}\n\n"
                                             f"Что хотите заказать?\n\n"
                                             f"{CONFIG['messages']['order_example']}",
                                             get_cancel_keyboard())
                            else:
                                user_states[chat_id]['state'] = 'waiting_for_address'
                                send_message(chat_id,
                                             f"✅ Телефон: {text}\n\n"
                                             f"Введите адрес доставки:\n\n"
                                             f"Пример: ул. Ленина 10, кв. 25",
                                             get_cancel_keyboard())

                        elif chat_id in user_states and user_states[chat_id]['state'] == 'waiting_for_address':
                            if len(text) < 5:
                                send_message(chat_id, "❌ Введите полный адрес:")
                                continue

                            user_states[chat_id]['address'] = text
                            user_states[chat_id]['state'] = 'waiting_for_order'
                            send_message(chat_id,
                                         f"✅ Адрес: {text}\n\n"
                                         f"Что хотите заказать?\n\n"
                                         f"{CONFIG['messages']['order_example']}",
                                         get_cancel_keyboard())

                        elif chat_id in user_states and user_states[chat_id]['state'] == 'waiting_for_order':
                            if len(text) < 10:
                                send_message(chat_id, "❌ Опишите заказ подробнее:")
                                continue

                            current_order = order_number
                            order_data = user_states[chat_id]

                            if save_order_to_history(current_order, name, chat_id,
                                                     order_data['phone'], order_data['address'],
                                                     text, order_data['order_type'],
                                                     order_data['payment_method']):

                                if send_order_to_admin(current_order, name, chat_id,
                                                       order_data['phone'], order_data['address'],
                                                       text, order_data['order_type'],
                                                       order_data['payment_method']):

                                    print(f"✅ Заказ #{current_order} отправлен")
                                    save_order_number(current_order)
                                    order_number += 1

                                    confirmation = (
                                        f"✅ Заказ номер #{current_order} оформлен\n\n"
                                        f"Тип: {order_data['order_type']}\n"
                                        f"Телефон: {order_data['phone']}\n"
                                        f"{'Адрес: ' + order_data['address'] if order_data['order_type'] == 'Доставка' else 'Самовывоз'}\n\n"
                                        f"Благодарим за ваш заказ! Скоро с вами свяжутся."
                                    )

                                    send_message(chat_id, confirmation, get_main_keyboard())
                                else:
                                    send_message(chat_id,
                                                 "❌ Ошибка отправки заказа\n"
                                                 f"Позвоните: {CONFIG['contacts']['phone']}",
                                                 get_main_keyboard())
                            else:
                                send_message(chat_id,
                                             "❌ Ошибка оформления заказа\n"
                                             "Попробуйте еще раз",
                                             get_main_keyboard())

                            user_states.pop(chat_id, None)

                        else:
                            send_message(chat_id, "🤔 Выберите действие из меню ⬇️", get_main_keyboard())

            time.sleep(0.5)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"⚠️ Ошибка: {e}")
            time.sleep(2)

except KeyboardInterrupt:
    print("\n👋 Бот остановлен")
    save_order_number(order_number - 1)

print(f"\n📊 Всего заказов: {order_number - 1}")
print(f"📁 Следующий заказ будет: #{order_number}")
