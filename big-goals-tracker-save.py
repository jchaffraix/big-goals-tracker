import logging
import webapp2

class SavePage(webapp2.RequestHandler):
    def post(self):
        logging.info(self.request.body)
        self.response.write("Not implemented")

app = webapp2.WSGIApplication([
    ('/save', SavePage),
# TODO: Should I switch to debug=False?
], debug=True)
