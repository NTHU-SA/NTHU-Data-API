import pytest
from fastapi.testclient import TestClient

from src import app

client = TestClient(app)
path_list = ["https://bulletin.site.nthu.edu.tw/p/403-1086-5081-1.php?Lang=zh-tw"]


@pytest.mark.parametrize("full_path", path_list)
def test_scrapers(full_path):
    response = client.get(url=f"/scrapers/rpage/announcements/{full_path}")
    assert response.status_code == 200
