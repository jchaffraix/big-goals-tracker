import os
import logging
from flask import Flask, render_template, redirect, request
from google.appengine.api import wrap_wsgi_app

from authentication import *
from save import save_pages

app = Flask(__name__)
app.register_blueprint(save_pages)
app.wsgi_app = wrap_wsgi_app(app.wsgi_app)


@app.route("/")
def main_page_handler():
  if not users.get_current_user():
    return redirect(users.create_login_url(request.full_path))

  if not Authentication.userIfAllowed():
    abort(403)

  template = open('index.html').read()
  return template

@app.route("/old")
def old_page_handler():
  if not users.get_current_user():
    return redirect(users.create_login_url(request.full_path))

  if not Authentication.userIfAllowed():
    abort(403)

  template = open('old.html').read()
  return template

if __name__ == "__main__":
  # This is used when running locally only. When deploying to Google App
  # Engine, a webserver process such as Gunicorn will serve the app. This
  # can be configured by adding an `entrypoint` to app.yaml.
  # Flask's development server will automatically serve static files in
  # the "static" directory. See:
  # http://flask.pocoo.org/docs/1.0/quickstart/#static-files. Once deployed,
  # App Engine itself will serve those files as configured in app.yaml.
  app.run(host="127.0.0.1", port=8080, debug=True)
