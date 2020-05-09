
import datetime
#from datetime import datetime
import json

from flask import Blueprint, request

import db
from utils import check_missing_keys

blueprint = Blueprint('api', __name__, url_prefix='/api')

# An endpoint to list all the events
# TODO: Restrict access based on user and project.
@blueprint.route('/list-all', methods=["GET"])
def list_all_events():
    db_conn = db.get_database_connection()
    with db_conn.cursor() as cursor:
        sql = 'SELECT * FROM `web_event`'
        cursor.execute(sql)
        result = cursor.fetchall()
        return {"events": result}
    return {}


def get_events(project_id:str, event_type:str = None, start_time:datetime.datetime = None, \
                end_time:datetime.datetime = None):
    '''
    Fetches the events that match the given parameters from the database.

    Returns:
        A list of events records or empty list if no records match the given criteria.
    '''

    db_conn = db.get_database_connection()
    with db_conn.cursor() as cursor:
        params_to_sql = []
        sql = 'SELECT * FROM `web_event` WHERE project_id=%s'
        params_to_sql.append(project_id)
        if event_type:
            sql += ' AND event_type=%s'
            params_to_sql.append(event_type)

        if start_time:
            sql += ' AND time_entered >= DATE(%s)'
            params_to_sql.append(start_time.isoformat())

        if end_time:
            sql += ' AND time_entered <= DATE(%s)'
            params_to_sql.append(end_time)
        cursor.execute(sql, params_to_sql)
        result = cursor.fetchall()
        return result


# TODO: Restrict access to require some kind of authorization

@blueprint.route('/v1/list-events/<string:project>/', methods=["GET"])
def list_events(project):
    """
    This endpoint gets the events associated with the given `project`.
    It also can be used to filter events with some parameters.
    If no parameter is given, it returns all the events

    parameters:
    	event_type: The events that have this particular type will only be returned
	    start_time: timestamp
                    Events that were logged after this time will be returned
	    end_time:  timestamp
                    The events returned would have been logged before this time
    """

    response = {"success": False}
    params = {}

    if "event_type" in request.args:
        params["event_type"] = request.args["event_type"]
    try:
        if "start_time" in request.args:
                timestamp = float(request.args["start_time"])
                params["start_time"] = datetime.datetime.utcfromtimestamp(timestamp)

        if "end_time" in request.args:
                timestamp = float(request.args["end_time"])
                params["end_time"] = datetime.datetime.utcfromtimestamp(timestamp).isoformat()
    except:
        response["error"] = "Invalid time parameter"
        return response, 400

    result = get_events(project, **params)
    response["events"] = result
    response["success"] = True
    return response

    

@blueprint.route('/v1/get-metrics/<string:project>/', methods=['GET'])
def get_metrics(project):

    """
    This endpoint gets the following metrics with the given `project`.
    metrics : 
        {
            total_visitors: count of total no of distinct users visited the project will be returned
            pageviews: count of total no of pageview events occured will be returned
            total_events: count of total no of events occured will be returned
            category_wise: events occured and the count of events occured will be returned
        }

    Parameters is passed to get the metrics
    If no parameters is passed then a error is thrown
    
    parameters:
        start_time: timestamp
                    Metrics of events logged after this time will only be taken into account
        end_time: timestamp
                  Metrics of events logged after this time wiil only be taken into account 

    """

    response ={}
    start_time = None
    end_time = None

    # Keys that must be present in a request to get metrics
    REQUIRED_PARAMETERS = {"start_time","end_time"}
    
    response = {"success": False}
    request_body = request.args.to_dict()

    missing = check_missing_keys(request_body, REQUIRED_PARAMETERS)
    if missing:
        response["error"] = "Malformed request - missing parameters - " + str(missing)
        return response, 400    

    try:
        if "start_time" in request.args:
            timestamp = float(request.args["start_time"])
            start_time = datetime.datetime.utcfromtimestamp(timestamp)

        if "end_time" in request.args:
            timestamp = float(request.args["end_time"])
            end_time = datetime.datetime.utcfromtimestamp(timestamp)
    except:
        response["error"] = "Invalid time parameter"
        return response, 400
            
    start_time = datetime.datetime.strptime(start_time.strftime('%Y-%m-%d'),'%Y-%m-%d')

    end_time = datetime.datetime.strptime(end_time.strftime('%Y-%m-%d'),'%Y-%m-%d')
    
    # This has the dates from given start time to endtime, including the 
    # start date and end date
    dates_array = (start_time + datetime.timedelta(days=x) for x in range(0, 
                                                    (end_time-start_time).days+1))

    for current_date in dates_array:
        current_date = current_date.strftime('%Y-%m-%d')
        db_conn = db.get_database_connection()
        with db_conn.cursor() as cursor:

            result = {}
            params_to_sql = []
            sql =  'SELECT COUNT(DISTINCT(origin_id)) AS total_visitors FROM `web_event` WHERE project_id=%s \
                        AND DATE(time_entered)=DATE(%s)'
            params_to_sql.append(project)
            params_to_sql.append(current_date)

            cursor.execute(sql, params_to_sql)
            records = cursor.fetchone()
            result['total_visitors'] = records['total_visitors']

            params_to_sql.clear()
            sql = 'SELECT COUNT(*) AS pageviews FROM `web_event` WHERE project_id=%s AND event_type=%s \
                        AND DATE(time_entered)=DATE(%s)'
            params_to_sql.append(project)
            params_to_sql.append('pageview')
            params_to_sql.append(current_date)

            cursor.execute(sql, params_to_sql)
            records = cursor.fetchone()
            result['pageviews'] = records['pageviews']

            params_to_sql.clear()
            sql = 'SELECT COUNT(*) AS total_events FROM `web_event` WHERE project_id=%s AND DATE(time_entered)=DATE(%s)'
            params_to_sql.append(project)
            params_to_sql.append(current_date)

            cursor.execute(sql, params_to_sql)
            records = cursor.fetchone()
            result['total_events'] = records['total_events']

            params_to_sql.clear()
            sql = 'SELECT event_type, COUNT(*) FROM `web_event` WHERE project_id=%s \
                        AND DATE(time_entered)=DATE(%s) GROUP BY event_type'
            params_to_sql.append(project)
            params_to_sql.append(current_date)

            cursor.execute(sql, params_to_sql)            
            records = cursor.fetchall()
            category_wise = {}
            for row in records:
                if row is not None:
                    category_wise[row['event_type']] = row['COUNT(*)']

            result['category_wise'] = category_wise

            response[current_date] = result
    response["success"] = True
    return response



# This function adds CORS headers to all the responses from this blueprint
# CORS headers are required as the requests to this server will be made from other
# sites.
@blueprint.after_request
def add_cors_header(response):
    headers = response.headers
    if 'Access-Control-Allow-Origin' not in response.headers:
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Content-Length'
    return response


@blueprint.route('/v1/register-new', methods=["POST"])
def register_new_event():
    """
    This endpoint registers a new event for a project.
    This endpoint should typically be called from an external site (i.e site of an user)
    to log a new event onto our database.

    parameters:
    	page_url:   The current URL of the from which the event is to be registered
	    event_type: A specific tag for that particular event.
	    custom_params: (Optional) Any other data that the client developer wants to send along.
                        (Should be valid JSON)
		api_key: The API key of the project for which the event is to be logged
		origin_id: A unique tag identifying the end-user of the client-website.
    """

    # The keys that should be present a request that comes in to register a new event
    REGISTER_NEW_EVENT_KEYS = {"page_url", "event_type", "api_key", "origin_id"}

    response = {"success": False}
    if not request.is_json:
        # Requests should be of type application/json
        return response, 400

    request_body = request.get_json()
    missing = check_missing_keys(request_body, REGISTER_NEW_EVENT_KEYS)
    if missing:
        response["error"] = "Malformed request - missing parameters - " + str(missing)
        return response, 400

    user_agent = request.headers.get('User-Agent', None)
    api_key = request_body["api_key"]
    get_project_from_api_key_sql  = 'SELECT `project_id` FROM `project` WHERE `api_key`=%s'
    project_id = None

    custom_data = request_body.get('custom_params', None)
    custom_data = json.dumps(custom_data)

    db_connection = db.get_database_connection()
    with db_connection.cursor() as cursor:
        cursor.execute(get_project_from_api_key_sql, (api_key,))
        result = cursor.fetchone()
        if not result:
            response["error"] = "Invalid API key"
            return response, 404

        project_id = result.get("project_id", None)

        insert_new_event_sql = "INSERT INTO `web_event` ( `project_id`, `origin_id`,`user_agent`, \
                                `page_url`, `event_type`, `custom_data`) VALUES \
                                (%s, %s, %s, %s, %s, %s)"

        cursor.execute(insert_new_event_sql, (project_id, request_body["origin_id"],
                                                user_agent, request_body["page_url"], request_body["event_type"],
                                                custom_data))
        db_connection.commit()

        response["success"] = True
    return response

