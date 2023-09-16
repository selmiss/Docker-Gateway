from flask import Flask
from flask_cors import CORS
from Images import base as image_base


# build flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
app.register_blueprint(image_base.option)


@app.route('/test')
def test_connection():
    return 'Hello dear, welcome to docker-gateway!'


if __name__ == '__main__':
    # app.debug = True 
    app.run(host='0.0.0.0', port=5000)
