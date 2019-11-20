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

def individual_emails(entity, pipe, reason, mail_header):
    if reason == 'dead-letters':
        msg = Message("SESAM " + mail_header, sender = "erik.leven@sesam.io", recipients = ["erik.leven@sesam.io"])
        msg.body = "The pipe %s failed at %s for entity %s \n \n Original error message: \n %s \n Entity body: \n { \n     country_id: %s \n     email: %s \n     ensure_unique_custom_tag_ids_by_category: %s \n     external_unique_id: %s \n     name: %s \n     office_id: %s \n     role: %s \n     telephone: %s \n }" %(entity['pipe'], entity['event_time'], entity['_id'], entity['original_error_message'], entity['entity']['payload']['user']['country_id'], entity['entity']['payload']['user']['email'], entity['entity']['payload']['user']['ensure_unique_custom_tag_ids_by_category'][list(entity['entity']['payload']['user']['ensure_unique_custom_tag_ids_by_category'].keys())[0]], entity['entity']['payload']['user']['external_unique_id'], entity['entity']['payload']['user']['name'], entity['entity']['payload']['user']['office_id'], entity['entity']['payload']['user']['role'], entity['entity']['payload']['user']['telephone'])
    elif reason == 'currentdepid':
        msg = Message("SESAM" + mail_header, sender = "erik.leven@sesam.io", recipients = ["erik.leven@sesam.io"])
        msg.body = "AD-user %s is a manager but has no CurrentDepartmentID" % entity["employeeID"][0]
    
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