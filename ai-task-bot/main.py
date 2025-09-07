import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from config import BOT_TOKEN
from celery import Celery

backend_celery = Celery(
    "bot-client",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1"
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

@dp.message(Command("start"))
async def start_command(message: types.Message):
    if not message.from_user:
        return
        
    try:
        result = backend_celery.send_task(
            "authenticate_telegram_user",
            args=[
                message.from_user.id,
                message.from_user.username or "",
                "",
                message.from_user.first_name or "",
                "",
                "",
                "",
                ""
            ]
        )
        
        user_data = result.get(timeout=10)
        
        if user_data:
            await message.answer(f"Добро пожаловать! Для помощи введите /help")
        else:
            await message.answer("❌ Ошибка аутентификации")
            
    except Exception as e:
        print(f"❌ Ошибка аутентификации: {e}")
        await message.answer("❌ Ошибка: не удалось аутентифицироваться")

@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer("""
    /start - аутентификация пользователя
    /help - помощь
    """)

@dp.message(Command("status"))
async def status_command(message: types.Message):
    try:
        inspect = backend_celery.control.inspect()
        stats = inspect.stats()
        
        if stats:
            await message.answer("✅ Backend workers активны!")
            for worker, info in stats.items():
                await message.answer(f"👷 Worker: {worker}")
        else:
            await message.answer("❌ Backend workers не найдены!")
            
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

        
@dp.message(Command("view_tasks"))
async def view_tasks_command(message: types.Message):
    if not message.from_user:
        return
        
    try:
        result = backend_celery.send_task(
            "get_user_tasks",
            args=[message.from_user.id]
        )

        tasks = result.get(timeout=10)
        
        if not tasks:
            await message.answer("У пользователя пока нет задач")
            return
        
        tasks_list = "\n".join([f"{task['id']}. {task['title']}" for task in tasks])
        await message.answer(f"Ваши задачи:\n{tasks_list}")
        
    except Exception as e:
        print(f"❌ Ошибка получения задач: {e}")
        await message.answer("❌ Ошибка: не удалось получить задачи")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())