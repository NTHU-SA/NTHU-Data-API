import pytest
from fastapi.testclient import TestClient

from src import app
from src.api import schemas

client = TestClient(app)


def test_newsletter():
    response = client.get(url="/newsletter/")
    assert response.status_code == 200


@pytest.mark.parametrize(
    "newsletter_name", [_.value for _ in schemas.newsletter.NewsletterName]
)
def test_newsletter_searches(newsletter_name):
    response = client.get(url=f"/newsletters/{newsletter_name}")
    assert response.status_code == 200
