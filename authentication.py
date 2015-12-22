import logging

from google.appengine.api import users

# TODO: Unit-test
class Authentication:
    @staticmethod
    def userIfAllowed():
        user = users.get_current_user()
        if not user:
            raise Exception("Got an unlogged user!")

        if not users.is_current_user_admin():
            logging.error("Unknown access from %s" % user.email())
            return None
        return user
