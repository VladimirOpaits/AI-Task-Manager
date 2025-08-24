import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from config import DATABASE_URL


async def run_migration() -> None:
    engine = create_async_engine(DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        # Ensure users table exists
        await conn.execute(text(
            """CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                google_id VARCHAR(255) UNIQUE NOT NULL,
                email TEXT NOT NULL,
                name VARCHAR(255),
                picture TEXT,
                access_token TEXT NOT NULL,
                refresh_token TEXT,
                token_expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
            )"""
        ))

        # Ensure tasks table exists
        await conn.execute(text(
            """CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                task_name TEXT NOT NULL,
                task_description TEXT NOT NULL,
                task_status TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )"""
        ))

        # Add missing columns (if DB was created earlier with a different layout)
        await conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS task_name TEXT"))
        await conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS task_description TEXT"))
        await conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS task_status TEXT"))
        await conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS user_id INTEGER"))
        await conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
        await conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))

        # Set defaults for NOT NULL semantics
        await conn.execute(text("UPDATE tasks SET task_name = COALESCE(task_name, '')"))
        await conn.execute(text("UPDATE tasks SET task_description = COALESCE(task_description, '')"))
        await conn.execute(text("UPDATE tasks SET task_status = COALESCE(task_status, 'new')"))

        # Backfill from legacy 'prompt' if present and name/description are empty
        await conn.execute(text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name='tasks' AND column_name='prompt'
                ) THEN
                    UPDATE tasks
                    SET task_name = CASE
                        WHEN COALESCE(task_name, '') = '' AND COALESCE(prompt, '') <> ''
                        THEN trim(both from regexp_replace(split_part(prompt, E'\n', 1), '^Task:\\s*', ''))
                        ELSE task_name
                    END,
                    task_description = CASE
                        WHEN COALESCE(task_description, '') = '' AND COALESCE(prompt, '') <> ''
                        THEN trim(both from regexp_replace(
                            NULLIF(split_part(prompt, E'\n', 2), ''), '^Description:\\s*', ''
                        ))
                        ELSE task_description
                    END;
                END IF;
            END$$;
            """
        ))

        # Apply NOT NULL constraints (only after backfills)
        await conn.execute(text("""
            DO $$
            BEGIN
                BEGIN
                    ALTER TABLE tasks ALTER COLUMN task_name SET NOT NULL;
                EXCEPTION WHEN others THEN NULL; END;
                BEGIN
                    ALTER TABLE tasks ALTER COLUMN task_description SET NOT NULL;
                EXCEPTION WHEN others THEN NULL; END;
                BEGIN
                    ALTER TABLE tasks ALTER COLUMN task_status SET NOT NULL;
                EXCEPTION WHEN others THEN NULL; END;
                BEGIN
                    ALTER TABLE tasks ALTER COLUMN user_id SET NOT NULL;
                EXCEPTION WHEN others THEN NULL; END;
            END$$;
        """))

        # Ensure exchanges table exists
        await conn.execute(text(
            """CREATE TABLE IF NOT EXISTS exchanges (
                id SERIAL PRIMARY KEY,
                task_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                prompt TEXT NOT NULL,
                response TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )"""
        ))

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_migration())
