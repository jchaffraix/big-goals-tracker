import hashlib
import sys

def hash(emails):
    for email in emails:
        print email + " -> " + hashlib.sha256(email).hexdigest()

if __name__ == "__main__":
    hash(sys.argv[1:])
