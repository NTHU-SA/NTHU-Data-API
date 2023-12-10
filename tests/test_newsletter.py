import pytest
from fastapi.testclient import TestClient

from src import app
from src.api import schemas

client = TestClient(app)
newsletter_link_list = [
    "https://newsletter.cc.nthu.edu.tw/nthu-list/index.php/zh/home-zh-tw/listid-44-"
]


# def test_newsletter():
#     response = client.get(url=f"/newsletter/")
#     assert response.status_code == 200


# @pytest.mark.parametrize(
#     "newsletter_name", [_.value for _ in schemas.newsletter.NewsletterName]
# )
# def test_newsletter_searches(newsletter_name):
#     response = client.get(url=f"/newsletters/{newsletter_name}")
#     assert response.status_code == 200


# @pytest.mark.parametrize("newsletter_link", newsletter_link_list)
# def test_newsletter_paths_link(newsletter_link):
#     response = client.get(url=f"/newsletters/paths/{newsletter_link}")
#     assert response.status_code == 200
