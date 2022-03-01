import logging

from aiounittest import AsyncTestCase
from botbuilder.core import MessageFactory

from botbuilder.testing import DialogTestClient, DialogTestLogger
from pathlib import Path
import os, sys


# Add parent paskage to sys.path so it can be imported (in child folder)
def find_pckg(pckg_name, starting_point=""):  
    if starting_point == "":
        starting_point =  str(Path(os.path.realpath(__file__)).parent)       
    
    found_in = starting_point

    while not pckg_name in os.listdir(found_in):
        found_in_before = found_in
        found_in = Path(found_in).parent

        if found_in_before == found_in:
            return None

    if found_in not in sys.path:
        sys.path.append(str(found_in))
    return str(found_in)

# name of the package to add
path = find_pckg("dialogs")

from dialogs import BookingDialog, MainDialog


class DialogTestClientTest(AsyncTestCase):
    """Tests for dialog test client."""

    def __init__(self, *args, **kwargs):
        super(DialogTestClientTest, self).__init__(*args, **kwargs)
        logging.basicConfig(format="", level=logging.INFO)

    def test_init(self):
        client = DialogTestClient(channel_or_adapter="test", target_dialog=None)
        self.assertIsInstance(client, DialogTestClient)

    def test_init_with_custom_channel_id(self):
        client = DialogTestClient(channel_or_adapter="custom", target_dialog=None)
        self.assertEqual("custom", client.test_adapter.template.channel_id)

    async def test_component_dialog(self):
        BOOKING_DIALOG = BookingDialog()
        DIALOG = MainDialog(None, BOOKING_DIALOG)
        
        client = DialogTestClient(
            "test",
            DIALOG,
            initial_dialog_options=None,
            middlewares=[DialogTestLogger()],
        )

        reply = await client.send_activity("hello")
        self.assertEqual("Hi, how can I help You?", reply.text)