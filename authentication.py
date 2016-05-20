import hashlib
import logging

from google.appengine.api import users

# TODO: Unit-test
class Authentication:
    known_users = set(["be101762cccb1ff52ca83fdbe45aeb59a919e7088f3fcbdb2d83729a4e65b143"])

    @staticmethod
    def isUserAllowed(user):
        # Sanity check, admins should always be allowed.
        if users.is_current_user_admin():
            return True

        email_hash = hashlib.sha256(user.email().lower()).hexdigest()
        if email_hash in Authentication.known_users:
            return True

        logging.error("Rejected email %s (hash %s)" % (user.email().lower(), email_hash))
        return False

    @staticmethod
    def userIfAllowed():
        user = users.get_current_user()
        if not user:
            raise Exception("Got an unlogged user!")

        if not Authentication.isUserAllowed(user):
            return None
        return user
