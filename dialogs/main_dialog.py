# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
import uuid, json, re

from botbuilder.dialogs import (
    ComponentDialog, WaterfallDialog,
    WaterfallStepContext, DialogTurnResult)

from botbuilder.dialogs.prompts import TextPrompt, PromptOptions
from botbuilder.core import MessageFactory, BotTelemetryClient, NullTelemetryClient
from botbuilder.schema import InputHints, Attachment

from booking_details import BookingDetails
from flight_booking_recognizer import FlightBookingRecognizer
from helpers.luis_helper import LuisHelper, Intent
from .booking_dialog import BookingDialog


class MainDialog(ComponentDialog):
    def __init__(
        self,
        luis_recognizer: FlightBookingRecognizer,
        booking_dialog: BookingDialog,
        telemetry_client: BotTelemetryClient = None,
    ):
        super(MainDialog, self).__init__(MainDialog.__name__)
        self.telemetry_client = telemetry_client or NullTelemetryClient()

        text_prompt = TextPrompt(TextPrompt.__name__)
        text_prompt.telemetry_client = self.telemetry_client

        booking_dialog.telemetry_client = self.telemetry_client

        wf_dialog = WaterfallDialog(
            "WFDialog", [self.intro_step, self.act_step, self.final_step]
        )
        wf_dialog.telemetry_client = self.telemetry_client

        self._luis_recognizer = luis_recognizer
        self._booking_dialog_id = booking_dialog.id

        self.add_dialog(text_prompt)
        self.add_dialog(booking_dialog)
        self.add_dialog(wf_dialog)

        self.initial_dialog_id = "WFDialog"

        self.uuid = ""

    async def intro_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        self.uuid = uuid.uuid1().__str__()

        message_text = (
            str(step_context.options)
            if step_context.options
            else "Hi, how can I help You?"
        )
        prompt_message = MessageFactory.text(
            message_text, message_text, InputHints.expecting_input
        )

        return await step_context.prompt(
            TextPrompt.__name__, PromptOptions(prompt=prompt_message)
        )

    async def act_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        # Call LUIS and gather any potential booking details. (Note the TurnContext has the response to the prompt.)
        intent, luis_result = await LuisHelper.execute_luis_query(
            self._luis_recognizer, step_context.context
        )

        if intent == Intent.BOOK_FLIGHT.value and luis_result:
            # Run the BookingDialog giving it whatever details we have from the LUIS call.
            return await step_context.begin_dialog(self._booking_dialog_id, luis_result)
        else:
            didnt_understand_text = (
                "Sorry, I did not understand. Can you rephrase your question?"
            )
            didnt_understand_message = MessageFactory.text(
                didnt_understand_text, didnt_understand_text, InputHints.ignoring_input
            )
            await step_context.context.send_activity(didnt_understand_message)

        return await step_context.next(None)

    async def final_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        # If the child dialog ("BookingDialog") was cancelled or the user failed to confirm,
        # the Result here will be null.
        if step_context.result is not None:
            # TRACK TELEMETRY IN BOOKING DIALOG RATHER THAN HERE
            # # Log the TP
            # properties = {}
            # properties["mainDialogUuid"] = self.uuid
            # self.telemetry_client.track_event("TP", properties)

            result = step_context.result

            # Now we have all the booking details call the booking service.
            msg_txt = ("Thank you, your flight is booked. Check your email for the confirmation.")
            message = MessageFactory.text(msg_txt, msg_txt, InputHints.ignoring_input)

            # # if you want to add a card at the end as recap
            # card = self.create_adaptive_card_attachment(result)
            # message = MessageFactory.attachment(card)
            
            await step_context.context.send_activity(message)
        else:
            # # Log the TN
            # properties = {}
            # properties["mainDialogUuid"] = self.uuid
            # self.telemetry_client.track_event("TN", properties)
            pass

        self.uuid = ""

        prompt_message = "What else can I do for you?"
        return await step_context.replace_dialog(self.id, prompt_message)


    # Create internal function
    def replace(self, templateCard: dict, data: dict):
        string_temp = str(templateCard)
        for key in data:
            pattern = "\${" + key + "}"
            string_temp = re.sub(pattern, str(data[key]), string_temp)
        return eval(string_temp)


    # Load attachment from file.
    def create_adaptive_card_attachment(self, result):
        """Create an adaptive card."""
        
        path =  "cards/bookedFlightCard.json" #need to create this
        with open(path) as card_file:
            card = json.load(card_file)
        
        origin = result.from_city
        destination = result.to_city
        start_date = result.from_date
        end_date = result.to_date
        budget = result.budget

        templateCard = {
            "origin": origin, 
            "destination": destination,
            "start_date": start_date,
            "end_date": end_date,
            "budget": budget}

        flightCard = self.replace(card, templateCard)

        return Attachment(
            content_type="application/vnd.microsoft.card.adaptive", content=flightCard)