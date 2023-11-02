import uuid
from datetime import datetime
from zoneinfo import ZoneInfo


class DataNode:
    def __init__(self) -> None:
        self.id = str(uuid.uuid4())
        self.data = {}
        self.create_time = str(self._gen_now_timestamp())
        self.update_time = str(self._gen_now_timestamp())

    def _gen_now_timestamp(self):
        return datetime.now(tz=ZoneInfo("Asia/Taipei")).strftime("%Y%m%dT%H%M%S%z")


a = DataNode()
