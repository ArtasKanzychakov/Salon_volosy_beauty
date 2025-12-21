# admin_handlers.py - Обработчики админ-панели

from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from admin_keyboards import *
from photo_storage import photo_storage, PHOTO_KEYS

# Состояния для админ-панели
class AdminState(StatesGroup):
    MAIN = State()
    UPLOAD = State()
    WAITING_PHOTO = State()
    DELETE_SELECT = State()
    DELETE_CONFIRM = State()

# Словарь для преобразования русских названий в ключи
NAME_TO_KEY = {v: k for k, v in PHOTO_KEYS.items()}

# Обратный словарь для упрощенных названий (для меню)
SIMPLIFIED_NAMES = {
    "Молочко для тела": "body_milk",
    "Гидрофильное масло": "hydrophilic_oil",
    "Крем суфле": "cream_body",
    "Скраб для тела": "body_scrub",
    "Гель для душа": "shower_gel",
    "Баттер для тела": "body_butter",
    "Гиалуроновая кислота": "hyaluronic_acid",
    "Биолипидный спрей": "biolipid_spray",
    "Сухое масло спрей": "dry_oil_spray",
    "Масло ELIXIR": "oil_elixir",
    "Молочко для волос": "hair_milk",
    "Масло концентрат": "oil_concentrate",
    "Флюид для волос": "hair_fluid",
    "Шампунь реконстракт": "reconstruct_shampoo",
    "Маска реконстракт": "reconstruct_mask",
    "Протеиновый крем": "protein_cream",
    "Шампунь для осветленных волос": "blonde_shampoo",
    "Кондиционер для осветленных волос": "blonde_conditioner",
    "Маска для осветленных волос": "blonde_mask",
    "Шампунь для окрашенных волос": "colored_shampoo",
    "Кондиционер для окрашенных волос": "colored_conditioner",
    "Маска для окрашенных волос": "colored_mask",
    "Оттеночная маска Холодный шоколад": "mask_cold_chocolate",
    "Оттеночная маска Медный": "mask_copper",
    "Оттеночная маска Розовая пудра": "mask_pink_powder",
    "Оттеночная маска Перламутр": "mask_mother_of_pearl",
    "Коллаж для блондинок": "blonde_general",
    "Коллаж: Ломкость волос": "blonde_lomkost",
    "Коллаж: Тусклость": "hair_milk_concentrate",
    "Коллаж: Пушистость": "fluid_protein_elixir",
    "Коллаж: Тонкие волосы": "thin_hair_care",
    "Коллаж: Поврежденные волосы": "damaged_hair",
    "Коллаж: Окрашенные (шатен/русая)": "colored_general_chocolate",
    "Коллаж: Окрашенные (рыжая)": "colored_general_copper",
    "Коллаж: Натуральные волосы": "natural_general",
    "Коллаж: Объем": "volume_care",
}

router = Router()

# Глобальная переменная для хранения выбранного продукта
current_selection = {}

@router.message(F.text == "admin2026")
async def admin_access(message: Message, state: FSMContext):
    """Вход в админ-панель"""
    await state.set_state(AdminState.MAIN)
    await message.answer(
        "🔐 <b>Админ-панель активирована!</b>\n"
        "Выберите действие:",
        reply_markup=get_admin_main_menu()
    )

@router.message(F.text == "🔙 Выйти из админки")
async def admin_exit(message: Message, state: FSMContext):
    """Выход из админ-панели"""
    await state.clear()
    from keyboards import get_main_menu
    await message.answer(
        "👋 Вы вышли из админ-панели.\n"
        "Возвращаюсь в главное меню.",
        reply_markup=get_main_menu()
    )

# ========== ГЛАВНОЕ МЕНЮ АДМИНКИ ==========

@router.message(AdminState.MAIN, F.text == "📤 Загрузить фото")
async def admin_upload_start(message: Message, state: FSMContext):
    """Начать загрузку фото"""
    await state.set_state(AdminState.UPLOAD)
    await message.answer(
        "📤 <b>Загрузка фото</b>\n"
        "Выберите категорию продукта:",
        reply_markup=get_photo_categories_menu()
    )

@router.message(AdminState.MAIN, F.text == "🗑 Удалить фото")
async def admin_delete_start(message: Message, state: FSMContext):
    """Начать удаление фото"""
    await state.set_state(AdminState.DELETE_SELECT)
    await message.answer(
        "🗑 <b>Удаление фото</b>\n"
        "Выберите действие:",
        reply_markup=get_admin_delete_menu()
    )

@router.message(AdminState.MAIN, F.text == "📊 Статус фото")
async def admin_status(message: Message):
    """Показать статус загрузки фото"""
    status = photo_storage.get_photo_status()
    total = len(status)
    uploaded = sum(1 for v in status.values() if v)
    missing = total - uploaded
    
    response = f"📊 <b>Статус загрузки фото:</b>\n\n"
    response += f"✅ Загружено: {uploaded}/{total}\n"
    response += f"❌ Отсутствует: {missing}\n\n"
    
    if missing > 0:
        response += "<b>Отсутствующие фото:</b>\n"
        for name, has_photo in status.items():
            if not has_photo:
                response += f"• {name}\n"
    
    await message.answer(response)

# ========== ЗАГРУЗКА ФОТО ==========

@router.message(AdminState.UPLOAD, F.text == "🔙 Назад")
async def admin_upload_back(message: Message, state: FSMContext):
    """Назад в админ-панель"""
    await state.set_state(AdminState.MAIN)
    await message.answer(
        "Выберите действие:",
        reply_markup=get_admin_main_menu()
    )

@router.message(AdminState.UPLOAD, F.text == "🔙 К категориям")
async def admin_back_to_categories(message: Message, state: FSMContext):
    """Вернуться к выбору категории"""
    await state.set_state(AdminState.UPLOAD)
    await message.answer(
        "Выберите категорию продукта:",
        reply_markup=get_photo_categories_menu()
    )

# Обработка выбора категорий
@router.message(AdminState.UPLOAD, F.text == "🧴 Тело")
async def admin_body_photos(message: Message):
    await message.answer("Выберите продукт для тела:", reply_markup=get_body_photos_menu())

@router.message(AdminState.UPLOAD, F.text == "💇 Волосы - общие")
async def admin_hair_common(message: Message):
    await message.answer("Выберите общий продукт для волос:", reply_markup=get_hair_common_menu())

@router.message(AdminState.UPLOAD, F.text == "👱‍♀️ Блондинки")
async def admin_blonde_photos(message: Message):
    await message.answer("Выберите продукт для блондинок:", reply_markup=get_blonde_photos_menu())

@router.message(AdminState.UPLOAD, F.text == "🎨 Окрашенные")
async def admin_colored_photos(message: Message):
    await message.answer("Выберите продукт для окрашенных волос:", reply_markup=get_colored_photos_menu())

@router.message(AdminState.UPLOAD, F.text == "🎨 Оттеночные маски")
async def admin_tone_masks(message: Message):
    await message.answer("Выберите оттеночную маску:", reply_markup=get_tone_masks_menu())

@router.message(AdminState.UPLOAD, F.text == "🖼 Коллажи")
async def admin_collages(message: Message):
    await message.answer("Выберите коллаж:", reply_markup=get_collage_menu())

# Обработка выбора конкретного продукта
@router.message(AdminState.UPLOAD, F.text.in_(SIMPLIFIED_NAMES.keys()))
async def admin_select_product(message: Message, state: FSMContext):
    """Выбор конкретного продукта для загрузки"""
    product_name = message.text
    key = SIMPLIFIED_NAMES[product_name]
    
    # Сохраняем выбор в состояние
    await state.update_data(selected_key=key, selected_name=product_name)
    await state.set_state(AdminState.WAITING_PHOTO)
    
    # Проверяем, есть ли уже фото
    existing_photo = photo_storage.get_photo_id(key)
    
    if existing_photo:
        await message.answer(
            f"📸 <b>{product_name}</b>\n"
            f"Фото уже загружено.\n"
            f"Отправьте новое фото чтобы заменить существующее:"
        )
    else:
        await message.answer(
            f"📸 <b>{product_name}</b>\n"
            f"Отправьте фото продукта:"
        )

# Обработка получения фото
@router.message(AdminState.WAITING_PHOTO, F.photo)
async def admin_receive_photo(message: Message, state: FSMContext):
    """Получение и сохранение фото"""
    data = await state.get_data()
    key = data.get("selected_key")
    product_name = data.get("selected_name")
    
    if not key:
        await message.answer("Ошибка: не выбран продукт")
        await state.set_state(AdminState.UPLOAD)
        await message.answer("Выберите категорию:", reply_markup=get_photo_categories_menu())
        return
    
    # Получаем file_id самого лучшего качества
    photo = message.photo[-1]
    file_id = photo.file_id
    
    # Сохраняем в хранилище
    photo_storage.save_photo_id(key, file_id)
    
    await message.answer(
        f"✅ <b>Фото успешно загружено!</b>\n"
        f"Продукт: {product_name}\n"
        f"ID фото сохранен в базе.\n\n"
        f"Вы можете:\n"
        f"1. Продолжить загрузку других фото\n"
        f"2. Проверить статус загрузки",
        reply_markup=get_admin_upload_menu()
    )
    
    # Возвращаемся в состояние загрузки
    await state.set_state(AdminState.UPLOAD)

@router.message(AdminState.WAITING_PHOTO)
async def admin_wrong_input(message: Message):
    """Неправильный ввод при ожидании фото"""
    await message.answer("❌ Пожалуйста, отправьте фото!")

# ========== УДАЛЕНИЕ ФОТО ==========

@router.message(AdminState.DELETE_SELECT, F.text == "🗑 Выбрать для удаления")
async def admin_delete_select(message: Message):
    """Выбор фото для удаления"""
    # Получаем все загруженные фото
    all_photos = photo_storage.get_all_photos()
    
    if not all_photos:
        await message.answer("❌ Нет загруженных фото для удаления.")
        return
    
    # Показываем список загруженных фото
    response = "📋 <b>Загруженные фото:</b>\n\n"
    for key, file_id in all_photos.items():
        if key in PHOTO_KEYS:
            product_name = PHOTO_KEYS[key]
            response += f"• {product_name}\n"
    
    response += "\nВведите точное название продукта для удаления:"
    await message.answer(response)

@router.message(AdminState.DELETE_SELECT, F.text.in_(PHOTO_KEYS.values()))
async def admin_confirm_delete(message: Message, state: FSMContext):
    """Подтверждение удаления"""
    product_name = message.text
    # Находим ключ по названию
    key = NAME_TO_KEY.get(product_name)
    
    if not key:
        await message.answer("❌ Продукт не найден в базе.")
        return
    
    # Сохраняем для подтверждения
    await state.update_data(delete_key=key, delete_name=product_name)
    await state.set_state(AdminState.DELETE_CONFIRM)
    
    await message.answer(
        f"⚠️ <b>Подтверждение удаления</b>\n\n"
        f"Вы действительно хотите удалить фото для:\n"
        f"<b>{product_name}</b>\n\n"
        f"Это действие нельзя отменить!",
        reply_markup=get_delete_confirmation()
    )

@router.message(AdminState.DELETE_CONFIRM, F.text == "✅ Да, удалить")
async def admin_execute_delete(message: Message, state: FSMContext):
    """Выполнение удаления"""
    data = await state.get_data()
    key = data.get("delete_key")
    product_name = data.get("delete_name")
    
    if key and photo_storage.delete_photo(key):
        await message.answer(
            f"🗑 <b>Фото удалено!</b>\n"
            f"Продукт: {product_name}\n\n"
            f"Выберите следующее действие:",
            reply_markup=get_admin_delete_menu()
        )
    else:
        await message.answer(
            "❌ Не удалось удалить фото. Возможно, оно уже было удалено."
        )
    
    await state.set_state(AdminState.DELETE_SELECT)

@router.message(AdminState.DELETE_CONFIRM, F.text == "❌ Нет, отмена")
async def admin_cancel_delete(message: Message, state: FSMContext):
    """Отмена удаления"""
    await state.set_state(AdminState.DELETE_SELECT)
    await message.answer(
        "Удаление отменено.\n"
        "Выберите действие:",
        reply_markup=get_admin_delete_menu()
    )

@router.message(AdminState.DELETE_SELECT, F.text == "🔙 Назад в админку")
async def admin_delete_back(message: Message, state: FSMContext):
    """Назад из удаления"""
    await state.set_state(AdminState.MAIN)
    await message.answer(
        "Выберите действие:",
        reply_markup=get_admin_main_menu()
    )