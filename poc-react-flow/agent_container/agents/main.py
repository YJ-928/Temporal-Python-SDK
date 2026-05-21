import sys
from pydantic_ai import Agent
from pydantic import BaseModel

class AgentOutput(BaseModel):
    answer: str

agent = Agent(
    "openai:gpt-4o-mini",
    output_type=AgentOutput,
    system_prompt="You are a helpful assistant. Be concise."
)

if __name__ == "__main__":
    prompt = sys.argv[1] if len(sys.argv) > 1 else "hello"
    result = agent.run_sync(prompt)
    print(result.output.model_dump_json())