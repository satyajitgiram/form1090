
#flaskapp.wsgi

import sys
sys.path.insert(0, '/var/www/html/puc-api_v2')
 
from gevent.pywsgi import WSGIServer
from main import app as application

