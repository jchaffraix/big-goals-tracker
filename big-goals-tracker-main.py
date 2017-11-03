import os
import logging
import webapp2

from authentication import *

class MainPage(webapp2.RequestHandler):
    def get(self):
        if not users.get_current_user():
            self.redirect(users.create_login_url(self.request.uri))
            return

        if not Authentication.userIfAllowed():
            self.response.status_int = 403
            return

        template = open('index.html').read()
        self.response.write(template)

class OldPage(webapp2.RequestHandler):
    def get(self):
        if not users.get_current_user():
            self.redirect(users.create_login_url(self.request.uri))
            return

        if not Authentication.userIfAllowed():
            self.response.status_int = 403
            return

        template = open('old.html').read()
        self.response.write(template)

app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/old', OldPage),
# TODO: Should I switch to debug=False?
], debug=True)
