import hashlib
import logging

from google.appengine.api import users

# TODO: Unit-test
class Authentication:
    @staticmethod
    def isUserAllowed(user):
        # Sanity check, admins should always be allowed.
        if users.is_current_user_admin():
            return True

        logging.error(hashlib.algorithms_guaranteed)
        email_hash = hashlib.sha256(user.email().lower()).hexdigest()
        return email_hash == "be101762cccb1ff52ca83fdbe45aeb59a919e7088f3fcbdb2d83729a4e65b143"

    @staticmethod
    def userIfAllowed():
        user = users.get_current_user()
        if not user:
            raise Exception("Got an unlogged user!")

        if not Authentication.isUserAllowed(user):
            logging.error("Unknown access from %s" % user.email())
            return None
        return user
