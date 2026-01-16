"""
Telegram Bot для автоматического заполнения Google Формы "Мана"
Использует: python-telegram-bot, requests
"""

import os
import re
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ============= КОНФИГУРАЦИЯ =============
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')  # Получаем из переменных окружения
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSeX-er8kGUTT72qEDZjgJX_E6Gmj9qnyVTZ_jQNbgOCdLf91g/formResponse"

# ID полей в Google Форме
FIELD_DEPARTMENT = "entry.947326788"
FIELD_EMPLOYEE = "entry.2052209930"
FIELD_PROJECT = "entry.1743944322"
FIELD_SCORE = "entry.44696242"

# Список всех проектов из формы (для проверки)
VALID_PROJECTS = [
    "NewBiz (тендеры)",
    "NewBiz (агентское промо/смм)",
    "Прочее (то, что не относится к конкретному проекту / база знаний)",
    "HR (найм, онбординг сотрудника и пр.)",
    "А деньги / SMM",
    "А деньги / Perf",
    "Академия ИИ / SMM",
    "Академия ИИ / Perf",
    "АК Барс / SMM",
    "АК Барс / Perf",
    "ВТБ / SMM",
    "ВТБ / Perf",
    "ВТБ ИХ / Perf",
    "ЛСР / SMM",
    "ЛСР / Perf",
    "СберОбразование",
    "Страна / SMM",
    "Страна / Perf",
    "Центр-инвест / SMM",
    "Центр-Инвест / Perf",
    "Школа Мосбиржи / SMM",
    "Школа Мосбиржи / Perf",
    "RBI / SMM",
    "RBI / Perf",
    "Chad",
    "Posters",
    "Icloud",
    "A&K",
    "Азбука Аттикус",
    "Ренессанс",
    "Аспектум"
]

# Список всех сотрудников из формы
VALID_EMPLOYEES = [
    "Голикова Ксения",
    "Казакова Мария",
    "Павлова Валерия",
    "Рябцева Александра",
    "Шабловская Екатерина",
    "Степанова Юлия",
    "Куминова Мария",
    "Гмырак Алексей",
    "Маринина Анастасия",
    "Ракчеева Ксения",
    "Чистяков Кирилл",
    "Шарапова Мария",
    "Швецов Денис",
    "Даниленко Павел",
    "Дюкова Мария",
    "Заколпская София",
    "Игнатович Ксения",
    "Исаков Никита",
    "Кириллова Варвара",
    "Коханова Татьяна",
    "Липатова Екатерина",
    "Трохинова Марина",
    "Трусова Вероника",
    "Хрулёв Роман",
    "Бударова Анастасия",
    "Иванов Александр",
    "Кузнецов Иван",
    "Наумычев Вячеслав",
    "Пичейкин Антоний",
    "Текучева Мария",
    "Толкачева Валерия",
    "Федосеенко Лина",
    "Ткаленко Евгений",
    "Сарычева Елизавета",
    "Кононенко Кристина",
    "Чуйко Юлия",
    "Шишлякова Алёна"
]

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============= ДАННЫЕ ПОЛЬЗОВАТЕЛЯ =============
user_data = {}

# ============= ФУНКЦИИ =============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    await update.message.reply_text(
        "👋 Привет! Я помогу тебе быстро заполнить форму Маны!\n\n"
        "Напиши свое имя и фамилию (как в списке сотрудников):"
    )

async def handle_employee_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка имени сотрудника"""
    employee_name = update.message.text.strip()
    user_id = update.effective_user.id
    
    # Проверяем, есть ли такой сотрудник в списке
    if employee_name not in VALID_EMPLOYEES:
        await update.message.reply_text(
            f"❌ Сотрудник '{employee_name}' не найден в списке.\n\n"
            "Пожалуйста, напиши имя точно так, как оно указано в форме.\n"
            "Попробуй еще раз:"
        )
        return
    
    # Сохраняем имя в контексте пользователя
    user_data[user_id] = {
        'employee': employee_name,
        'department': None,
        'projects': {}
    }
    
    await update.message.reply_text(
        f"✅ Спасибо, {employee_name}!\n\n"
        "Теперь напиши свои проекты и оценки в формате:\n"
        "<b>Проект1 - балл, Проект2 - балл, Проект3 - балл</b>\n\n"
        "Например:\n"
        "<b>ВТБ / SMM - 5, РБИ / SMM - 3, СберОбразование - 2</b>\n\n"
        "Баллы: от 1 до 10\n"
        "Сумма всех баллов не может быть больше 10!",
        parse_mode='HTML'
    )
    
    # Переходим в режим ожидания проектов
    context.user_data[user_id] = 'waiting_projects'

async def handle_projects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка проектов и оценок"""
    user_id = update.effective_user.id
    message_text = update.message.text.strip()
    
    # Проверяем, есть ли данные о сотруднике
    if user_id not in user_data:
        await update.message.reply_text(
            "❌ Ошибка: сначала напиши свое имя.\n"
            "/start - для начала заново"
        )
        return
    
    # Парсим формат: "Проект - балл, Проект - балл"
    projects_pattern = r'([^-,]+?)\s*-\s*(\d+)'
    matches = re.findall(projects_pattern, message_text)
    
    if not matches:
        await update.message.reply_text(
            "❌ Неверный формат!\n\n"
            "Используй формат:\n"
            "<b>Проект1 - балл, Проект2 - балл</b>\n\n"
            "Пример:\n"
            "<b>ВТБ / SMM - 5, РБИ / SMM - 3</b>",
            parse_mode='HTML'
        )
        return
    
    # Валидируем проекты и баллы
    projects = {}
    total_score = 0
    errors = []
    
    for project_name, score_str in matches:
        project_name = project_name.strip()
        
        try:
            score = int(score_str)
            if score < 1 or score > 10:
                errors.append(f"❌ '{project_name}': балл должен быть от 1 до 10")
                continue
        except ValueError:
            errors.append(f"❌ '{project_name}': некорректный балл")
            continue
        
        # Проверяем наличие проекта в списке
        if project_name not in VALID_PROJECTS:
            errors.append(f"❌ Проект '{project_name}' не найден в списке")
            continue
        
        projects[project_name] = score
        total_score += score
    
    # Проверяем сумму баллов
    if total_score > 10:
        await update.message.reply_text(
            f"❌ Сумма баллов = {total_score}, а максимум = 10!\n\n"
            "Пожалуйста, перераспредели баллы так, чтобы сумма была ≤ 10."
        )
        return
    
    # Если были ошибки, выводим их
    if errors:
        error_text = "\n".join(errors)
        await update.message.reply_text(
            f"{error_text}\n\n"
            "Проверь названия проектов и попробуй еще раз."
        )
        return
    
    if not projects:
        await update.message.reply_text(
            "❌ Не удалось распарсить ни один проект.\n"
            "Попробуй еще раз."
        )
        return
    
    # Сохраняем проекты
    user_data[user_id]['projects'] = projects
    
    # Показываем подтверждение
    projects_text = "\n".join([f"• {proj}: {score} баллов" for proj, score in projects.items()])
    await update.message.reply_text(
        f"📋 Твои данные:\n\n"
        f"<b>Сотрудник:</b> {user_data[user_id]['employee']}\n\n"
        f"<b>Проекты:</b>\n{projects_text}\n\n"
        f"<b>Сумма баллов:</b> {total_score}/10\n\n"
        "⏳ Заполняю форму...",
        parse_mode='HTML'
    )
    
    # Заполняем форму
    await fill_form(update, context, user_id)

async def fill_form(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Автоматически заполняет Google Форму"""
    import requests
    
    employee = user_data[user_id]['employee']
    projects = user_data[user_id]['projects']
    
    # Определяем отдел по сотруднику (упрощённо - берём первый символ)
    # В реальности можно создать маппинг сотрудник -> отдел
    department = "Проектный офис"  # По умолчанию
    
    # Заполняем форму для каждого проекта
    successful = 0
    failed = 0
    
    for project_name, score in projects.items():
        try:
            # Данные для отправки в форму
            form_data = {
                FIELD_DEPARTMENT: department,
                FIELD_EMPLOYEE: employee,
                FIELD_PROJECT: project_name,
                FIELD_SCORE: str(score)
            }
            
            # Отправляем POST запрос
            response = requests.post(FORM_URL, data=form_data, timeout=10)
            
            if response.status_code == 200:
                successful += 1
                logger.info(f"✅ Заполнена форма для {employee} -> {project_name} ({score})")
            else:
                failed += 1
                logger.error(f"❌ Ошибка при заполнении для {project_name}: {response.status_code}")
        
        except Exception as e:
            failed += 1
            logger.error(f"❌ Исключение при заполнении {project_name}: {str(e)}")
    
    # Выводим результат
    if successful == len(projects):
        await update.message.reply_text(
            f"✅ Отлично! Успешно заполнена {successful} форм{'ы' if successful != 1 else ''}!\n\n"
            f"Сэкономил тебе около 5-10 минут работы 🎉\n\n"
            "Спасибо, что используешь бота!\n"
            "/start - для новой заявки"
        )
    else:
        await update.message.reply_text(
            f"⚠️ Результат:\n"
            f"✅ Успешно: {successful}\n"
            f"❌ Ошибок: {failed}\n\n"
            f"Свяжись с администратором, если что-то пошло не так.\n"
            "/start - для новой заявки"
        )
    
    # Очищаем данные пользователя
    if user_id in user_data:
        del user_data[user_id]

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    await update.message.reply_text(
        "📖 <b>Как использовать бота:</b>\n\n"
        "1️⃣ Напиши /start\n"
        "2️⃣ Укажи свое имя и фамилию\n"
        "3️⃣ Напиши проекты и баллы в формате:\n"
        "   <b>Проект1 - балл, Проект2 - балл</b>\n\n"
        "4️⃣ Бот автоматически заполнит форму!\n\n"
        "⚠️ <b>Важно:</b>\n"
        "• Сумма баллов не может быть больше 10\n"
        "• Баллы от 1 до 10\n"
        "• Названия проектов должны совпадать с формой",
        parse_mode='HTML'
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /cancel - отмена"""
    user_id = update.effective_user.id
    if user_id in user_data:
        del user_data[user_id]
    
    await update.message.reply_text(
        "❌ Отменено.\n"
        "/start - для начала заново"
    )

# ============= MAIN =============

def main():
    """Запуск бота"""
    if not TELEGRAM_TOKEN:
        raise ValueError("❌ TELEGRAM_TOKEN не установлен!")
    
    # Создаём приложение
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cancel", cancel))
    
    # Обработчик сообщений
    # Если пользователь в режиме ввода проектов - обрабатываем проекты
    def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        # Если это первое сообщение (имя сотрудника)
        if user_id not in user_data:
            return handle_employee_name(update, context)
        # Если ждём проекты
        else:
            return handle_projects(update, context)
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, 
                                   lambda u, c: handle_employee_name(u, c) if u.effective_user.id not in user_data 
                                   else handle_projects(u, c)))
    
    # Запускаем бота
    logger.info("🤖 Бот запущен! Ожидаю сообщения...")
    app.run_polling()

if __name__ == '__main__':
    main()