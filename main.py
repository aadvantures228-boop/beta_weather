import logging
import requests
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, CallbackContext,
    filters, MessageHandler, CallbackQueryHandler
)

# ==================== НАСТРОЙКИ ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Ключ API
weather_token = "e8677da6c554a5a738e4df8f0802c283"
BOT_TOKEN = "8507475399:AAFDXfVd9900GI1PDjlB8greQz5X4a-0RPE"

# ==================== ФУНКЦИИ ХРАНЕНИЯ ДАННЫХ ====================
def get_user_lang(context: CallbackContext, user_id: int):
    if 'lang' not in context.bot_data:
        context.bot_data['lang'] = {}
    if user_id not in context.bot_data['lang']:
        context.bot_data['lang'][user_id] = 'rus'
    return context.bot_data['lang'][user_id]

def set_user_lang(context: CallbackContext, user_id: int, lang: str):
    if 'lang' not in context.bot_data:
        context.bot_data['lang'] = {}
    context.bot_data['lang'][user_id] = lang

def get_user_region(context: CallbackContext, user_id: int):
    if 'region' not in context.bot_data:
        context.bot_data['region'] = {}
    if user_id not in context.bot_data['region']:
        context.bot_data['region'][user_id] = 'Moscow'
    return context.bot_data['region'][user_id]

def set_user_region(context: CallbackContext, user_id: int, region: str):
    if 'region' not in context.bot_data:
        context.bot_data['region'] = {}
    context.bot_data['region'][user_id] = region

def get_user_favorites(context: CallbackContext, user_id: int):
    if 'favorites' not in context.bot_data:
        context.bot_data['favorites'] = {}
    if user_id not in context.bot_data['favorites']:
        context.bot_data['favorites'][user_id] = []
    return context.bot_data['favorites'][user_id]

def add_user_favorite(context: CallbackContext, user_id: int, city: str):
    favorites = get_user_favorites(context, user_id)
    if city not in favorites:
        favorites.append(city)
        context.bot_data['favorites'][user_id] = favorites
        return True
    return False

def remove_user_favorite(context: CallbackContext, user_id: int, city: str):
    favorites = get_user_favorites(context, user_id)
    if city in favorites:
        favorites.remove(city)
        context.bot_data['favorites'][user_id] = favorites
        return True
    return False

def clear_user_favorites(context: CallbackContext, user_id: int):
    if 'favorites' not in context.bot_data:
        context.bot_data['favorites'] = {}
    context.bot_data['favorites'][user_id] = []

# ==================== ПОГОДНЫЕ ФУНКЦИИ ====================
def get_weather(city: str, lang: str = "ru") -> tuple:
    try:
        url = 'https://api.openweathermap.org/data/2.5/weather'
        params = {
            'q': city,
            'appid': weather_token,
            'units': 'metric',
            'lang': 'ru' if lang == 'rus' else 'en'
        }
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 404:
            return None, f"🌍 Город {city} не найден" if lang == 'rus' else f"🌍 City {city} not found"
        elif response.status_code != 200:
            return None, f"⚠️ Ошибка: код {response.status_code}" if lang == 'rus' else f"⚠️ Error: code {response.status_code}"
            
        data = response.json()
        temp = data['main']['temp']
        feels_like = data['main']['feels_like']
        humidity = data['main']['humidity']
        pressure_hpa = data['main']['pressure']
        wind_speed = data['wind']['speed']
        desc = data['weather'][0]['description']
        city_name = data['name']
        
        if lang == 'rus':
            pressure_display = f"{round(pressure_hpa * 0.750062)} мм рт. ст."
            text = (f"🌤️ Погода в {city_name}:\n"
                    f"🌡️ Температура: {temp}°C (ощущается как {feels_like}°C)\n"
                    f"📝 Описание: {desc}\n"
                    f"💧 Влажность: {humidity}%\n"
                    f"📊 Давление: {pressure_display}\n"
                    f"💨 Ветер: {wind_speed} м/с")
            
            extended_text = "\n📊 ДОПОЛНИТЕЛЬНЫЕ ДАННЫЕ:"
            added = False
            
            clouds = data['clouds'].get('all', 'Н/Д')
            extended_text += f"\n☁️ Облачность: {clouds}%"
            added = True
            
            wind_deg = data['wind'].get('deg')
            if wind_deg:
                directions = ["⬆️ Северный", "↗️ Северо-восточный", "➡️ Восточный", "↘️ Юго-восточный",
                              "⬇️ Южный", "↙️ Юго-западный", "⬅️ Западный", "↖️ Северо-западный"]
                idx = round(wind_deg / 45) % 8
                extended_text += f"\n💨 Направление: {directions[idx]}"
                added = True
                
            wind_gust = data['wind'].get('gust')
            if wind_gust:
                extended_text += f"\n💨 Порывы: {wind_gust} м/с"
                added = True
                
            sunrise = datetime.fromtimestamp(data['sys']['sunrise']).strftime('%H:%M')
            sunset = datetime.fromtimestamp(data['sys']['sunset']).strftime('%H:%M')
            extended_text += f"\n🌅 Восход: {sunrise}\n🌇 Закат: {sunset}"
            added = True
            
            if added:
                text += extended_text
        else:
            pressure_display = f"{pressure_hpa} hPa"
            text = (f"🌤️ Weather in {city_name}:\n"
                    f"🌡️ Temperature: {temp}°C (feels like {feels_like}°C)\n"
                    f"📝 Description: {desc}\n"
                    f"💧 Humidity: {humidity}%\n"
                    f"📊 Pressure: {pressure_display}\n"
                    f"💨 Wind: {wind_speed} m/s")
            
            extended_text = "\n📊 EXTENDED DATA:"
            added = False
            
            clouds = data['clouds'].get('all', 'N/A')
            extended_text += f"\n☁️ Cloudiness: {clouds}%"
            added = True
            
            wind_deg = data['wind'].get('deg')
            if wind_deg:
                directions = ["⬆️ North", "↗️ Northeast", "➡️ East", "↘️ Southeast",
                              "⬇️ South", "↙️ Southwest", "⬅️ West", "↖️ Northwest"]
                idx = round(wind_deg / 45) % 8
                extended_text += f"\n💨 Direction: {directions[idx]}"
                added = True
                
            wind_gust = data['wind'].get('gust')
            if wind_gust:
                extended_text += f"\n💨 Gust: {wind_gust} m/s"
                added = True
                
            sunrise = datetime.fromtimestamp(data['sys']['sunrise']).strftime('%H:%M')
            sunset = datetime.fromtimestamp(data['sys']['sunset']).strftime('%H:%M')
            extended_text += f"\n🌅 Sunrise: {sunrise}\n🌇 Sunset: {sunset}"
            added = True
            
            if added:
                text += extended_text
                
        return {'city': city_name, 'temp': temp}, text
    except Exception as e:
        return None, f'❌ Ошибка: {e}' if lang == 'rus' else f'❌ Error: {e}'

def get_forecast(city: str, lang: str = "ru"):
    try:
        url = 'https://api.openweathermap.org/data/2.5/forecast'
        params = {
            'q': city,
            'appid': weather_token,
            'units': 'metric',
            'lang': 'ru' if lang == 'rus' else 'en',
            'cnt': 40
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            return None, None, f"Ошибка: код {response.status_code}" if lang == 'rus' else f"Error: code {response.status_code}"
        data = response.json()
        return data['city']['name'], data['list'], None
    except Exception as e:
        return None, None, f'Ошибка: {e}' if lang == 'rus' else f'Error: {e}'

def get_daily_forecast(forecast_list, day_offset: int = 0):
    if not forecast_list:
        return None
    target_date = (datetime.now() + timedelta(days=day_offset)).date()
    day_forecasts = [f for f in forecast_list if datetime.fromtimestamp(f['dt']).date() == target_date]
    if not day_forecasts:
        return None
        
    temps = [f['main']['temp'] for f in day_forecasts]
    day_forecast = next((f for f in day_forecasts if 12 <= datetime.fromtimestamp(f['dt']).hour <= 15), day_forecasts[0])
    
    return {
        'date': target_date,
        'temp_min': min(temps),
        'temp_max': max(temps),
        'temp_day': day_forecast['main']['temp'],
        'feels_like': day_forecast['main']['feels_like'],
        'humidity': day_forecast['main']['humidity'],
        'pressure': day_forecast['main']['pressure'],
        'wind_speed': day_forecast['wind']['speed'],
        'description': day_forecast['weather'][0]['description']
    }

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def create_weather_keyboard(city_name: str, city_in_favorites: bool, lang: str = "rus"):
    keyboard = []
    row = []
    
    if lang == "rus":
        row.append(InlineKeyboardButton("📍 Сделать моим регионом", callback_data=f"set_region_{city_name}"))
        if not city_in_favorites:
            row.append(InlineKeyboardButton("⭐ Добавить в избранное", callback_data=f"add_favorite_{city_name}"))
        else:
            row.append(InlineKeyboardButton("❌ Удалить из избранного", callback_data=f"remove_favorite_{city_name}"))
    else:
        row.append(InlineKeyboardButton("📍 Set as my region", callback_data=f"set_region_{city_name}"))
        if not city_in_favorites:
            row.append(InlineKeyboardButton("⭐ Add to favorites", callback_data=f"add_favorite_{city_name}"))
        else:
            row.append(InlineKeyboardButton("❌ Remove from favorites", callback_data=f"remove_favorite_{city_name}"))
            
    keyboard.append(row)
    
    if lang == "rus":
        keyboard.append([InlineKeyboardButton("📅 Прогноз на неделю", callback_data=f"week_forecast_{city_name}")])
    else:
        keyboard.append([InlineKeyboardButton("📅 Weekly forecast", callback_data=f"week_forecast_{city_name}")])
        
    return InlineKeyboardMarkup(keyboard)

# ==================== ОСНОВНЫЕ ОБРАБОТЧИКИ ====================
async def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    lang = get_user_lang(context, user_id)
    
    if lang == "rus":
        keyboard = [
            ["⚙️ Настройки", "⭐ Избранное"],
            ["🌅 Погода в моем регионе", "🔄 Обновления"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "🌤️ Добро пожаловать в бета версию бота!\n"
            "📌 Текущая версия: Beta 1.0\n\n"
            "Я показываю погоду в любой точке земного шара!\n"
            "🏙️ Введите город, чтобы увидеть погоду в нём!\n"
            "📱 Используйте кнопки ниже или введите /settings для помощи.",
            reply_markup=reply_markup
        )
    else:
        keyboard = [
            ["⚙️ Settings", "⭐ Favorites"],
            ["🌅 Weather in my region", "🔄 Updates"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "🌤️ Welcome to the beta version of the!\n"
            "📌 Current version: Beta 1.0\n\n"
            "I show weather anywhere in the world!\n"
            "🏙️ Enter a city to see the weather there!\n"
            "📱 Use the buttons below or type /settings for help.",
            reply_markup=reply_markup
        )

async def get_weather_for_region(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    lang = get_user_lang(context, user_id)
    region = get_user_region(context, user_id)
    
    if region == 'Moscow':
        if lang == "rus":
            text = ("📍 Вы еще не выбрали свой регион!\n\n"
                    "Введите название города прямо в чат, и после получения погоды "
                    "нажмите кнопку '📍 Сделать моим регионом' под сообщением.")
        else:
            text = ("📍 You haven't selected your region yet!\n\n"
                    "Enter the city name directly in the chat, and after getting the weather, "
                    "press the '📍 Set as my region' button under the message.")
        await update.message.reply_text(text)
        return

    weather_info, weather_text = get_weather(region, lang)
    if weather_info:
        city = weather_info['city']
        city_in_favorites = city in get_user_favorites(context, user_id)
        keyboard = create_weather_keyboard(city, city_in_favorites, lang)
        await update.message.reply_text(weather_text, reply_markup=keyboard)
    else:
        await update.message.reply_text(
            f"⚠️ Не удалось получить погоду для региона {region}" if lang == "rus" 
            else f"⚠️ Failed to get weather for region {region}"
        )

async def show_updates(update: Update, context: CallbackContext):
    user_id = update.effective_user.id if update.message else update.callback_query.from_user.id
    lang = get_user_lang(context, user_id)
    
    if lang == "rus":
        text = (
            "📌 *Доступно в текущей версии (Beta 1.0):*\n"
            "✅ Просмотр текущей погоды\n"
            "✅ Прогноз на неделю\n"
            "✅ Список избранных городов\n\n"
            "🚧 *В разработке (будущие обновления):*\n"
            "🔜 Авторассылка погоды (Обновление 1.1)\n"
            "🔜 История запросов, пересылка погоды, дополнительная информация (Обновление 1.5)"
        )
    else:
        text = (
            "📌 *Available in current version (Beta 1.0):*\n"
            "✅ Current weather view\n"
            "✅ Weekly forecast\n"
            "✅ Favorite cities list\n\n"
            "🚧 *In development (future updates):*\n"
            "🔜 Auto-notification of weather (Update 1.1)\n"
            "🔜 Query history, weather forwarding, additional info (Update 1.5)"
        )
    
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown")

async def handle_reply(update: Update, context: CallbackContext):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    lang = get_user_lang(context, user_id)
    
    # Обработка кнопок нижнего меню
    if lang == "rus":
        if text == "⚙️ Настройки": return await settings(update, context)
        elif text == "⭐ Избранное": return await favorites(update, context)
        elif text == "🌅 Погода в моем регионе": return await get_weather_for_region(update, context)
        elif text == "🔄 Обновления": return await show_updates(update, context)
    else:
        if text == "⚙️ Settings": return await settings(update, context)
        elif text == "⭐ Favorites": return await favorites(update, context)
        elif text == "🌅 Weather in my region": return await get_weather_for_region(update, context)
        elif text == "🔄 Updates": return await show_updates(update, context)

    # Если это не команда меню, считаем это запросом погоды по названию города
    weather_info, weather_text = get_weather(text, lang)
    if weather_info:
        city = weather_info['city']
        city_in_favorites = city in get_user_favorites(context, user_id)
        keyboard = create_weather_keyboard(city, city_in_favorites, lang)
        await update.message.reply_text(weather_text, reply_markup=keyboard)
    else:
        await update.message.reply_text(weather_text)

# ==================== ИЗБРАННОЕ ====================
async def favorites(update: Update, context: CallbackContext):
    query = update.callback_query if hasattr(update, 'callback_query') else None
    user_id = update.effective_user.id if update.message else query.from_user.id
    lang = get_user_lang(context, user_id)
    favorites_list = get_user_favorites(context, user_id)
    
    if not favorites_list:
        text = "⭐ Ваш список избранных городов пуст." if lang == "rus" else "⭐ Your favorites list is empty."
        await (update.message if update.message else query.message).reply_text(text)
        return

    text = "⭐ Ваши избранные города:" if lang == "rus" else "⭐ Your favorite cities:"
    keyboard = []
    
    for city in favorites_list:
        # Получаем только температуру, чтобы не перегружать API лишними данными
        weather_info, _ = get_weather(city, lang)
        temp = weather_info['temp'] if weather_info else "?"
        city_text = f"🏙️ {city} ({temp}°C)"
        keyboard.append([
            InlineKeyboardButton(city_text, callback_data=f"weather_{city}"),
            InlineKeyboardButton("❌", callback_data=f"remove_favorite_{city}")
        ])
        
    if favorites_list:
        keyboard.append([InlineKeyboardButton("🗑️ Очистить весь список" if lang == "rus" else "🗑️ Clear all favorites", callback_data="clear_all_favorites")])
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    elif query:
        await query.edit_message_text(text, reply_markup=reply_markup)

# ==================== ПРОГНОЗ НА НЕДЕЛЮ ====================
async def week_forecast(update: Update, context: CallbackContext, city_name: str = None):
    query = update.callback_query if hasattr(update, 'callback_query') else None
    user_id = query.from_user.id if query else update.effective_user.id
    lang = get_user_lang(context, user_id)
    
    if not city_name:
        city_name = get_user_region(context, user_id)
        
    text = f"📅 Загружаю прогноз погоды для {city_name} на неделю..." if lang == "rus" else f"📅 Loading weather forecast for {city_name} for the week..."
    if query:
        await query.edit_message_text(text)
    else:
        await update.message.reply_text(text)
        
    city_name_api, forecast_list, error = get_forecast(city_name, lang)
    if error or not forecast_list:
        error_msg = "❌ Не удалось получить прогноз." if lang == "rus" else "❌ Failed to get forecast."
        if query: await query.message.reply_text(error_msg)
        else: await update.message.reply_text(error_msg)
        return
        
    context.user_data['forecast_data'] = {'city': city_name_api, 'forecast_list': forecast_list}
    
    text = f"🌤️ Прогноз погоды в {city_name_api}:\nВыберите день:" if lang == "rus" else f"🌤️ Weather forecast in {city_name_api}:\nChoose a day:"
    days_of_week = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"] if lang == "rus" else ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    
    now = datetime.now()
    keyboard = []
    
    for i in range(6):
        forecast_date = now + timedelta(days=i)
        day_num = forecast_date.day
        month_num = forecast_date.month
        
        if lang == "rus":
            day_name = "Сегодня" if i == 0 else "Завтра" if i == 1 else days_of_week[forecast_date.weekday()]
        else:
            day_name = "Today" if i == 0 else "Tomorrow" if i == 1 else days_of_week[forecast_date.weekday()]
            
        button_text = f"{day_name} ({day_num}.{month_num})"
        
        if i % 2 == 0:
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"day_forecast_{city_name_api}_{i}")])
        else:
            keyboard[-1].append(InlineKeyboardButton(button_text, callback_data=f"day_forecast_{city_name_api}_{i}"))
            
    keyboard.append([InlineKeyboardButton("🔙 Назад к погоде" if lang == "rus" else "🔙 Back to weather", callback_data=f"weather_{city_name_api}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    if query: await query.message.reply_text(text, reply_markup=reply_markup)
    else: await update.message.reply_text(text, reply_markup=reply_markup)

# ==================== НАСТРОЙКИ ====================
async def settings(update: Update, context: CallbackContext):
    user_id = update.effective_user.id if update.message else update.callback_query.from_user.id
    lang = get_user_lang(context, user_id)
    
    if lang == "rus":
        keyboard = [[InlineKeyboardButton("🌐 Язык", callback_data="Language")]]
        text = "⚙️ Настройки:"
    else:
        keyboard = [[InlineKeyboardButton("🌐 Language", callback_data="Language")]]
        text = "⚙️ Settings:"
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)

# ==================== ОБРАБОТЧИК CALLBACK ====================
async def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    lang = get_user_lang(context, user_id)
    
    logger.info(f"User {user_id} pressed button with data: {data}")

    if data == "Language":
        if lang == "rus":
            keyboard = [[InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")], [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")]]
            text = "🌐 Выберите язык:"
        else:
            keyboard = [[InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")], [InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")]]
            text = "🌐 Choose language:"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        
    elif data == "lang_ru":
        set_user_lang(context, user_id, "rus")
        keyboard = [["⚙️ Настройки", "⭐ Избранное"], ["🌅 Погода в моем регионе", "🔄 Обновления"]]
        await query.message.reply_text("✅ Язык изменен на Русский", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        
    elif data == "lang_en":
        set_user_lang(context, user_id, "eng")
        keyboard = [["⚙️ Settings", "⭐ Favorites"], ["🌅 Weather in my region", "🔄 Updates"]]
        await query.message.reply_text("✅ Language changed to English", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        
    elif data.startswith("set_region_"):
        city = data.split("_", 2)[2]
        set_user_region(context, user_id, city)
        if lang == "rus":
            await query.answer(f"✅ {city} установлен как ваш регион")
            await query.message.reply_text(f"📍 Город {city} установлен как ваш регион")
        else:
            await query.answer(f"✅ {city} set as your region")
            await query.message.reply_text(f"📍 City {city} set as your region")
            
    elif data.startswith("add_favorite_"):
        city = data.split("_", 2)[2]
        if add_user_favorite(context, user_id, city):
            await query.answer(f"✅ {city} добавлен в избранное" if lang == "rus" else f"✅ {city} added to favorites")
            await query.message.reply_text(f"⭐ Город '{city}' добавлен в избранное!" if lang == "rus" else f"⭐ City '{city}' added to favorites!")
        else:
            await query.answer(f"⚠️ {city} уже в избранном" if lang == "rus" else f"⚠️ {city} already in favorites")
            
    elif data.startswith("remove_favorite_"):
        city = data.split("_", 2)[2]
        if remove_user_favorite(context, user_id, city):
            await query.answer(f"✅ {city} удален из избранного" if lang == "rus" else f"✅ {city} removed from favorites")
            await favorites(update, context) # Обновляем список
            
    elif data == "clear_all_favorites":
        if lang == "rus":
            keyboard = [[InlineKeyboardButton("✅ Да", callback_data="confirm_clear_favorites")], [InlineKeyboardButton("❌ Нет", callback_data="favorites")]]
            text = "⚠️ Очистить весь список?"
        else:
            keyboard = [[InlineKeyboardButton("✅ Yes", callback_data="confirm_clear_favorites")], [InlineKeyboardButton("❌ No", callback_data="favorites")]]
            text = "⚠️ Clear all favorites?"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        
    elif data == "confirm_clear_favorites":
        clear_user_favorites(context, user_id)
        await query.answer("✅ Список очищен" if lang == "rus" else "✅ List cleared", show_alert=True)
        await query.edit_message_text("🗑️ Список очищен." if lang == "rus" else "🗑️ List cleared.")
        
    elif data.startswith("weather_"):
        city = data.split("_", 1)[1]
        weather_info, weather_text = get_weather(city, lang)
        if weather_info:
            city_in_favorites = city in get_user_favorites(context, user_id)
            await query.edit_message_text(weather_text, reply_markup=create_weather_keyboard(city, city_in_favorites, lang))
        else:
            await query.edit_message_text(weather_text)
            
    elif data.startswith("week_forecast_"):
        await week_forecast(update, context, data.split("_", 2)[2])
        
    elif data.startswith("day_forecast_"):
        parts = data.split("_")
        city_name, day_offset = parts[2], int(parts[3])
        forecast_data = context.user_data.get('forecast_data')
        
        if not forecast_data or forecast_data['city'] != city_name:
            city_name_api, forecast_list, error = get_forecast(city_name, lang)
            if error:
                await query.message.reply_text(error)
                return
            forecast_data = {'city': city_name_api, 'forecast_list': forecast_list}
            
        daily = get_daily_forecast(forecast_data['forecast_list'], day_offset)
        if daily:
            now = datetime.now()
            target_date = now + timedelta(days=day_offset)
            days_ru = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
            days_en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            months_ru = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
            months_en = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
            
            if lang == "rus":
                day_name = "сегодня" if day_offset == 0 else "завтра" if day_offset == 1 else days_ru[target_date.weekday()].lower()
                date_str = f"{target_date.day} {months_ru[target_date.month - 1]}"
                pressure_display = f"{round(daily['pressure'] * 0.750062)} мм рт. ст."
                forecast_text = (f"📅 Погода в {forecast_data['city']} на {day_name} ({date_str}):\n"
                                 f"📝 {daily['description'].capitalize()}\n"
                                 f"🌡️ Температура: {daily['temp_day']}°C (ощущается {daily['feels_like']}°C)\n"
                                 f"📈 Диапазон: {daily['temp_min']}°C - {daily['temp_max']}°C\n"
                                 f"💧 Влажность: {daily['humidity']}%\n"
                                 f"📊 Давление: {pressure_display}\n"
                                 f"💨 Ветер: {daily['wind_speed']} м/с")
            else:
                day_name = "today" if day_offset == 0 else "tomorrow" if day_offset == 1 else days_en[target_date.weekday()].lower()
                date_str = f"{months_en[target_date.month - 1]} {target_date.day}"
                forecast_text = (f"📅 Weather in {forecast_data['city']} on {day_name} ({date_str}):\n"
                                 f"📝 {daily['description'].capitalize()}\n"
                                 f"🌡️ Temperature: {daily['temp_day']}°C (feels like {daily['feels_like']}°C)\n"
                                 f"📈 Range: {daily['temp_min']}°C - {daily['temp_max']}°C\n"
                                 f"💧 Humidity: {daily['humidity']}%\n"
                                 f"📊 Pressure: {daily['pressure']} hPa\n"
                                 f"💨 Wind: {daily['wind_speed']} m/s")
            await query.message.reply_text(forecast_text)
        else:
            await query.message.reply_text("❌ Не удалось получить прогноз." if lang == "rus" else "❌ Failed to get forecast.")
            
    else:
        logger.warning(f"Unknown callback data: {data}")
        await query.answer("⚠️ Неизвестная команда" if lang == "rus" else "⚠️ Unknown command")

# ==================== ОСНОВНАЯ ФУНКЦИЯ ====================
def main():
    try:
        logger.info("Запуск бота погоды (Beta 1.0)...")
        application = Application.builder().token(BOT_TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("settings", settings))
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reply))
        
        logger.info("Обработчики добавлены, запускаю polling...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()