from flask import request
from flask_restful import Resource, fields, marshal_with, abort
from bson.son import SON
from .extentions import mongo, api


ACTIVITY_FIELDS = {
    'name': fields.String,
    'date': fields.String,
    'start_time' : fields.String,
    'stop_time' : fields.String,
    'total': fields.Integer
}


def get_specyfic_time(total_time):
    return {
        'days': total_time // 86400,
        'hours': (total_time % 86400) // 3600,
        'minutes': (total_time % 3600) // 60,
        'seconds': total_time % 60
    }


def abort_if_no_data(data):
    if not data:
        abort(404, message="Not Found Any Data")


class DailyRawData(Resource):
    @marshal_with(ACTIVITY_FIELDS)
    def get(self, date):      
        actvitity_collection = mongo.db.time_entry 
        data = list(actvitity_collection.find({'date': date}))
        abort_if_no_data(data)

        return data


class DailySummary(Resource):
    def get(self, date):
        limit = int(request.args.get('limit'))      
        actvitity_collection = mongo.db.time_entry 

        pipeline = [
            {"$match": {"date" : date}},
            {"$group": {
                "_id": "$name", 
                "totalTime": {"$sum": "$total"}, 
                "maxEntry": {"$max": "$total"},
                "count": {"$sum": 1}
            }},
            {"$sort": SON([("totalTime", -1)])},
            {"$limit": limit}
        ]

        data = list(actvitity_collection.aggregate(pipeline))

        total_sum = sum(activity["totalTime"] for activity in data)
        for activity in data:
            activity['%time'] = round(activity["totalTime"] / total_sum * 100, 2)

        return data


class DailyActivityEntries(Resource):
    @marshal_with(ACTIVITY_FIELDS)
    def get(self, name, date):
        limit = int(request.args.get('limit'))
        actvitity_collection = mongo.db.time_entry 

        pipeline = [
            {"$match": {"date": date, "name": name}},
            {"$project" : { "total" : 1, "start_time" : 1, "stop_time" : 1 }},
            {"$sort": SON([("total", -1)])},
            {"$limit": limit},
            {"$sort": SON([("start_time", 1)])}
        ]
        
        data = list(actvitity_collection.aggregate(pipeline))

        return data


class TotalTimeSummary(Resource):
    def get(self, from_date, to_date):
        limit = int(request.args.get('limit'))
        actvitity_collection = mongo.db.time_entry
        pipeline = [
            {"$match": {
                "date": {"$gte": from_date,"$lte": to_date}
                }
            },
            {"$group": {
                "_id": "$date",
                "totalTime": {"$sum": "$total"},
            }},
            {"$sort": SON([("totalTime", -1)])},
            {"$limit": limit},
            {"$sort": SON([("_id", 1)])}
        ]

        data = list(actvitity_collection.aggregate(pipeline))

        return data


class ActivitySummary(Resource):
    def get(self, name):      
        limit = int(request.args.get('limit'))
        actvitity_collection = mongo.db.time_entry
        query_filter = self._get_filter(name)

        pipeline = [
            {"$match": query_filter
            },
            {"$group": {
                "_id": "$date",
                "totalTime": {"$sum": "$total"}, 
                "maxEntry": {"$max": "$total"},
                "count": {"$sum": 1}
            }},
            {"$sort": SON([("totalTime", -1)])},
            {"$limit": limit},
            {"$sort": SON([("_id", 1)])}
        ]

        data = list(actvitity_collection.aggregate(pipeline))

        return data

    def _get_filter(self, name):
        query_filter = {'name' : name, 'date': {}}

        if from_date := request.args.get('from'):
            query_filter['date']["$gte"] = from_date

        if to_date := request.args.get('to'):
            query_filter['date']["$lte"] = to_date

        if not query_filter['date']:
            del query_filter['date']

        return query_filter
        
api.add_resource(DailyRawData, '/daily-raw-data/<date>/')
api.add_resource(DailySummary, '/daily-summary/<date>/')
api.add_resource(ActivitySummary, '/activity-summary/<name>/')
api.add_resource(TotalTimeSummary, '/total-time/<from_date>/<to_date>/')
api.add_resource(DailyActivityEntries, '/activity/<name>/<date>/')