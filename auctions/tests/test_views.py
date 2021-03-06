import pytest
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from auctions import views
from auctions.models import Watchlist


class TestIndexView(TestCase):
    def test_index(self):
        client = Client()
        url = reverse("auctions:index")
        response = client.get(url)
        self.assertTemplateUsed(response, "auctions/index.html")
        assert response.status_code == 200


@pytest.mark.django_db
def test_watchlist_owner(user_watchlist):
    assert user_watchlist.user.username == "seyamack"


@pytest.mark.django_db
def test_watchlist_listing(user_watchlist, watchlist_two, watchlist_three):
    assert user_watchlist.listing.title == "puppies for sale"
    assert watchlist_two.listing.title == "for the watchlist"
    assert watchlist_three.listing.title == "3rd on the watchlist"

    watchlist_query = Watchlist.objects.filter(
        user_id=user_watchlist.user
    ).select_related("listing")

    assert watchlist_query[0].listing.title == "puppies for sale"
    assert watchlist_query[1].listing.title == "for the watchlist"
    assert watchlist_query[2].listing.title == "3rd on the watchlist"


@pytest.mark.django_db
def test_new_listing_detail(listing_fixture, user_fixture):

    assert listing_fixture.user == user_fixture

    client = Client()

    response = client.get(
        reverse("auctions:new_listing_detail", kwargs={"slug": listing_fixture.slug})
    )

    assert response.status_code == 200


@pytest.mark.django_db
def test_listing_bids(listing_fixture, user_fixture):
    factory = RequestFactory()
    request = factory.get(f"deets/{listing_fixture.slug}")
    request.user = user_fixture

    response = views.new_listing_detail(request, listing_fixture.slug)
    # breakpoint()
    assert response.status_code == 200
