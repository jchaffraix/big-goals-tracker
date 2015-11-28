import logging
import json
import webapp2

from google.appengine.ext import ndb
from google.appengine.api import users

class Counts(ndb.Model):
    # We track when this was last modified.
    updatedDate = ndb.DateProperty(auto_now=True)
    physicalCount = ndb.IntegerProperty(indexed=False)
    wellBeingCount = ndb.IntegerProperty(indexed=False)
    moneyCount = ndb.IntegerProperty(indexed=False)
    relationshipsCount = ndb.IntegerProperty(indexed=False)
    totalCount = ndb.IntegerProperty(indexed=False)
    # Whether the counts where submitted.
    # There should be only one unsubmitted Counts at all time per user.
    submitted = ndb.BooleanProperty()

    def toJSON(self):
        return '{"physicalCount":%d,"wellBeingCount":%d,"moneyCount":%d,"relationshipsCount":%d,"totalCount":%d}' % (self.physicalCount, self.wellBeingCount, self.moneyCount, self.relationshipsCount, self.totalCount)

    @classmethod
    def ancestorKey(cls, user):
        return ndb.Key("User", user)

    # TODO: Consolidate the querying logic to avoid parent/ancestor discrepancies.
    @classmethod
    def getLatestSubmittedEntry(cls, user):
        return cls.query(ancestor=Counts.ancestorKey(user)).filter(Counts.submitted == True).order(-cls.updatedDate).fetch(1)

    @classmethod
    def saveCounts(cls, user, jsonString, shouldSubmit):
        # TODO: Do some server side validation on the input (totalCount OK, ...).
        parsedJson = json.loads(jsonString)
        #Query a previous instance to be sure.
        unsubmittedCounts = cls.query(ancestor=Counts.ancestorKey(user)).filter(Counts.submitted == False).order(-cls.updatedDate).fetch(10)
        numberOfResults = len(unsubmittedCounts)
        logging.info("Found %d unsubmitted queries" % numberOfResults)
        if numberOfResults is 0:
            counts = Counts(parent = Counts.ancestorKey(user),
                            physicalCount = parsedJson["physicalCount"],
                            wellBeingCount = parsedJson["wellBeingCount"],
                            moneyCount = parsedJson['moneyCount'],
                            relationshipsCount = parsedJson["relationshipsCount"],
                            totalCount = parsedJson["totalCount"],
                            submitted = shouldSubmit)
            counts.put()
        else:
            if numberOfResults > 1:
                logging.error("Found %d unsubmitted request for user %s, hell is loose"
                            % (numberOfResults, user))
                # TODO: Fix the data-store if there is more than one.
            # Update the last result as it's the newest.
            counts = unsubmittedCounts[numberOfResults - 1]
            counts.physicalCount = parsedJson["physicalCount"]
            counts.wellBeingCount = parsedJson["wellBeingCount"]
            counts.moneyCount = parsedJson['moneyCount']
            counts.relationshipsCount = parsedJson["relationshipsCount"]
            counts.totalCount = parsedJson["totalCount"]
            if (shouldSubmit):
                counts.submitted = True
                logging.info("Submitted counts: %s" % counts)
            counts.put()


class SavePage(webapp2.RequestHandler):
    def post(self):
        user = users.get_current_user()
        if not user:
            self.response.status_int = 403
            return

        # TODO: Build a single point of checks.
        if not users.is_current_user_admin():
            self.response.status_int = 403
            return

        logging.info(self.request.body)
        # The body is a JSON object containing the counts.
        shouldSubmit = False;
        if (self.request.get('submit')):
            shouldSubmit = True
        logging.info("ShouldSubmit: %s" % shouldSubmit)
        # TODO: Hash and salt the user email.
        Counts.saveCounts(user.email(), self.request.body, shouldSubmit)
        self.response.write("Not implemented")

class GetOldPage(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if not user:
            self.response.status_int = 403
            return

        # TODO: Build a single point of checks.
        if not users.is_current_user_admin():
            self.response.status_int = 403
            return

        logging.info("Requesting info for user: %s" % user.email())
        log = Counts.getLatestSubmittedEntry(user.email())
        if len(log) is 0:
            logging.error("Not old data queried.");
        elif len(log) > 1:
            logging.error("Requested one submitted entry, got %d!!!." % len(log));
            self.response.status_int = 500
        else:
            logging.info(log[0])
            jsonifiedLog = log[0].toJSON()
            logging.info(jsonifiedLog)
            self.response.write(jsonifiedLog)

app = webapp2.WSGIApplication([
    ('/save', SavePage),
    ('/getold', GetOldPage),
# TODO: Should I switch to debug=False?
], debug=True)
