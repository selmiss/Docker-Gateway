from flask import Flask
from Images import base as image_base


# build flask app
app = Flask(__name__)

app.register_blueprint(image_base.option)


@app.route('/test')
def test_connection():
    return 'Hello dear, welcome to docker-gateway!'


if __name__ == '__main__':
    # app.debug = True 
    app.run(host='0.0.0.0', port=5000)
