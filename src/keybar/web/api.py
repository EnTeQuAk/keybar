from rest_framework.views import APIView
from rest_framework.response import Response

from keybar.models.user import User


# Only for testing...
class ListUsersView(APIView):

    def get(self, request, format=None):
        usernames = [user.username for user in User.objects.all()]
        return Response(usernames)
