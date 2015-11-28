import os
import jinja2
import logging
import webapp2

from google.appengine.api import users

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

class MainPage(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))
            return

        if not users.is_current_user_admin():
            self.response.status_int = 403
            logging.error("Unknown access from %s" % user.email())
            return

        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render())

class OldPage(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))
            return

        if not users.is_current_user_admin():
            self.response.status_int = 403
            logging.error("Unknown access from %s" % user.email())
            return

        template = JINJA_ENVIRONMENT.get_template('old.html')
        self.response.write(template.render())

app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/old', OldPage),
# TODO: Should I switch to debug=False?
], debug=True)
