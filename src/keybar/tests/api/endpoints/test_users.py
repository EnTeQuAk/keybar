import pytest
import mock

from keybar.client import Client

from keybar.tests.factories.user import UserFactory
from keybar.tests.factories.device import DeviceFactory, PRIVATE_KEY


@pytest.mark.django_db(transaction=True)
class TestUsersEndpoint:

    @pytest.fixture(autouse=True)
    def setup(self, settings, keybar_liveserver):
        user = UserFactory.create(email='test@none.none', is_superuser=True)
        device = DeviceFactory.create(user=user)
        self.client = Client(device.id, PRIVATE_KEY)
        self.liveserver = keybar_liveserver

    def test_list(self):
        endpoint = '{0}/api/users/'.format(self.liveserver.url)

        response = self.client.get(endpoint)

        assert response.status_code == 200
        assert response.json() == [{
            'date_joined': mock.ANY,
            'email': 'test@none.none',
            'id': mock.ANY
        }]
