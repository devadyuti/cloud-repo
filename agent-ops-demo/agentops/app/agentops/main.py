from strands import Agent, tool
from strands_tools import calculator  # starter agent's calculator tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from model.load import load_model

app = BedrockAgentCoreApp()
log = app.logger


# --- Starter agent tools (ported verbatim from the workshop starter) ---------
@tool
def weather(city: str):
    """Get weather information.

    Args:
        city: City for which weather will be returned

    Returns:
        Weather of provided city as a string.
    """
    log.info(f"weather tool called: {city}")
    if city.lower() == "athens":
        return "very sunny"
    return "sunny"


# Collection of tools available to the agent (same set as the starter).
tools = [calculator, weather]


_agent = None

def get_or_create_agent():
    global _agent
    if _agent is None:
        _agent = Agent(
            model=load_model(),
            system_prompt="You're a helpful assistant. You can do simple math calculation, and tell the weather.",
            tools=tools,
        )
    return _agent


@app.entrypoint
async def invoke(payload, context):
    log.info("Invoking Agent.....")

    agent = get_or_create_agent()

    # Execute and format response
    stream = agent.stream_async(payload.get("prompt"))

    async for event in stream:
        # Handle Text parts of the response
        if "data" in event and isinstance(event["data"], str):
            yield event["data"]


if __name__ == "__main__":
    app.run()
