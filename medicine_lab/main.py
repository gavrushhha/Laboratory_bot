import sqlite3
import telebot
import pandas as pd
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from datetime import datetime
import os

TOKEN = "7857050136:AAE-ZyTtmR8VCAQgeWJdTbPFf4IFk-qAI0M"
ADMIN_ID = [767393993, 355829421, 870756798]
bot = telebot.TeleBot(TOKEN)

# 🔹 Подключение к базе данных
# Подключение к базе данных
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "bot_database.db")

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# Создание таблиц
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER UNIQUE,
    full_name TEXT,
    department TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    sample_id TEXT,
    mass_or_concentration TEXT,
    project TEXT,
    study_type TEXT,
    note TEXT,
    timestamp TEXT,
    solvent TEXT, 
    expected_result TEXT,
    FOREIGN KEY (user_id) REFERENCES users (id)
)
''')
conn.commit()

# Клавиатура для ожидаемого результата
kb_expected_result = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
kb_expected_result.add("Протокол по форме", "RAW-data", "Приборный отчёт", "Не требуется")

# Клавиатура выбора растворителя
kb_solvents = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
kb_solvents.add("ACN 100%", "ACN 70%", "MeOH", "Другое")

kb_user = ReplyKeyboardMarkup(resize_keyboard=True).add(
    KeyboardButton("Создать заявку"), 
    KeyboardButton("Зарегистрироваться")
)

kb_admin = ReplyKeyboardMarkup(resize_keyboard=True).add(
    # KeyboardButton("Просмотреть все заявки"),
    KeyboardButton("Сформировать отчет"), 
    KeyboardButton("Просмотреть пользователей"), 
    KeyboardButton("Удалить заявку") 
)

projects = ["CSE", "LPS", "Selexipag", "Risdiplam", "Ataluren", "Bromantane", "GLP1R", "Другое"]
kb_projects = ReplyKeyboardMarkup(resize_keyboard=True)
for project in projects:
    kb_projects.add(KeyboardButton(project))

study_types = [
    "Анализ реакционной смеси (ГХ-МС-ПИД)",
    "Анализ реакционной смеси (ВЭЖХ-УФ-МС)"
]
kb_study_types = ReplyKeyboardMarkup(resize_keyboard=True)
for study in study_types:
    kb_study_types.add(KeyboardButton(study))

@bot.message_handler(commands=['start'])
def start_command(message):
    cursor.execute("SELECT id FROM users WHERE tg_id = ?", (message.from_user.id,))
    user = cursor.fetchone()

    if message.chat.id in ADMIN_ID:
        bot.send_message(message.chat.id, "Привет, админ! Выберите действие:", reply_markup=kb_admin)
    elif user:
        # Если пользователь зарегистрирован, сразу показываем кнопки для создания заявки
        bot.send_message(message.chat.id, "Привет! Выберите действие:", reply_markup=kb_user)
    else:
        # Если пользователь не зарегистрирован, показываем кнопку только для регистрации
        kb_register = ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("Зарегистрироваться"))
        bot.send_message(message.chat.id, "Привет! Вам нужно зарегистрироваться.", reply_markup=kb_register)

@bot.message_handler(func=lambda message: message.text == "Зарегистрироваться")
def register_user(message):
    cursor.execute("SELECT id FROM users WHERE tg_id = ?", (message.from_user.id,))
    user = cursor.fetchone()

    if user:
        bot.send_message(message.chat.id, "Вы уже зарегистрированы!", reply_markup=kb_user)
    else:
        bot.send_message(message.chat.id, "Введите ваше ФИО:")
        bot.register_next_step_handler(message, get_full_name)

def get_full_name(message):
    full_name = message.text
    bot.send_message(message.chat.id, "Введите ваше направление:")
    bot.register_next_step_handler(message, lambda msg: save_user(msg, message.from_user.id, full_name))

def save_user(message, tg_id, full_name):
    department = message.text

    cursor.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,))
    user_exists = cursor.fetchone()

    if user_exists:
        bot.send_message(message.chat.id, "Вы уже зарегистрированы!", reply_markup=kb_user)
        return

    cursor.execute("INSERT INTO users (tg_id, full_name, department) VALUES (?, ?, ?)", (tg_id, full_name, department))
    conn.commit()

    # После успешной регистрации показываем клавиатуру с кнопкой для создания заявки
    bot.send_message(message.chat.id, "✅ Вы успешно зарегистрированы!", reply_markup=kb_user)


@bot.message_handler(func=lambda message: message.text == "Создать заявку")
def create_request(message):
    cursor.execute("SELECT id FROM users WHERE tg_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    if not user:
        bot.send_message(message.chat.id, "Сначала зарегистрируйтесь!")
        return
    bot.send_message(message.chat.id, "Введите ID образца:", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(message, lambda msg: ask_mass_or_concentration(msg, user[0]))

def ask_mass_or_concentration(message, user_id):
    sample_id = message.text
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Масса (мг)", "Объем/концентрация (мкл - мг/мл)")
    bot.send_message(message.chat.id, "Выберите: масса (мг) или объем/концентрация (мкл - мг/мл)", reply_markup=markup)
    bot.register_next_step_handler(message, lambda msg: ask_user_input_for_mass_or_concentration(msg, user_id, sample_id))

def ask_user_input_for_mass_or_concentration(message, user_id, sample_id):
    # Сохраняем, что выбрал пользователь
    # selected_option = message.text

    # Запрашиваем ввод от пользователя
    bot.send_message(message.chat.id, "Пожалуйста, введите значение (например, 5.5 мг или 10 мкл - мг/мл):")
    bot.register_next_step_handler(message, lambda msg: ask_project(msg, user_id, sample_id, msg.text))


def ask_project(message, user_id, sample_id, user_input):
    mass_or_concentration = user_input
    bot.send_message(message.chat.id, "Выберите проект:", reply_markup=kb_projects)
    bot.register_next_step_handler(message, lambda msg: ask_study_type(msg, user_id, sample_id, mass_or_concentration, msg.text))

def ask_study_type(message, user_id, sample_id, mass_or_concentration, project):
    bot.send_message(message.chat.id, "Выберите тип исследования:", reply_markup=kb_study_types)
    bot.register_next_step_handler(message, lambda msg: ask_solvent(msg, user_id, sample_id, mass_or_concentration, project, msg.text))

def ask_solvent(message, user_id, sample_id, mass_or_concentration, project, study_type):
    bot.send_message(message.chat.id, "Выберите растворитель:", reply_markup=kb_solvents)
    bot.register_next_step_handler(message, lambda msg: handle_solvent(msg, user_id, sample_id, mass_or_concentration, project, study_type))

def handle_solvent(message, user_id, sample_id, mass_or_concentration, project, study_type):
    if message.text == "Другое":
        bot.send_message(message.chat.id, "Введите название растворителя вручную:", reply_markup=ReplyKeyboardRemove())
        bot.register_next_step_handler(message, lambda msg: ask_expected_result(msg, user_id, sample_id, mass_or_concentration, project, study_type, msg.text))
    else:
        ask_expected_result(message, user_id, sample_id, mass_or_concentration, project, study_type, message.text)

def ask_expected_result(message, user_id, sample_id, mass_or_concentration, project, study_type, solvent):
    bot.send_message(message.chat.id, "Выберите ожидаемый результат анализа:", reply_markup=kb_expected_result)
    bot.register_next_step_handler(message, lambda msg: ask_note(msg, user_id, sample_id, mass_or_concentration, project, study_type, solvent, msg.text))


def ask_note(message, user_id, sample_id, mass_or_concentration, project, study_type, solvent, expected_result):
    bot.send_message(message.chat.id, "Введите примечание:", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(message, lambda msg: save_request(msg, user_id, sample_id, mass_or_concentration, project, study_type, solvent, expected_result))

def save_request(message, user_id, sample_id, mass_or_concentration, project, study_type, solvent, expected_result):
    note = message.text
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Получаем ФИО заказчика
    cursor.execute("SELECT full_name FROM users WHERE id = ?", (user_id,))
    user_data = cursor.fetchone()
    full_name = user_data[0] if user_data else "Неизвестный пользователь"

    # Сохраняем заявку в БД
    cursor.execute("INSERT INTO requests (user_id, sample_id, mass_or_concentration, project, study_type, note, timestamp, solvent, expected_result) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, sample_id, mass_or_concentration, project, study_type, note, timestamp, solvent, expected_result))
    conn.commit()

    # Получаем ID только что вставленной заявки
    request_id = cursor.lastrowid

    # Сообщение пользователю с ID заявки
    bot.send_message(message.chat.id, f"✅ Заявка успешно создана! ID заявки: {request_id}", reply_markup=kb_user)

    # Уведомление админу с ФИО заказчика
    for admin in ADMIN_ID:
        try:
            bot.send_message(admin, f"📌 Новая заявка!\n👤 Заказчик: {full_name}\n🔹 ID заявки: {request_id}\n🔹 ID образца: {sample_id}\n⚖ Масса/концентрация: {mass_or_concentration}\n📂 Проект: {project}\n🔬 Исследование: {study_type}\n🧪 Растворитель: {solvent}\n📄 Ожидаемый результат: {expected_result}\n📝 Примечание: {note}\n")
        except Exception as e:
            print(f"Ошибка при отправке сообщения админу {admin}: {e}")


# =======================
# 🔹 Просмотр всех заявок (для админа)
# =======================
# @bot.message_handler(func=lambda message: message.text == "Просмотреть все заявки")
# def view_requests(message):
#     if message.chat.id not in ADMIN_ID:  # Проверяем, что пользователь - админ
#         return

#     cursor.execute('''
#         SELECT r.id, r.sample_id, r.mass_or_concentration, r.project, r.study_type, u.full_name, r.timestamp, r.note, r.solvent 
#         FROM requests r 
#         JOIN users u ON r.user_id = u.id
#     ''')
#     requests = cursor.fetchall()

#     if not requests:
#         bot.send_message(message.chat.id, "Нет активных заявок.")
#         return

#     response = "📌 Список заявок:\n"
#     for req in requests:
#         response += (f"🔹 ID заявки: {req[0]}\n"
#                         f"📌 ID образца: {req[1]}\n"
#                         f"⚖ Масса/концентрация: {req[2]}\n"
#                         f"📂 Проект: {req[3]}\n"
#                         f"🔬 Исследование: {req[4]}\n"
#                         f"👤 Заказчик: {req[5]}\n"
#                         f"📅 Дата: {req[6]}\n"
#                         f"🧪 Растворитель: {req[8]}\n"
#                         f"📝 Примечание: {req[7]}\n"
#                         "----------------------\n")

#     bot.send_message(message.chat.id, response)

# =======================
# 🔹 Формирование отчёта в Excel (для админа)
# =======================
@bot.message_handler(func=lambda message: message.text == "Сформировать отчет")
def generate_report(message):
    if message.chat.id not in ADMIN_ID:  # Проверяем, что пользователь - админ
        return
    cursor.execute('''
        SELECT r.sample_id, u.full_name, r.mass_or_concentration, r.project, 
               r.timestamp, r.study_type, r.solvent, r.expected_result, r.note 
        FROM requests r 
        JOIN users u ON r.user_id = u.id
    ''')
    requests = cursor.fetchall()

    if not requests:
        bot.send_message(message.chat.id, "Нет данных для отчёта.")
        return

    df = pd.DataFrame(requests, columns=[
        "ID образца", "Заказчик", "Масса/Концентрация", "Проект", 
        "Дата заявки", "Тип исследования", "Растворитель", 
        "Ожидаемый результат", "Примечание"
    ])
    file_path = "report.xlsx"
    df.to_excel(file_path, index=False)

    with open(file_path, "rb") as file:
        bot.send_document(message.chat.id, file, caption="📄 Отчёт по заявкам")




@bot.message_handler(func=lambda message: message.text == "Просмотреть пользователей")
def view_users(message):
    if message.chat.id not in ADMIN_ID:
        return
    

    # conn = sqlite3.connect("bot_database.db") 
    # cursor = conn.cursor()
    
    cursor.execute("SELECT id, tg_id, full_name, department FROM users") 
    users = cursor.fetchall()


    if users:
        response = "Список пользователей:\n"
        for user in users:
            response += f"ID: {user[0]}, Telegram ID: {user[1]}, Имя: {user[2]}, Отдел: {user[3]}\n"
    else:
        response = "В базе данных нет пользователей."

    bot.send_message(message.chat.id, response)



@bot.message_handler(func=lambda message: message.text == "Удалить заявку")
def delete_request(message):
    if message.chat.id not in ADMIN_ID:  # Проверяем, что пользователь - админ
        return

    bot.send_message(message.chat.id, "Введите ID заявки, которую хотите удалить:", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(message, handle_delete_request)

def handle_delete_request(message):
    try:
        request_id = int(message.text)  # Преобразуем введенный текст в число

        # Проверяем, существует ли заявка с таким ID
        cursor.execute("SELECT id FROM requests WHERE id = ?", (request_id,))
        request = cursor.fetchone()

        if request:
            cursor.execute("DELETE FROM requests WHERE id = ?", (request_id,))
            conn.commit()
            bot.send_message(message.chat.id, f"✅ Заявка с ID {request_id} успешно удалена!")
        else:
            bot.send_message(message.chat.id, "❌ Заявка с таким ID не найдена.")
        
        # После удаления заявки (или в случае ошибки) отправляем клавиатуру с админскими кнопками
        bot.send_message(message.chat.id, "Выберите действие:", reply_markup=kb_admin)

    except ValueError:
        bot.send_message(message.chat.id, "❌ Пожалуйста, введите корректный ID заявки.")
        bot.send_message(message.chat.id, "Попробуйте снова:", reply_markup=ReplyKeyboardRemove())
        bot.register_next_step_handler(message, handle_delete_request)





# =======================
# 🔹 Запуск бота
# =======================
if __name__ == "__main__":
    print("Бот запущен...")
    bot.polling(none_stop=True)
