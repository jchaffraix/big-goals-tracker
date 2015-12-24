import logging
import hashlib
import json
import os
import webapp2

from authentication import *

from google.appengine.ext import ndb
from google.appengine.api import users

class EmailSalt(ndb.Model):
    salt = ndb.BlobProperty(indexed = False, required = True)

    @classmethod
    def ancestorKey(cls, user):
        return ndb.Key("UserEmail", user.user_id())

    @classmethod
    def getSalt(cls, user):
        existingSalt = cls.query(ancestor = EmailSalt.ancestorKey(user)).fetch(10)
        if len(existingSalt) > 1:
            raise Exception("Several salts are store for email" + user + ", data corruption is about to happen.")
        elif len(existingSalt) == 0:
            # We need to create the salt. We use the cryptographically secure os.urandom to do so.
            # Per http://www.jasypt.org/howtoencryptuserpasswords.html, the salt should be at least 8 bits.
            # So we settled for 32 bits.
            new_salt = os.urandom(32)
            existingSalt = EmailSalt(parent = EmailSalt.ancestorKey(user),
                                     salt = new_salt)
            existingSalt.put()
            return new_salt
        else:
            return existingSalt[0].salt

    @classmethod
    def hashForUser(cls, user):
        salt = EmailSalt.getSalt(user)
        salted_id = salt + user.user_id()
        hash_id = hashlib.sha256(salted_id).hexdigest()
        return hash_id


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
        return '{"physicalCount":%d,"wellBeingCount":%d,"moneyCount":%d,"relationshipsCount":%d,"totalCount":%d,"updatedDate":"%s"}' % (self.physicalCount, self.wellBeingCount, self.moneyCount, self.relationshipsCount, self.totalCount, self.updatedDate)

    @classmethod
    def ancestorKey(cls, email):
        return ndb.Key("UserEmailHash", EmailSalt.hashForUser(email))

    # TODO: Consolidate the querying logic to avoid parent/ancestor discrepancies.
    @classmethod
    def getLatestSubmittedEntries(cls, user):
        return cls.query(ancestor=Counts.ancestorKey(user)).filter(Counts.submitted == True).order(-cls.updatedDate).fetch(25)

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
                # TODO: Email is not necessarily populated and we use user_id()
                # in the rest of the code. Should this be changed too?
                logging.error("Found %d unsubmitted request for user %s, hell is loose"
                            % (numberOfResults, user.email()))
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
        user = Authentication.userIfAllowed()
        if not user:
            self.response.status_int = 403
            return

        logging.info(self.request.body)
        # The body is a JSON object containing the counts.
        shouldSubmit = False;
        if (self.request.get('submit')):
            shouldSubmit = True
        logging.info("ShouldSubmit: %s" % shouldSubmit)
        Counts.saveCounts(user, self.request.body, shouldSubmit)
        self.response.write("Not implemented")

class GetOldPage(webapp2.RequestHandler):
    def get(self):
        user = Authentication.userIfAllowed()
        if not user:
            self.response.status_int = 403
            return

        logging.info("Requesting info for user: %s" % user.email())
        logs = Counts.getLatestSubmittedEntries(user)
        if len(logs) is 0:
            logging.error("Not old data queried.");
        else:
            jsonifiedLogs = '{"logs":['
            for i in range(0, len(logs)):
                log = logs[i]
                logging.info(log)
                jsonifiedLogs += log.toJSON()
                if i != len(logs) - 1:
                    jsonifiedLogs += ","
            jsonifiedLogs += ']}'
            self.response.write(jsonifiedLogs)

app = webapp2.WSGIApplication([
    ('/save', SavePage),
    ('/getold', GetOldPage),
# TODO: Should I switch to debug=False?
], debug=True)
