#!/usr/bin/env python
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
"""Configuration for the bot."""

import os

from dotenv import load_dotenv


class DefaultConfig:
    """Configuration for the bot."""

    def __init__(self):
        load_dotenv()

        self.PORT = 8000 #3978
        self.CHATBOT_BOT_ID = os.environ.get("CHATBOT_BOT_ID", "bce25a24-e082-44fe-85e6-74db2e3de6d4")
        self.CHATBOT_BOT_PASSWORD = os.environ.get("CHATBOT_BOT_PASSWORD", "ga.7Q~khgL1bfX61t6wstqIsrvu7hfwBTzukw")

        self.LUIS_APP_ID = os.environ.get("LUIS_APP_ID", "cfde1d4c-2cf0-437c-98b9-cdfb6abdbecb")
        self.LUIS_PRED_KEY = os.environ.get("LUIS_PRED_KEY", "6321abe2e88341ecab8981a107c87099")
        self.LUIS_PRED_ENDPOINT = os.environ.get("LUIS_PRED_ENDPOINT", "https://p10luis.cognitiveservices.azure.com/")
        
        self.APPINSIGHTS_INSTRUMENTATIONKEY = os.environ.get("APPINSIGHTS_INSTRUMENTATIONKEY", "7a7bd8f1-6b2a-4ddd-9bd2-ef22e1fd5143")