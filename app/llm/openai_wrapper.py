import os
from openai import AsyncOpenAI, OpenAI

class OpenAIWrapper(object):

    def __init__(self, api_key, model="gpt-4o-mini", max_retries=3):
        """
        Initialize the OpenAIWrapper instance.
        """
        self.api_key = api_key
        self.model = model

    def generate_sync_response(self, prompt, return_in_json=True):
        """
        """
        client = OpenAI(
            api_key=self.api_key
        )

        if return_in_json:
            response = client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
                model=self.model,
                response_format={ "type": "json_object" }
            )

        else:
            response = client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
                model=self.model
            )

        return response

    async def generate_async_response(self, prompt):
        """
        """
        client = AsyncOpenAI(
            api_key=self.api_key
        )

        response_stream = await client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            model=self.model,
            stream=True
        )

        async for chunk in response_stream:
            if chunk.choices[0].finish_reason == 'stop':
                yield None
            else:
                content = chunk.choices[0].delta.content
                if content:
                    yield content

    
    async def generate_async_json_response(self, prompt):
        """
        """
        client = AsyncOpenAI(
            api_key=self.api_key
        )

        response_stream = await client.chat.completions.create(
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            model = self.model,
            stream = True,
            response_format={ "type": "json_object" }
        )

        async for chunk in response_stream:
            if chunk.choices[0].finish_reason == 'stop':
                yield None
            else:
                content = chunk.choices[0].delta.content
                if content:
                    yield content


