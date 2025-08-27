from openai import OpenAI

from config import LLM_TOKEN, DATABASE_URL, REDIS_URL
from databasemanager import DatabaseManager
from redismanager import RedisManager

class LLMManager:
    def __init__(self):
        self.client = OpenAI(api_key=LLM_TOKEN)
        self.model = "gpt-4o-mini"  
        self.db = DatabaseManager(database_url=DATABASE_URL)
        self.redis = RedisManager(redis_url=REDIS_URL)
    
    async def init_redis(self):
        await self.redis.init_redis()

    def get_answer(self, prompt: str, task_context: str) -> str:
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"You are an AI assistant helping with task management. Here's the task context:\n{task_context}"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=1000
            )

            answer = completion.choices[0].message.content
            if answer and "<think>" in answer and "</think>" in answer:
                clean_answer = answer.split("</think>")[-1].strip()
            else:
                clean_answer = answer or "No answer"
                
            return clean_answer
        except Exception as e:
            print(f"OpenAI API Error: {e}")
            return f"🚫 Ошибка AI: {str(e)}"

    async def invalidate_task_cache(self, task_id: int, user_id: int):
        await self.redis.invalidate_task_context(task_id, user_id)
    
    async def generate_task_context(self, task_name: str, task_description: str, task_id: int, user_id: int, existing_context: str | None = None) -> str:
        cached_context = await self.redis.get_task_context(task_id, user_id)
        if cached_context:
            print(f"🚀 Using cached context for task {task_id}")
            return cached_context
        
        print(f"🔄 Generating new context for task {task_id}")
        try:
            history = await self.db.get_task_exchanges(task_id=task_id, user_id=user_id)
            
            has_existing_context = existing_context and existing_context.strip() and existing_context != "no context"
            has_history = history and len(history) > 0
            
            if has_history:
                formatted_history = "\n".join([
                    f"User: {exchange['prompt']}\nAI: {exchange['response'][:100]}{'...' if len(exchange['response']) > 100 else ''}\n---"
                    for exchange in history[-3:]
                ])
            else:
                formatted_history = "No conversation history yet - this is the first interaction with AI for this task."
            
            if has_existing_context and has_history:
                prompt = f"""You are an AI assistant that updates task contexts in AI Task Manager system.

CURRENT SITUATION: This task already has a context and new conversation history. Your job is to UPDATE the existing context intelligently.

EXISTING CONTEXT:
{existing_context}

NEW CONVERSATION DATA:
{formatted_history}

TASK INFO:
- Task Name: {task_name}
- Task Description: {task_description}

YOUR TASK: UPDATE the existing context by:
1. Preserving important user-edited information
2. Adding insights from new conversations
3. Updating progress/status based on recent exchanges
4. Keeping the context concise (max 400 words)
5. Maintaining the same structure and style

IMPORTANT: Do not completely rewrite the context. Instead, intelligently merge new information with existing content.

UPDATED CONTEXT:"""
                
            elif has_existing_context and not has_history:
                if existing_context:
                    await self.redis.set_task_context(task_id, user_id, existing_context, ttl_hours=24)
                    return existing_context or ""
                else:
                    return f"📋 Task: {task_name}\n📝 Description: {task_description}\n🔧 Basic context generated."
                
            else:
                prompt = f"""You are an AI assistant that creates task contexts for AI Task Manager system.

YOUR OBJECTIVE:
Create a comprehensive context for a task that will be used by other AI assistants when communicating with users about this specific task.

TASK INFORMATION:
- Task Name: {task_name}
- Task Description: {task_description}
- Task ID: {task_id}
- User ID: {user_id}
- Conversation History: {formatted_history}

WHAT THE CONTEXT SHOULD INCLUDE:
1. Brief summary of the task and its main objectives
2. Key requirements and constraints identified
3. Current status/progress based on any existing conversation
4. Important details to remember for future conversations
5. Domain-specific knowledge if applicable
6. Communication style preference (formal/informal)
7. Next logical steps or areas to focus on

HOW THE CONTEXT WILL BE USED:
- Every new user question will be sent to AI along with this context
- AI should respond within the scope of this task, remembering all background
- Context helps AI provide more accurate and relevant answers
- Context should guide the AI to maintain task focus and continuity

FORMAT REQUIREMENTS:
- Write concisely but informatively (max 400 words)
- Use structured text with clear sections
- Highlight key points and actionable items
- Write in English
- Focus on essential information, don't duplicate entire history
- Make it actionable for the AI assistant

GENERATE TASK CONTEXT:"""
            
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3, 
                max_tokens=800
            )
            
            if completion.choices[0].message.content:
                generated_context = completion.choices[0].message.content.strip()
                await self.redis.set_task_context(task_id, user_id, generated_context)
                return generated_context
            else:
                fallback_context = f"📋 Task: {task_name}\n📝 Description: {task_description}\n🔧 Basic context generated."
                await self.redis.set_task_context(task_id, user_id, fallback_context, ttl_hours=1)
                return fallback_context
                
        except Exception as e:
            print(f"OpenAI API Error in generate_task_context: {e}")
            if existing_context and existing_context.strip() and existing_context != "no context":
                await self.redis.set_task_context(task_id, user_id, existing_context, ttl_hours=1)
                return existing_context or ""
            else:
                error_context = f"📋 Task: {task_name}\n📝 Description: {task_description}\n⚠️ Context generation failed: {str(e)}"
                await self.redis.set_task_context(task_id, user_id, error_context, ttl_hours=1)
                return error_context



    


