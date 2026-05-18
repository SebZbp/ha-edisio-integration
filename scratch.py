import asyncio
import voluptuous as vol
from voluptuous_serialize import convert
from custom_components.edisio.config_flow import EdisioConfigFlow, EdisioOptionsFlowHandler
from unittest.mock import MagicMock

async def test():
    entry = MagicMock()
    entry.options = {}
    
    # Try getting the handler
    handler = EdisioConfigFlow.async_get_options_flow(entry)
    print("Handler created:", type(handler))
    
    # Try calling async_step_init
    result = await handler.async_step_init()
    print("Result form:", result)
    
    # Check if schema is serializable
    schema = result.get('data_schema')
    print("Schema serialization:", convert(schema))

asyncio.run(test())
