# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.


class BookingDetails:
    def __init__(
        self,
        from_city: str = "",
        to_city: str = "",
        from_date: str = "",
        to_date: str = "",
        budget: str = ""
    ):
        self.from_city = from_city
        self.to_city = to_city
        self.from_date = from_date
        self.to_date = to_date
        self.budget = budget
