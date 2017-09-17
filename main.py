import base64
import os
from PIL import Image
import re
from io import StringIO
import random
import urllib
import json

from binascii import a2b_base64

from flask import Flask, redirect, render_template, request
from google.cloud import datastore
from google.cloud import storage
from google.cloud import vision


app = Flask(__name__)


@app.route('/')
def homepage():
    # Create a Cloud Datastore client.
    datastore_client = datastore.Client()

    # Use the Cloud Datastore client to fetch information from Datastore about
    # each photo.
    query = datastore_client.query(kind='Blob')
    image_entities = list(query.fetch())    

    # Return a Jinja2 HTML template.
    return render_template('homepage.html', image_entities=image_entities)

@app.route('/upload_photo', methods=['GET', 'POST'])
def upload_photo():
    # Create a Cloud Storage client.
    storage_client = storage.Client()

    # Get the Cloud Storage bucket that the file will be uploaded to.
    bucket = storage_client.get_bucket(os.environ.get('BUCKET'))

    # Create a new blob and upload the file's content to Cloud Storage.
    # image_b64 = request.values['file']
    # image_data = re.sub('^data:image/.+;base64,', '', image_b64).decode('base64')
    # image_PIL = Image.open(StringIO(image_b64))
    #
    # image_PIL.save("image.png")

    # print("fml")
    # print(request.data)

    dataDict = json.loads(request.data.decode(encoding='UTF-8'))

    print(dataDict['weirdImg'])

    imgData = urllib.parse.unquote(dataDict['weirdImg'])
    print(imgData)

    blob = bucket.blob("image.png")
    blob.upload_from_string(
        imgData)
    print("Got to spot 1")
    # Make the blob publicly viewable.
    blob.make_public()
    image_public_url = blob.public_url
    print("Got to spot 2")

    # Create a Cloud Vision client.
    vision_client = vision.ImageAnnotatorClient()

    # Retrieve a Vision API response for the photo stored in Cloud Storage
    source_uri = 'gs://{}/{}'.format(os.environ.get('BUCKET'), blob.name)
    response = vision_client.annotate_image({
        'image': {'content': imgData.encode()},
    })

    print(response)

    print("Got to spot 3")
    labels = response.label_annotations
    faces = response.face_annotations
    web_entities = response.web_detection.web_entities
    print("Got to spot 4")

    # Create a Cloud Datastore client
    datastore_client = datastore.Client()

    # The kind for the new entity
    kind = 'Photos'

    # The name/ID for the new entity
    name = blob.name

    # Create the Cloud Datastore key for the new entity
    key = datastore_client.key(kind, name)
    print("Got to spot 5")

    # Construct the new entity using the key. Set dictionary values for entity
    # keys image_public_url and label.
    # entity = datastore.Entity(key)
    # entity['image_public_url'] = image_public_url
    #
    #
    #
    #
    # #labels[0].description = "butt"
    #
    #
    #
    #
    # entity['label'] = labels[0].description
    # print("Got to spot 6")
    #
    # # Save the new entity to Datastore
    # datastore_client.put(entity)
    # print("Got to spot 7")

    # Redirect to the home page.
    emotions = []
    for face in faces:
        emotions += [face.joy_likelihood]
        emotions += [face.sorrow_likelihood]
        emotions += [face.anger_likelihood]
        emotions += [face.surprise_likelihood]
        emotions += [face.headwear_likelihood]
    if len(emotions) > 0:
        emojifinal = num_to_emoji(emotions)
    else:
        print("no face")
        emojifinal = "No face detected"

    return render_template('homepage.html', labels=labels, faces=faces, web_entities=web_entities, public_url=image_public_url,emojifinal=emojifinal)


@app.errorhandler(500)
def server_error(e):
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500

def switch(emo):
    return{
        'UNKNOWN' : 0,
        'VERY_UNLIKELY': 1,
        'UNLIKELY' : 2,
        'POSSIBLE' : 3,
        'LIKELY' : 4,
        'VERY_LIKELY': 5
    }.get(emo,0)

def num_to_emoji(values):
    ejstring = ""
    emojicodes = ["\U0001F600","\U00002639","\U0001F620","\U0001F631"]
    J = 0
    SO = 1
    A = 2
    SU = 3
    H = 4
    if values[4] >= 3:
        eistring = "\U0001F920"
        return eistring
    values.pop()
    if (values[0] == values[1] and values[1] == values[2] )or\
        (values[1] == values[2] and values[2] == values[3]) or\
            (values[0] == values[2] and values[2] == values[3]):
        eistring = "\U0001F643"
        return eistring

    if (values[0] == values[1] and values[1] == values[2] and values[2] == values[3]):
        eistring = "\U0001F643"
        return eistring

    if (values[J] == values[SO]):
        eistring = '\U0001F610'
        return eistring

    eistring = emojicodes[values.index(max(values))]
    return eistring



if __name__ == '__main__':
    # This is used when running locally. Gunicorn is used to run the
    # application on Google App Engine. See entrypoint in app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)