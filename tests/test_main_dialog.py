import logging

from aiounittest import AsyncTestCase
from botbuilder.core import MessageFactory

from botbuilder.testing import DialogTestClient, DialogTestLogger

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
        self.assertEqual("Hi, how can I help you?", reply.text)