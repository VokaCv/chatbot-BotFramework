# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
"""Flight booking dialog."""

from datatypes_date_time.timex import Timex

from botbuilder.dialogs import WaterfallDialog, WaterfallStepContext, DialogTurnResult
from botbuilder.dialogs.prompts import ConfirmPrompt, TextPrompt, PromptOptions, PromptCultureModels
from botbuilder.dialogs.choices import Choice, ChoiceFactoryOptions
from botbuilder.core import MessageFactory, BotTelemetryClient, NullTelemetryClient
from .cancel_and_help_dialog import CancelAndHelpDialog
from .date_resolver_dialog import DateResolverDialog


class BookingDialog(CancelAndHelpDialog):
    """Flight booking implementation."""

    def __init__(
        self,
        dialog_id: str = None,
        telemetry_client: BotTelemetryClient = NullTelemetryClient(),
    ):
        super(BookingDialog, self).__init__(
            dialog_id or BookingDialog.__name__, telemetry_client
        )
        self.telemetry_client = telemetry_client
        text_prompt = TextPrompt(TextPrompt.__name__)
        text_prompt.telemetry_client = telemetry_client

        waterfall_dialog = WaterfallDialog(
            WaterfallDialog.__name__,
            [
                self.from_city_step,
                self.to_city_step,
                self.from_date_step,
                self.to_date_step,
                self.budget_step,
                self.confirm_step,
                self.final_step,
            ],
        )
        waterfall_dialog.telemetry_client = telemetry_client

        self.add_dialog(text_prompt)

        # BUG : We map all cultures to English, else there is a misunderstanding
        # between English (Yes, No) and French (Oui, Non).
        default_locale = {
            c.locale: (
                Choice(PromptCultureModels.English.yes_in_language),
                Choice(PromptCultureModels.English.no_in_language),
                ChoiceFactoryOptions(
                    PromptCultureModels.English.separator,
                    PromptCultureModels.English.inline_or,
                    PromptCultureModels.English.inline_or_more,
                    True
                ),
            )
            for c in PromptCultureModels.get_supported_cultures()
        }

        self.add_dialog(ConfirmPrompt(ConfirmPrompt.__name__, default_locale=default_locale))
        self.add_dialog(
            DateResolverDialog(
                DateResolverDialog.__name__ + "_from_date",
                self.telemetry_client,
                "When do you want to leave?"
            )
        )
        self.add_dialog(
            DateResolverDialog(
                DateResolverDialog.__name__ + "_to_date",
                self.telemetry_client,
                "When do you want to come back?"
            )
        )
        self.add_dialog(waterfall_dialog)

        self.initial_dialog_id = WaterfallDialog.__name__

    async def from_city_step(
        self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        """Prompt for from_city."""
        booking_details = step_context.options

        if not booking_details.from_city:
            return await step_context.prompt(
                TextPrompt.__name__,
                PromptOptions(
                    prompt=MessageFactory.text("From what city will you be departing?")
                ),
            )

        return await step_context.next(booking_details.from_city)

    async def to_city_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """Prompt for to_city."""
        booking_details = step_context.options

        # Capture the response to the previous step's prompt
        booking_details.from_city = step_context.result

        if not booking_details.to_city:
            return await step_context.prompt(
                TextPrompt.__name__,
                PromptOptions(
                    prompt=MessageFactory.text("To what city would you like to travel?")
                ),
            )

        return await step_context.next(booking_details.to_city)

    async def from_date_step(
        self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        """Prompt for travel date.
        This will use the DATE_RESOLVER_DIALOG."""

        booking_details = step_context.options

        # Capture the results of the previous step
        booking_details.to_city = step_context.result

        if not booking_details.from_date:
            return await step_context.begin_dialog(
                DateResolverDialog.__name__ + "_from_date", booking_details.from_date
            )

        return await step_context.next(booking_details.from_date)

    async def to_date_step(
        self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        """Prompt for travel date.
        This will use the DATE_RESOLVER_DIALOG."""

        booking_details = step_context.options

        # Capture the results of the previous step
        booking_details.from_date = step_context.result

        if not booking_details.to_date:
            return await step_context.begin_dialog(
                DateResolverDialog.__name__ + "_to_date", booking_details.to_date
            )

        return await step_context.next(booking_details.to_date)

    async def budget_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """Prompt for budget."""
        booking_details = step_context.options

        # Capture the response to the previous step's prompt
        booking_details.to_date = step_context.result

        if not booking_details.budget:
            return await step_context.prompt(
                TextPrompt.__name__,
                PromptOptions(
                    prompt=MessageFactory.text("What is your budget?")
                ),
            )

        return await step_context.next(booking_details.budget)
    
    async def confirm_step(
        self, step_context: WaterfallStepContext
    ) -> DialogTurnResult:
        """Confirm the information the user has provided."""
        booking_details = step_context.options

        # Capture the results of the previous step
        booking_details.budget = step_context.result

        msg = (
            "Please confirm that:\n"
            "- You want to **book a flight**.\n"
            f"- From **{booking_details.from_city}** to **{booking_details.to_city}**.\n"
            f"- Between the **{booking_details.from_date}** and the **{booking_details.to_date}**.\n"
            f"- With a budget of **{booking_details.budget}**."
        )

        # Offer a YES/NO prompt.
        return await step_context.prompt(
            ConfirmPrompt.__name__, PromptOptions(prompt=MessageFactory.text(msg))
        )

    async def final_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        """Complete the interaction and end the dialog."""
        booking_details = step_context.options

        # TRACK THE DATA INTO Application INSIGHTS
        # more here https://docs.microsoft.com/en-us/azure/azure-monitor/app/api-custom-events-metrics
        properties = {}
        properties["origin"] = booking_details.from_city
        properties["destination"] = booking_details.to_city
        properties["departure_date"] = booking_details.from_date
        properties["return_date"] = booking_details.to_date
        properties["budget"] = booking_details.budget


        # severity levels as per  App Insight doc
        severity_level = {0: "Verbose",
                          1: "Information",
                          2: "Warning",
                          3: "Error",
                          4: "Critical",
                        }

        if step_context.result:
            # booking_details = step_context.options

            # TRACK THE DATA INTO Application INSIGHTS
            # INFO, ERROR are severity levels reported to App Insight
            self.telemetry_client.track_trace("YES answer", properties, severity_level[1])
            return await step_context.end_dialog(booking_details)
        else:
            # TRACK THE DATA INTO Application INSIGHTS
            self.telemetry_client.track_trace("NO answer", properties, severity_level[3])

        return await step_context.end_dialog()
