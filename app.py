#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 PIRAJOK TELEGRAM BOT
Версия с вебхуками для GitHub Actions
"""

import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify
import telebot
from telebot import types

# ================== НАСТРОЙКИ ==================
BOT_TOKEN = os.getenv('BOT_TOKEN', 'ВАШ_ТОКЕН_ЗДЕСЬ')
ADMIN_ID = os.getenv('ADMIN_ID', '757172736')

# Создаем Flask приложение
app = Flask(__name__)

# Создаем бота
bot = telebot.TeleBot(BOT_TOKEN)

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ================== БАЗА ДАННЫХ ==================
DB_FILE = 'data.json'

def load_db():
    """Загружает базу данных"""
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {
            "orders": [],
            "last_order": 0,
            "users": {},
            "stats": {"total": 0, "today": 0}
        }

def save_db(data):
    """Сохраняет базу данных"""
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения: {e}")
        return False

# ================== КОМАНДЫ БОТА ==================
@bot.message_handler(commands=['start'])
def start_command(message):
    """Обработка /start"""
    user = message.from_user
    db = load_db()
    
    # Регистрируем пользователя
    if str(user.id) not in db["users"]:
        db["users"][str(user.id)] = {
            "name": user.first_name,
            "username": user.username,
            "joined": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "orders": 0
        }
        save_db(db)
    
    # Создаем клавиатуру
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    items = ['📋 Меню', '🚚 Доставка', '🛒 Самовывоз', '📞 Контакты', '🏠 О нас', '❌ Отменить']
    buttons = [types.KeyboardButton(item) for item in items]
    markup.add(*buttons)
    
    welcome_text = f"""
👋 Привет, {user.first_name}!

Добро пожаловать в *PIRAJOK* 🥟
Самые вкусные пирожки в городе!

👇 *Выберите действие:*
"""
    
    bot.send_message(
        message.chat.id,
        welcome_text,
        parse_mode='Markdown',
        reply_markup=markup
    )
    logger.info(f"Новый пользователь: {user.first_name}")

@bot.message_handler(func=lambda m: m.text == '📋 Меню')
def show_menu(message):
    """Показывает меню"""
    menu = """
*🍽️ МЕНЮ PIRAJOK*

*🥟 ПИРОЖКИ (150г):*
• С мясом — 150₽
• С капустой — 120₽
• С вишней — 130₽
• С творогом — 125₽

*🥤 НАПИТКИ:*
• Компот — 50₽
• Чай — 40₽
• Кофе — 80₽

*🧁 ДЕСЕРТЫ:*
• Ватрушка — 100₽
• Печенье (3шт) — 80₽

*🔥 АКЦИЯ:* Заказ от 500₽ — компот в подарок!
"""
    bot.send_message(message.chat.id, menu, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '🚚 Доставка')
def start_delivery(message):
    """Начинает оформление доставки"""
    msg = bot.send_message(
        message.chat.id,
        "🚚 *ОФОРМЛЕНИЕ ДОСТАВКИ*\n\n"
        "Пожалуйста, введите ваш *адрес доставки*:",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, process_address)

def process_address(message):
    """Обрабатывает адрес"""
    address = message.text
    msg = bot.send_message(
        message.chat.id,
        f"✅ Адрес: {address}\n\n"
        "Теперь введите ваш *номер телефона*:",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, process_phone, address)

def process_phone(message, address):
    """Обрабатывает телефон"""
    phone = message.text
    msg = bot.send_message(
        message.chat.id,
        f"✅ Телефон: {phone}\n\n"
        "📝 *Что хотите заказать?*",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, finalize_order, address, phone)

def finalize_order(message, address, phone):
    """Завершает оформление заказа"""
    order_text = message.text
    user = message.from_user
    
    # Сохраняем заказ
    db = load_db()
    order_id = db["last_order"] + 1
    
    order = {
        "id": order_id,
        "user_id": user.id,
        "user_name": user.first_name,
        "phone": phone,
        "address": address,
        "order": order_text,
        "type": "delivery",
        "status": "new",
        "time": datetime.now().strftime('%H:%M %d.%m.%Y')
    }
    
    db["orders"].append(order)
    db["last_order"] = order_id
    db["stats"]["total"] += 1
    save_db(db)
    
    # Подтверждение клиенту
    bot.send_message(
        message.chat.id,
        f"""
✅ *ЗАКАЗ #{order_id} ПРИНЯТ!*

🍽️ *Заказ:* {order_text}
📍 *Адрес:* {address}
📱 *Телефон:* {phone}
🚚 *Тип:* Доставка
⏰ *Время:* {order['time']}

*Скоро с вами свяжутся!*
        """,
        parse_mode='Markdown'
    )
    
    # Уведомление админу
    try:
        bot.send_message(
            ADMIN_ID,
            f"""
🆕 *НОВЫЙ ЗАКАЗ #{order_id}*
👤 *Клиент:* {user.first_name}
📱 *Телефон:* {phone}
📍 *Адрес:* {address}
📦 *Заказ:* {order_text}
⏰ *Время:* {order['time']}
            """,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Ошибка уведомления админа: {e}")

@bot.message_handler(func=lambda m: m.text == '📞 Контакты')
def show_contacts(message):
    """Показывает контакты"""
    contacts = """
*📞 КОНТАКТЫ PIRAJOK*

📍 *Адрес:* ул. Пирожковая, 15
📱 *Телефон:* +7 (999) 123-45-67
⏰ *Часы работы:* 9:00–21:00
📧 *Email:* order@pirajok.ru

💬 *Telegram:* @armanayvazyan
    """
    bot.send_message(message.chat.id, contacts, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == '❌ Отменить')
def cancel_order(message):
    """Отмена заказа"""
    user_id = message.from_user.id
    db = load_db()
    
    # Ищем активные заказы
    active_orders = [
        o for o in db["orders"] 
        if o["user_id"] == user_id and o["status"] == "new"
    ]
    
    if not active_orders:
        bot.send_message(message.chat.id, "❌ У вас нет активных заказов.")
        return
    
    # Отменяем
    cancelled = []
    for order in active_orders:
        order["status"] = "cancelled"
        order["cancelled_at"] = datetime.now().strftime('%H:%M %d.%m.%Y')
        cancelled.append(order["id"])
    
    save_db(db)
    
    if cancelled:
        orders_str = ", ".join([f"#{id}" for id in cancelled])
        bot.send_message(
            message.chat.id,
            f"✅ Отменены заказы: {orders_str}"
        )

# ================== WEBHOOK РОУТЫ ==================
@app.route('/')
def home():
    """Главная страница"""
    db = load_db()
    return jsonify({
        "status": "online",
        "bot": "PIRAJOK",
        "orders": db["stats"]["total"],
        "users": len(db["users"]),
        "time": datetime.now().isoformat()
    })

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook от Telegram"""
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK'
    return 'Bad Request', 400

@app.route('/health')
def health():
    """Health check"""
    return 'OK', 200

# ================== ЗАПУСК ==================
if __name__ == '__main__':
    logger.info("🤖 Запуск PIRAJOK бота...")
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
