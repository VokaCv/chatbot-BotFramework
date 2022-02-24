# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
"""Main dialog to welcome users."""
from typing import List
from botbuilder.dialogs import Dialog
from botbuilder.core import (
    TurnContext,
    ConversationState,
    UserState,
    BotTelemetryClient,
)
from botbuilder.schema import ChannelAccount
from .dialog_bot import DialogBot


class DialogAndWelcomeBot(DialogBot):
    """Main dialog to welcome users."""

    def __init__(
        self,
        conversation_state: ConversationState,
        user_state: UserState,
        dialog: Dialog,
        telemetry_client: BotTelemetryClient,
    ):
        super(DialogAndWelcomeBot, self).__init__(
            conversation_state, user_state, dialog, telemetry_client
        )
        self.telemetry_client = telemetry_client

    async def on_members_added_activity(
        self, members_added: List[ChannelAccount], turn_context: TurnContext
    ):
        for member in members_added:
            # Greet anyone that was not the target (recipient) of this message.
            # To learn more about Adaptive Cards, see https://aka.ms/msbot-adaptivecards
            # for more details.
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(f"Hi there! I'm a friendly bot and I will try to help you.")