import logging
import hashlib
import json
import os

from authentication import *

from google.cloud import ndb
from google.appengine.api import users

from flask import Blueprint, redirect, request
save_pages = Blueprint('save_page', __name__)

ds_client = ndb.Client()

# This class stores the salt associated with a user.
# While this is not strictly required as we don't store sensitive
# information such as some passwords or the email itself, this hardens
# the datastore against finding out who uses the service.
class EmailSalt(ndb.Model):
    salt = ndb.BlobProperty(indexed = False, required = True)

    @classmethod
    def ancestorKey(cls, user):
        return ndb.Key("UserEmail", user.user_id())

    @classmethod
    def getSalt(cls, user):
      with ds_client.context():
        existingSalt = cls.query(ancestor = EmailSalt.ancestorKey(user)).fetch(10)
        if len(existingSalt) > 1:
          raise Exception("Several salts are stored for email" + user + ", data corruption is about to happen.")
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
    physicalCount = ndb.IntegerProperty(indexed=False, repeated=True)
    wellBeingCount = ndb.IntegerProperty(indexed=False, repeated=True)
    moneyCount = ndb.IntegerProperty(indexed=False, repeated=True)
    relationshipsCount = ndb.IntegerProperty(indexed=False, repeated=True)
    # Whether the counts where submitted.
    # There should be only one unsubmitted Counts at all time per user.
    submitted = ndb.BooleanProperty()

    def toJSONSummary(self):
        return '{"physicalCount":%d,"wellBeingCount":%d,"moneyCount":%d,"relationshipsCount":%d,"updatedDate":"%s"}' % (len(self.physicalCount), len(self.wellBeingCount), len(self.moneyCount), len(self.relationshipsCount), self.updatedDate)

    def toFullJSON(self):
        return '{"physicalCount":%s,"wellBeingCount":%s,"moneyCount":%s,"relationshipsCount":%s,"updatedDate":"%s"}' % (str(self.physicalCount), str(self.wellBeingCount), str(self.moneyCount), str(self.relationshipsCount), self.updatedDate)

    @classmethod
    def ancestorKey(cls, email):
        return ndb.Key("UserEmailHash", EmailSalt.hashForUser(email))

    @classmethod
    def getLatestSubmittedEntries(cls, user):
      with ds_client.context():
        return cls.query(ancestor=Counts.ancestorKey(user)).filter(Counts.submitted == True).order(-cls.updatedDate).fetch(25)

    @classmethod
    def getUnsubmittedCount(cls, user):
      with ds_client.context():
        return cls.query(ancestor=Counts.ancestorKey(user)).filter(Counts.submitted == False).order(-cls.updatedDate).fetch(10)

    @classmethod
    def saveCounts(cls, user, jsonString, shouldSubmit):
      with ds_client.context():
        # TODO: Do some server side validation on the input.
        parsedJson = json.loads(jsonString)
        #Query a previous instance to be sure.
        unsubmittedCounts = cls.query(ancestor=Counts.ancestorKey(user)).filter(Counts.submitted == False).order(-cls.updatedDate).fetch(10)
        numberOfResults = len(unsubmittedCounts)
        logging.info("Found %d unsubmitted queries" % numberOfResults)
        if numberOfResults == 0:
            counts = Counts(parent = Counts.ancestorKey(user),
                            physicalCount = parsedJson["physicalCount"],
                            wellBeingCount = parsedJson["wellBeingCount"],
                            moneyCount = parsedJson['moneyCount'],
                            relationshipsCount = parsedJson["relationshipsCount"],
                            submitted = shouldSubmit)
            counts.put()
        else:
            if numberOfResults > 1:
                raise Exception("Found %d unsubmitted count for user %s, something is very wrong."
                                 % (numberOfResults, user.email()))

            # Update the last result as it's the newest.
            counts = unsubmittedCounts[numberOfResults - 1]
            counts.physicalCount = parsedJson["physicalCount"]
            counts.wellBeingCount = parsedJson["wellBeingCount"]
            counts.moneyCount = parsedJson['moneyCount']
            counts.relationshipsCount = parsedJson["relationshipsCount"]
            if (shouldSubmit):
                counts.submitted = True
                logging.info("Submitted counts: %s" % counts)
            counts.put()


@save_pages.route('/save', methods=['POST'])
def save_page_handler():
    user = Authentication.userIfAllowed()
    if not user:
        abort(403)

    # TODO: Flask discourage calling get_data without looking at Content-Length.
    body = request.get_data()
    logging.info(body)
    # The body is a JSON object containing the counts.
    shouldSubmit = False;
    if (request.args.get('submit')):
        shouldSubmit = True
    Counts.saveCounts(user, body, shouldSubmit)
    return "Saved"

@save_pages.route('/unsubmitted')
def get_unsubmitted_handler():
    user = Authentication.userIfAllowed()
    if not user:
      abort(403)

    unsubmittedCounts = Counts.getUnsubmittedCount(user)
    if len(unsubmittedCounts) > 1:
      logging.error("More than one unsubmitted count for "
                    + Counts.ancestorKey(user))
    elif len(unsubmittedCounts) == 1:
      # TODO: This doesn't set Content-Type correctly.
      return unsubmittedCounts[0].toFullJSON()

    # Note that we don't return any value if there is no unsubmitted count.

@save_pages.route('/getold')
def get_old_page_handler():
    user = Authentication.userIfAllowed()
    if not user:
      abort(403)

    logging.info("Requesting info for user: %s" % user.email())
    logs = Counts.getLatestSubmittedEntries(user)
    if len(logs) == 0:
        logging.error("Not old data queried.");
    else:
        summed_logs = []
        for i in range(0, len(logs)):
            log = logs[i]
            logging.info(log)
            summed_logs += log.toJSONSummary()
        return {'logs': summed_logs}
