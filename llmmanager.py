from huggingface_hub import InferenceClient

from config import LLM_TOKEN, DATABASE_URL
from databasemanager import DatabaseManager

class LLMManager:
    def __init__(self):
        self.client = InferenceClient(
            provider="fireworks-ai",
            api_key=LLM_TOKEN,
            model="deepseek-ai/DeepSeek-R1"
        )
        self.db = DatabaseManager(database_url=DATABASE_URL)

    def get_answer(self, prompt: str, task_context: str) -> str:
        completion = self.client.chat.completions.create(
        messages=[
            {
            "role": "user",
            "content": task_context + "\n\n" + prompt
            }
        ],
        )

        answer = completion.choices[0].message.content
        if answer and "<think>" in answer and "</think>" in answer:
            clean_answer = answer.split("</think>")[-1].strip()
        else:
            clean_answer = answer or "Нет ответа"
            
        return clean_answer

    async def generate_task_context(self, task_name: str, task_description: str, task_id: int, user_id: int) -> str:
        history = await self.db.get_task_exchanges(task_id=task_id, user_id=user_id)
        prompt = "Generate a context for the task: " + task_name + " with the description: " + task_description + " And with the message history: " + str(history)
        completion = self.client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        if completion.choices[0].message.content:
            return completion.choices[0].message.content
        else:
            return "No context"



    


