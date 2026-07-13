from aiogram.fsm.state import State, StatesGroup


class LeadForm(StatesGroup):
    waiting_full_name = State()
    waiting_phone = State()


class ReceiptForm(StatesGroup):
    waiting_photo = State()


class AdminContent(StatesGroup):
    waiting_new_start_video = State()


class Broadcast(StatesGroup):
    waiting_message = State()


class BookUpload(StatesGroup):
    collecting = State()


class SampleUpload(StatesGroup):
    collecting = State()
