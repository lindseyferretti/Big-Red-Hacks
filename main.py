import base64
import os

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
    query = datastore_client.query(kind='Photos')
    image_entities = list(query.fetch())    

    # Return a Jinja2 HTML template.
    return render_template('homepage.html', image_entities=image_entities)

@app.route('/upload_photo', methods=['GET', 'POST'])
def upload_photo():
    # Create a Cloud Storage client.
    storage_client = storage.Client()

    # Get the Cloud Storage bucket that the file will be uploaded to.
    bucket = storage_client.get_bucket(os.environ.get('CLOUD_STORAGE_BUCKET'))

    # Create a new blob and upload the file's content to Cloud Storage.
    photo = request.files['file']
    blob = bucket.blob(photo.filename)
    blob.upload_from_string(
            photo.read(), content_type=photo.content_type)

    # Make the blob publicly viewable.
    blob.make_public()
    image_public_url = blob.public_url
    
    # Create a Cloud Vision client.
    vision_client = vision.ImageAnnotatorClient()

    # Retrieve a Vision API response for the photo stored in Cloud Storage
    source_uri = 'gs://{}/{}'.format(os.environ.get('CLOUD_STORAGE_BUCKET'), blob.name)
    response = vision_client.annotate_image({
        'image': {'source': {'image_uri': source_uri}},
    })
    labels = response.label_annotations
    faces = response.face_annotations
    web_entities = response.web_detection.web_entities

    # Create a Cloud Datastore client
    datastore_client = datastore.Client()

    # The kind for the new entity
    kind = 'Photos'

    # The name/ID for the new entity
    name = blob.name

    # Create the Cloud Datastore key for the new entity
    key = datastore_client.key(kind, name)

    # Construct the new entity using the key. Set dictionary values for entity
    # keys image_public_url and label.
    entity = datastore.Entity(key)
    entity['image_public_url'] = image_public_url
    entity['label'] = labels[0].description

    # Save the new entity to Datastore
    datastore_client.put(entity)

    # Redirect to the home page.
    emotions = []
    for face in faces:
        emotions += [face.joy_likelihood]
        emotions += [face.sorrow_likelihood]
        emotions += [face.anger_likelihood]
        emotions += [face.surprise_likelihood]
        emotions += [face.headwear_likelihood]
    num_emotions = []
    for emotion in emotions:
        num_emotions += [switch(emotion)]

    emojifinal = num_to_emoji(num_emotions)

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
    emojicodes = ["\u1F600","\u2639""\u1F621""\u1F631"]
    J = 0
    SO = 1
    A = 2
    SU = 3
    H = 4
    if values[4] >= 3:
        eistring = "\u1F920"
        return eistring
    values.pop(4)
    if all(values[0] == values for val in values):
        eistring = "\u1F643"
        return eistring
    eistring = emojicodes[values.index(max(values))]
    return eistring



if __name__ == '__main__':
    # This is used when running locally. Gunicorn is used to run the
    # application on Google App Engine. See entrypoint in app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)