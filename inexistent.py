#from google.appengine.api.logservice.logservice import logservice

import webapp2

# TODO: Prettify.
# TODO: Do a better attribution.
# TODO: Enable logging for real.
class ErrorPage(webapp2.RequestHandler):
    def get(self):
        self.response.write('''
<!DOCTYPE html>
The page you're requesting doesn't exist!<br>
<a href="https://www.flickr.com/photos/armydre2008/19339086155/">
    <img src="images/shocked-raccoon.jpg">
</a>
<!-- Credit: User frankieleon on flickr -->''')

app = webapp2.WSGIApplication([
    ('/.*', ErrorPage)
# TODO: Should I switch to debug=False?
], debug=True)
