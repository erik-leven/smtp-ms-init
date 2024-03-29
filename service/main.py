from flask import Flask, request, jsonify
import sys
sys.path.append("/usr/local/lib/python2.7/dist-packages/")
from flask_mail import Message, Mail
import logging
import requests
import json
import os

app = Flask(__name__)
mail = Mail(app)

def get_env(var):
    envvar = None
    if var.upper() in os.environ:
        envvar = os.environ[var.upper()]
    return envvar

base_url = get_env('BASE_URL')
app.config['MAIL_SERVER']='smtp.bouvet.no'
app.config['MAIL_PORT'] = 25
app.config['MAIL_USE_TLS'] = False
mail = Mail(app)

logger = logging.getLogger('Bouvet-smtp')
format_string = '%(asctime)s - %(lineno)d - %(levelname)s - %(message)s'
stdout_handler = logging.StreamHandler()
stdout_handler.setFormatter(logging.Formatter(format_string))
logger.addHandler(stdout_handler)
logger.setLevel(logging.INFO)

def find_key_string(dictionary):
    string = ""
    for i, key in enumerate(dictionary.keys()):
        try:
            string +="\n" + key + ": " + "{" + find_key_string(dictionary[key]) + "}"  
        except AttributeError:
            string 
            string += "\n" + key + ": " + dictionary[key]
    return string

def individual_emails(entity, pipe, reason, mail_header):
    if reason == 'dead-letters':
        payload = find_key_string(entity['entity']['payload'])
        msg.body = "The pipe %s failed at %s for entity %s \n\nOriginal error message: \n\n%s \nEntity body: %s \n\nFor more information, please contact support@sesam.io or your direct Sesam contact." %(entity['pipe'], entity['event_time'], entity['_id'], entity['original_error_message'], payload)
    elif reason == 'currentdepid':
        msg = Message("SESAM" + mail_header, sender = "dont-reply@sesam.io", recipients = [get_env('MAIL_RECEIVER')])
        msg.body = "AD-user %s is a manager but has no CurrentDepartmentID \n For more information, please contact support@sesam.io or your direct Sesam contact." % entity["employeeID"][0]
    
    try:
        mail.send(msg)
    except Exception as e:
        logger.error("Error during email-constuction: {}".format(e))

@app.route('/<string:pipe>/<string:reason>/<string:mail_header>', methods=['GET','POST'])
def main_func(pipe, reason, mail_header):
    entities = request.get_json()

    if len(entities) == 0:
        return "Done"
    else:
        for entity in entities:
            individual_emails(entity, pipe, reason, mail_header)
    delete_entities(entities, pipe)
    return "Done"

@app.route('/', methods=['GET','POST'])
def delete_entities(entities, pipe):
    header = {'Authorization': "Bearer {}".format(get_env('SESAM_JWT')), "content_type": "application/json"}
    for entity in entities:
        entity["_deleted"] = True
        try:
            entity['_id'] = entity['type'][0][2:] + ':' + entity['_id']
        except KeyError:
            pass
        try:
            del entity['thumbnailPhoto']
        except KeyError:
            pass
        resp = requests.post(base_url + "datasets/%s/entities" % pipe, headers=header, data=json.dumps(entity), verify=False)
        if resp.status_code != 200:
            logger.error("Error in post to Sesam: status_code = {} for _id: {}".format(resp.status_code, entity['_id']))
    logger.info("Mail sent")
    
if __name__ == '__main__':

    # This is used when running locally. Gunicorn is used to run the
    # application on Google App Engine. See entrypoint in app.yaml.
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)