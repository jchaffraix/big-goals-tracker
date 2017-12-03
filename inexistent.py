import logging
import webapp2

# TODO: Prettify.
# TODO: Do a better attribution.
class ErrorPage(webapp2.RequestHandler):
    def get(self):
        logging.error("Unknown GET URL called: %s" % self.request.url)
        self.response.write('''
<!DOCTYPE html>
The page you're requesting doesn't exist!<br>
<a href="https://www.flickr.com/photos/armydre2008/19339086155/">
    <img src="/images/shocked-raccoon.jpg">
</a>
<!-- Credit: User frankieleon on flickr -->''')

    def post(self):
        logging.error("Unknown POST URL called: %s" % self.request.url)
        self.response.status_int = 405

app = webapp2.WSGIApplication([
    ('/.*', ErrorPage)
# TODO: Should I switch to debug=False?
], debug=True)
