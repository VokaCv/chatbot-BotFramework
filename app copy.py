# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""
This sample shows how to create a bot that demonstrates the following:
- Use [LUIS](https://www.luis.ai) to implement core AI capabilities.
- Implement a multi-turn conversation using Dialogs.
- Handle user interruptions for such things as `Help` or `Cancel`.
- Prompt for and validate requests for information from the user.
"""
from http import HTTPStatus
from typing import Dict

from aiohttp import web
from aiohttp.web import Request, Response, json_response

from botbuilder.core import (
    BotFrameworkAdapterSettings,
    ConversationState,
    MemoryStorage,
    UserState,
)

from botbuilder.core.integration import aiohttp_error_middleware
from botbuilder.schema import Activity
from botbuilder.applicationinsights import ApplicationInsightsTelemetryClient
from botbuilder.integration.applicationinsights.aiohttp import (
    AiohttpTelemetryProcessor,
    bot_telemetry_middleware,
)
from botbuilder.core.telemetry_logger_middleware import TelemetryLoggerMiddleware

from config import DefaultConfig
from dialogs import MainDialog, BookingDialog
from bots import DialogAndWelcomeBot

from adapter_with_error_handler import AdapterWithErrorHandler
from flight_booking_recognizer import FlightBookingRecognizer


CONFIG = DefaultConfig()

# Create adapter.
# See https://aka.ms/about-bot-adapter to learn more about how bots work.
SETTINGS = BotFrameworkAdapterSettings(CONFIG.CHATBOT_BOT_ID, CONFIG.CHATBOT_BOT_PASSWORD)

# Create MemoryStorage, UserState and ConversationState
MEMORY = MemoryStorage()
USER_STATE = UserState(MEMORY)
CONVERSATION_STATE = ConversationState(MEMORY)

# Create adapter.
# See https://aka.ms/about-bot-adapter to learn more about how bots work.
ADAPTER = AdapterWithErrorHandler(SETTINGS, CONVERSATION_STATE)

class CustomApplicationInsightsTelemetryClient(ApplicationInsightsTelemetryClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.main_dialog = None

    def track_event(
        self,
        name: str,
        properties: Dict[str, object] = None,
        measurements: Dict[str, object] = None,
    ) -> None:
        # Add the uuid of the main dialog
        if self.main_dialog:
            properties["mainDialogUuid"] = self.main_dialog.uuid
        
        super().track_event(name, properties=properties, measurements=measurements)

# Create telemetry client.
# Note the small 'client_queue_size'.  This is for demonstration purposes.  Larger queue sizes
# result in fewer calls to applicationInsights, improving bot performance at the expense of
# less frequent updates.
INSTRUMENTATION_KEY = CONFIG.APPINSIGHTS_INSTRUMENTATIONKEY
INSTRUMENTATION_KEY = '2d499cdc-86ad-4237-b30a-6c92b4590c6b'
# TELEMETRY_CLIENT = ApplicationInsightsTelemetryClient(
TELEMETRY_CLIENT = CustomApplicationInsightsTelemetryClient(
    instrumentation_key = INSTRUMENTATION_KEY, 
    telemetry_processor=AiohttpTelemetryProcessor(), 
    client_queue_size=10,
)

TELEMETRY_MIDDLEWARE =  TelemetryLoggerMiddleware(
    telemetry_client=TELEMETRY_CLIENT,
    log_personal_information=True
)
ADAPTER.use(TELEMETRY_MIDDLEWARE)

# Create dialogs and Bot
RECOGNIZER = FlightBookingRecognizer(CONFIG, telemetry_client=TELEMETRY_CLIENT)
BOOKING_DIALOG = BookingDialog()
DIALOG = MainDialog(RECOGNIZER, BOOKING_DIALOG, telemetry_client=TELEMETRY_CLIENT)
BOT = DialogAndWelcomeBot(CONVERSATION_STATE, USER_STATE, DIALOG, TELEMETRY_CLIENT)

TELEMETRY_CLIENT.main_dialog = DIALOG

# # Listen for incoming requests on /api/messages.
# async def index(req: Request) -> Response:
#     name = req.match_info.get('name', "Anonymous")
#     text = "Hello, " + name
#     return web.Response(text=text)

# Listen for incoming requests on /api/messages.
async def messages(req: web.Request) -> web.Response:
    # Main bot message handler.
    if "application/json" in req.headers["Content-Type"]:
        body = await req.json()
    else:
        return web.Response(status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)

    activity = Activity().deserialize(body)
    auth_header = req.headers["Authorization"] if "Authorization" in req.headers else ""

    response = await ADAPTER.process_activity(activity, auth_header, BOT.on_turn)
    if response:
        return web.json_response(data=response.body, status=response.status)
    return web.Response(status=HTTPStatus.OK)

def get_app(argv):
    app = web.Application(middlewares=[bot_telemetry_middleware, aiohttp_error_middleware])
    # app.router.add_get("/", index)

    app.router.add_post("/api/messages", messages)
    return app

if __name__ == "__main__":
    app = get_app(None)
    try:
        web.run_app(app, host="0.0.0.0", port=CONFIG.PORT)
    except Exception as error:
        raise error
