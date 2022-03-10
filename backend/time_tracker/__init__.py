from flask import Flask, render_template
from .extentions import mongo, cors
from .views import api

 
def create_app(config_obj='time_tracker.settings'):
    app = Flask(__name__, template_folder='templates', static_url_path='/static')
    app.config.from_object(config_obj)
    
    @app.route('/')
    def home():
        return render_template('landing_page.html')

    cors.init_app(app)
    mongo.init_app(app)
   
    api.init_app(app)

    return app