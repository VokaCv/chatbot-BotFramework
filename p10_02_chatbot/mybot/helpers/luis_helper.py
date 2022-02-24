# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
from enum import Enum
from typing import DefaultDict, Dict, Tuple
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

from botbuilder.ai.luis import LuisRecognizer
from botbuilder.core import IntentScore, TopIntent, TurnContext
from datatypes_date_time import Timex

from booking_details import BookingDetails


class Intent(Enum):
    BOOK_FLIGHT = "ReserverVoyage"
    NONE_INTENT = "None"


def top_intent(intents: Dict[Intent, dict]) -> TopIntent:
    max_intent = Intent.NONE_INTENT
    max_value = 0.0

    for intent, value in intents:
        intent_score = IntentScore(value)
        if intent_score.score > max_value:
            max_intent, max_value = intent, intent_score.score

    return TopIntent(max_intent, max_value)


class LuisHelper:
    @staticmethod
    async def execute_luis_query(
        luis_recognizer: LuisRecognizer, turn_context: TurnContext
    ) -> (Intent, object):
        """
        Returns an object with preformatted LUIS results for the bot's dialogs to consume.
        """
        result = None
        intent = None

        try:
            recognizer_result = await luis_recognizer.recognize(turn_context)

            intent = (
                sorted(
                    recognizer_result.intents,
                    key=recognizer_result.intents.get,
                    reverse=True,
                )[:1][0]
                if recognizer_result.intents
                else None
            )
           
            if intent == Intent.BOOK_FLIGHT.value:
                result = BookingDetails()

                # Extract the departure city
                from_city = recognizer_result.entities.get("from_city")
                if from_city:
                    result.from_city = from_city[0]

                # Extract the arrival city
                to_city = recognizer_result.entities.get("to_city")
                if to_city:
                    result.to_city = to_city[0]

                # Extract the datetimes
                datetimes = recognizer_result.entities.get("datetime")
                if datetimes:
                    result.from_date, result.to_date = LuisHelper.extract_datetimes(datetimes)

                # Extract the budget
                money = recognizer_result.entities.get("money")
                budget = recognizer_result.entities.get("budget")
                if money:
                    number = money[0]
                    units = money[0]
                    result.budget = f"{number:0.2f} {units}"
                elif budget:
                    result.budget = budget[0]

        except Exception as exception:
            print(exception)
        
        return intent, result

    @staticmethod
    def extract_datetimes(datetimes: list) -> Tuple[str, str]:
        """"""
        from_date, to_date = "", ""
        now = datetime.now()
        dt_format = "%d-%m-%Y"

        if len(datetimes) == 1:
            if datetimes[0]["type"] == "daterange":
                timex = Timex(datetimes[0]["timex"][0])


                from_date = datetime(
                    timex.year if timex.year else now.year,
                    timex.month if timex.month else now.month,
                    timex.day_of_month if timex.day_of_month else now.day
                )

                to_date = from_date + relativedelta(
                    years=int(timex.years) if timex.years else 0,
                    months=int(timex.months) if timex.months else 0,
                    weeks=int(timex.weeks) if timex.weeks else 0,
                    days=int(timex.days) if timex.days else 0,
                    hours=int(timex.hours) if timex.hours else 0,
                    minutes=int(timex.minutes) if timex.minutes else 0,
                    seconds=int(timex.seconds) if timex.seconds else 0
                )

                from_date = from_date.strftime(dt_format)
                to_date = to_date.strftime(dt_format)

            elif datetimes[0]["type"] == "duration":
                timex = Timex(datetimes[0]["timex"][0])
                from_date = now

                to_date = from_date + relativedelta(
                    years=int(timex.years) if timex.years else 0,
                    months=int(timex.months) if timex.months else 0,
                    weeks=int(timex.weeks) if timex.weeks else 0,
                    days=int(timex.days) if timex.days else 0,
                    hours=int(timex.hours) if timex.hours else 0,
                    minutes=int(timex.minutes) if timex.minutes else 0,
                    seconds=int(timex.seconds) if timex.seconds else 0
                )

                from_date = from_date.strftime(dt_format)
                to_date = to_date.strftime(dt_format)

        elif len(datetimes) == 2:
            if (datetimes[0]["type"] == "date") and (datetimes[1]["type"] == "date"):
                timex = Timex(datetimes[0]["timex"][0])

                dt0 = datetime(
                    timex.year if timex.year else now.year,
                    timex.month if timex.month else now.month,
                    timex.day_of_month if timex.day_of_month else now.day
                )

                timex = Timex(datetimes[1]["timex"][0])

                dt1 = datetime(
                    timex.year if timex.year else now.year,
                    timex.month if timex.month else now.month,
                    timex.day_of_month if timex.day_of_month else now.day
                )

                from_date = min(dt0, dt1)
                to_date = max(dt0, dt1)

                from_date = from_date.strftime(dt_format)
                to_date = to_date.strftime(dt_format)

            elif (datetimes[0]["type"] == "date") and (datetimes[1]["type"] == "duration"):
                timex = Timex(datetimes[0]["timex"][0])

                from_date = datetime(
                    timex.year if timex.year else now.year,
                    timex.month if timex.month else now.month,
                    timex.day_of_month if timex.day_of_month else now.day
                )

                timex = Timex(datetimes[1]["timex"][0])

                to_date = from_date + relativedelta(
                    years=int(timex.years) if timex.years else 0,
                    months=int(timex.months) if timex.months else 0,
                    weeks=int(timex.weeks) if timex.weeks else 0,
                    days=int(timex.days) if timex.days else 0,
                    hours=int(timex.hours) if timex.hours else 0,
                    minutes=int(timex.minutes) if timex.minutes else 0,
                    seconds=int(timex.seconds) if timex.seconds else 0
                )

                from_date = from_date.strftime(dt_format)
                to_date = to_date.strftime(dt_format)

            elif (datetimes[0]["type"] == "duration") and (datetimes[1]["type"] == "date"):
                timex = Timex(datetimes[1]["timex"][0])

                from_date = datetime(
                    timex.year if timex.year else now.year,
                    timex.month if timex.month else now.month,
                    timex.day_of_month if timex.day_of_month else now.day
                )

                timex = Timex(datetimes[0]["timex"][0])

                to_date = from_date + relativedelta(
                    years=int(timex.years) if timex.years else 0,
                    months=int(timex.months) if timex.months else 0,
                    weeks=int(timex.weeks) if timex.weeks else 0,
                    days=int(timex.days) if timex.days else 0,
                    hours=int(timex.hours) if timex.hours else 0,
                    minutes=int(timex.minutes) if timex.minutes else 0,
                    seconds=int(timex.seconds) if timex.seconds else 0
                )

                from_date = from_date.strftime(dt_format)
                to_date = to_date.strftime(dt_format)

        return from_date, to_date
