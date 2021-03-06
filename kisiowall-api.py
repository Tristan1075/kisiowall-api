from flask import Flask, jsonify
from flask_api import status
from datetime import datetime, timedelta
from random import randint
import logging
import requests
import yaml
import pytz
import json


CONFIGURATION_FILE = "kisiowall-api.yaml"
config = None


app_api = Flask(__name__)


class KisioWallApiConfigLoad(Exception):
    pass


@app_api.route("/total_call")
def get_total_call():
    """
    Get Sum call since navitia creation.
    :return: json
    """
    content = None
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    # Define count user before newrelic
    active_visitors_before_newrelics = 1025779805

    today = datetime.now().strftime("%Y-%m-%dT00:00:00+00:00")

    # Define data to post
    data = ['names[]=HttpDispatcher&from=2016-05-14T00:00:00+00:00&to=%s&summarize=true' % today,
            'names[]=HttpDispatcher&from=%s&summarize=true' % today]

    try:
        for d in data:
            # Send http requests
            r = requests.get(config['url_newrelic'], headers=config['headers_newrelic'], params=d)

            if r.status_code == 200 and content is None:
                content = r.json()

                # Append with count user before newrelic
                content['metric_data']['metrics'][0]['timeslices'][0]['values']['call_count'] += active_visitors_before_newrelics

                status_code = status.HTTP_200_OK
            elif r.status_code == 200 and content is not None:
                content['metric_data']['metrics'][0]['timeslices'][0]['values']['call_count'] += r.json()['metric_data']['metrics'][0]['timeslices'][0]['values']['call_count']
                status_code = status.HTTP_200_OK
            else:
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    except Exception as e:
        content = str(e)

    return jsonify(content), status_code


@app_api.route("/last_review")
def last_review():
    """
    Get the last 5-star review
    :return: json
    """
    content = None
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    try:
        dl_response = make_request("/reviews?stars=5&lang=fr&sort=date")
        if dl_response.status_code == 200:
            content = dl_response.json()
            content = content["reviews"][0]["original_review"]
            status_code = status.HTTP_200_OK
    except Exception as e:
        content = str(e)

    return jsonify({'last_five_star_review':content}), status_code


@app_api.route("/number_of_apps")
def number_of_apps():
    """
    Get all our apps available on all stores
    :return: json
    """
    content = None
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    try:
        dl_response = make_request("/products/mine")
        if dl_response.status_code == 200:
            content = {'number_of_apps': len(dl_response.json().items())}
            status_code = status.HTTP_200_OK
    except Exception as e:
        content = str(e)

    return jsonify(content), status_code


@app_api.route("/volume_call")
def get_volume_call():
    """
    Get volume http call per 30 minute.
    :return: json
    """
    content = None
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    datetime_last3_hours = datetime.now(tz=pytz.utc) - timedelta(hours=3)

    # Define data to post
    data = 'names[]=HttpDispatcher&from=%s&to=%s' % (datetime_last3_hours.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                                                     datetime.now(tz=pytz.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"))

    try:
        r = requests.get(config['url_newrelic'], headers=config['headers_newrelic'], params=data)

        if r.status_code == 200:
            content = r.json()
            status_code = status.HTTP_200_OK

    except Exception as e:
        content = str(e)

    return jsonify(content), status_code


@app_api.route("/volume_call_summarize")
def get_volume_call_summarize():
    """
    Get total http request from today 00:00:00.
    :return: json
    """
    content = None
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    datetime_24_hours_ago = datetime.now(tz=pytz.utc) - timedelta(hours=24)

    # Define data to post
    data = 'names[]=HttpDispatcher&from=%s&to=%s&summarize=true' % \
           (datetime_24_hours_ago.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            datetime.now(tz=pytz.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"))

    try:
        r = requests.get(config['url_newrelic'], headers=config['headers_newrelic'], params=data)

        if r.status_code == 200:
            content = r.json()
            status_code = status.HTTP_200_OK

    except Exception as e:
        content = str(e)

    return jsonify(content), status_code


@app_api.route("/volume_errors")
def get_volume_errors():
    """
    Get volume errors from today at 00:00:00.
    :return: json
    """
    content = None
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    datetime_24_hours_ago = datetime.now(tz=pytz.utc) - timedelta(hours=24)

    # Define data to post
    data = 'names[]=Errors/all&from=%s&summarize=true' % datetime_24_hours_ago.strftime("%Y-%m-%dT%H:%M:%S+00:00")

    try:
        r = requests.get(config['url_newrelic'], headers=config['headers_newrelic'], params=data)

        if r.status_code == 200:
            content = r.json()
            status_code = status.HTTP_200_OK

    except Exception as e:
        content = str(e)

    return jsonify(content), status_code


@app_api.route("/active_users")
def get_active_users():
    """
    Get current active users.
    :return: json
    """
    realtime_file = config['google_analytics_reporter_export_path'] + "/realtime.json"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    try:
        # Load json file
        jf = open(realtime_file)
        realtime = json.load(jf)

        # Set output
        content = {'name': 'current active users',
                   'value': (int(realtime['data'][0]['active_visitors']) * 5) + randint(1, 9)}

        status_code = status.HTTP_200_OK
    except Exception as e:
        content = str(e)

    return jsonify(content), status_code


@app_api.route("/downloads_by_store")
def get_downloads_by_store():
    """
    Get number of downloads of all our apps each day.
    :return: json
    """
    content = None
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    try:
        dl_response = make_request("/reports/sales/?group_by=store")
        if dl_response.status_code == 200:
            content = {'google_play': dl_response.json()['google_play']['downloads'],
                       'ios_store': dl_response.json()['apple:ios']['downloads']}

            status_code = status.HTTP_200_OK
    except Exception as e:
        content = str(e)

    return jsonify(content), status_code


@app_api.route("/total_regions")
def get_total_regions():
    """
    Get total regions.
    :return: json
    """
    url = config['url_navitia'] + "coverage/"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    total_regions = 0

    try:
        r = requests.get(url, headers=config['headers_navitia'])

        if r.status_code == 200:
            for id in [r['id'] for r in r.json()["regions"]]:

                r = requests.get("%s%s/networks" % (url, id), headers=config['headers_navitia'])

                if r.status_code == 200:
                    total_regions += r.json()["pagination"]["total_result"]

            status_code = status.HTTP_200_OK

        content = {'name': 'total regions', 'value': total_regions}
    except Exception as e:
        content = str(e)

    return jsonify(content), status_code


@app_api.route("/weekly_data_update")
def get_weekly_data_update():
    """
    Get weekly data update.
    :return: json
    """
    url = config['url_navitia'] + "status/"

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    update_count = 0

    last_week = datetime.now() - timedelta(days=7)

    try:
        r = requests.get(url, headers=config['headers_navitia'])

        if r.status_code == 200:
            for region in r.json()["regions"]:

                publication_date = datetime.strptime(region['publication_date'][0:15], '%Y%m%dT%H%M%S')
                update_count += (publication_date >= last_week)

            status_code = status.HTTP_200_OK

        content = {'name': 'weekly update data', 'value': update_count}
    except Exception as e:
        content = str(e)

    return jsonify(content), status_code


def app_logging(log_file, lvl=logging.INFO):
    """
    Write app log to file with specific format and log level
    :param log_file: File name where to write logs.
    :param lvl: Log level.
    """

    # Define format
    log_format = '[%(levelname)s] - %(asctime)s - %(message)s'
    log_date_format = '%m-%d-%Y %H:%M:%S'

    # Set logging method
    logging.basicConfig(format=log_format, level=lvl, datefmt=log_date_format, filename=log_file, filemode='a')


def make_request(uri, **querystring_params):
    headers = {"X-Client-Key": config['apikey_appfigures']}
    auth = (config['username_appfigures'], config['password_appfigures'])
    return requests.get(config['url_appfigures'] + uri.lstrip("/"),
                        auth=auth,
                        params=querystring_params,
                        headers=headers)


if __name__ == "__main__":
    # Load configuration file
    try:
        f = open(CONFIGURATION_FILE, 'r')
        config = yaml.load(f)
    except Exception as e:
        raise KisioWallApiConfigLoad(str(e))

    # Enable logs
    app_logging(config['log_file'])

    # Set connection to Redis cache db
    """pool = redis.ConnectionPool(host=config['host_relis'], port=config['port_relis'], db=0)
    last_cache_update = datetime.now()"""

    # Create access log for api call
    app_api.run(port=config['port'])
