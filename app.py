from flask import Flask
from flask_bcrypt import Bcrypt

import auth
import events
import config
import db
import organisation
import os

UPLOAD_FOLDER = 'static/uploads'


def register_blueprints(app):
    """Register Flask blueprints."""
    app.register_blueprint(auth.blueprint)
    app.register_blueprint(events.blueprint)
    app.register_blueprint(organisation.blueprint)

def register_extensions(app):
    """Register Flask extensions."""
    bcrypt = Bcrypt(app)
    return None


app = Flask(__name__)
register_blueprints(app)
register_extensions(app)
app.config.from_object(config)
app.teardown_appcontext(db.close_database_connection)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route('/')
def hello_world():
    return 'Hello, World!'
