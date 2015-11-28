import logging
import json
import webapp2

from google.appengine.ext import ndb

class Counts(ndb.Model):
    # We track when this was last modified.
    updatedDate = ndb.DateProperty(auto_now=True)
    relationshipsCount = ndb.IntegerProperty(indexed=False)
    physicalCount = ndb.IntegerProperty(indexed=False)
    wellBeingCount = ndb.IntegerProperty(indexed=False)
    totalCount = ndb.IntegerProperty(indexed=False)
    # Whether the counts where submitted.
    # There should be only one unsubmitted Counts at all time per user.
    submitted = ndb.BooleanProperty()

    @classmethod
    def ancestorKey(cls, user):
        return ndb.Key("User", user)

    @classmethod
    def saveCounts(cls, user, jsonString):
        # TODO: Do some server side validation on the input (totalCount OK, ...).
        parsedJson = json.loads(jsonString)
        #Query a previous instance to be sure.
        unsubmittedCounts = cls.query(ancestor=Counts.ancestorKey("User")).filter(Counts.submitted == False).order(-cls.updatedDate).fetch(10)
        numberOfResults = len(unsubmittedCounts)
        if numberOfResults is 0:
            counts = Counts(relationshipsCount = parsedJson["relationshipsCount"],
                            physicalCount = parsedJson["physicalCount"],
                            wellBeingCount = parsedJson["wellBeingCount"],
                            totalCount = parsedJson["totalCount"],
                            submitted = False)
            counts.put()
        else:
            if numberOfResults > 1:
                logging.error("Found %d unsubmitted request for user %s, hell is loose"
                            % (numberOfResults, user))
                # TODO: Fix the data-store if there is more than one.
            # Update the last result as it's the newest.
            counts = unsubmittedCounts[numberOfResults - 1]
            counts.relationshipsCount = parsedJson["relationshipsCount"],
            counts.physicalCount = parsedJson["physicalCount"],
            counts.wellBeingCount = parsedJson["wellBeingCount"],
            counts.totalCount = parsedJson["totalCount"]
            counts.put()


class SavePage(webapp2.RequestHandler):
    def post(self):
        logging.info(self.request.body)
        # The body is a JSON object containing the counts.
        # TODO: Use the users as the parent to ensure consistency per user.
        user = "Fooo"
        Counts.saveCounts(user, self.request.body)
        self.response.write("Not implemented")

app = webapp2.WSGIApplication([
    ('/save', SavePage),
# TODO: Should I switch to debug=False?
], debug=True)
