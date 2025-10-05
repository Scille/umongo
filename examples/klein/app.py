import datetime as dt
import json

from bson import ObjectId
from txmongo import MongoConnection

from klein import Klein
from klein_babel import gettext, locale_from_request
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, returnValue

from umongo import Document, RemoveMissingSchema, ValidationError, fields, set_gettext
from umongo.frameworks import PyMongoInstance

app = Klein()
db = MongoConnection().demo_umongo
instance = PyMongoInstance(db)
set_gettext(gettext)


class MongoJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (dt.datetime, dt.date)):
            return obj.isoformat()
        if isinstance(obj, ObjectId):
            return str(obj)
        return json.JSONEncoder.default(self, obj)


def jsonify(request, *args, **kwargs):
    """Jsonify with support for MongoDB ObjectId"""
    request.setHeader("Content-Type", "application/json")
    return json.dumps(dict(*args, **kwargs), cls=MongoJsonEncoder, indent=True)


def get_json(request):
    return json.loads(request.content.read().decode())


@instance.register
class User(Document):
    # We specify `RemoveMissingSchema` as a base marshmallow schema so that
    # auto-generated marshmallow schemas skip missing fields instead of returning None
    MA_BASE_SCHEMA_CLS = RemoveMissingSchema

    nick = fields.StrField(required=True, unique=True)
    firstname = fields.StrField()
    lastname = fields.StrField()
    birthday = fields.AwareDateTimeField()
    password = fields.StrField()  # Don't store it in clear in real life !


@inlineCallbacks
def populate_db():
    yield User.collection.drop()
    yield User.ensure_indexes()
    for data in [
        {
            "nick": "mze",
            "lastname": "Mao",
            "firstname": "Zedong",
            "birthday": dt.datetime(1893, 12, 26),
            "password": "Serve the people",
        },
        {
            "nick": "lsh",
            "lastname": "Liu",
            "firstname": "Shaoqi",
            "birthday": dt.datetime(1898, 11, 24),
            "password": "Dare to think, dare to act",
        },
        {
            "nick": "lxia",
            "lastname": "Li",
            "firstname": "Xiannian",
            "birthday": dt.datetime(1909, 6, 23),
            "password": "To rebel is justified",
        },
        {
            "nick": "ysh",
            "lastname": "Yang",
            "firstname": "Shangkun",
            "birthday": dt.datetime(1907, 7, 5),
            "password": "Smash the gang of four",
        },
        {
            "nick": "jze",
            "lastname": "Jiang",
            "firstname": "Zemin",
            "birthday": dt.datetime(1926, 8, 17),
            "password": "Seek truth from facts",
        },
        {
            "nick": "huji",
            "lastname": "Hu",
            "firstname": "Jintao",
            "birthday": dt.datetime(1942, 12, 21),
            "password": "It is good to have just 1 child",
        },
        {
            "nick": "xiji",
            "lastname": "Xi",
            "firstname": "Jinping",
            "birthday": dt.datetime(1953, 6, 15),
            "password": "Achieve the 4 modernisations",
        },
    ]:
        yield User(**data).commit()


# Define a custom marshmallow schema to ignore read-only fields
class UserUpdateSchema(User.schema.as_marshmallow_schema()):
    class Meta:
        dump_only = ("nick", "password")


user_update_schema = UserUpdateSchema()


# Define a custom marshmallow schema from User document to exclude password field
class UserNoPassSchema(User.schema.as_marshmallow_schema()):
    class Meta:
        exclude = ("password",)


user_no_pass_schema = UserNoPassSchema()


def dump_user_no_pass(u):
    return user_no_pass_schema.dump(u)


# Define a custom marshmallow schema from User document to expose only password field
class ChangePasswordSchema(User.schema.as_marshmallow_schema()):
    class Meta:
        fields = ("password",)
        required = ("password",)


change_password_schema = ChangePasswordSchema()


@app.route("/", methods=["GET"])
def root(request):
    return """<h1>Umongo flask example</h1>
<br>
<h3>routes:</h3><br>
<ul>
  <li><a href="/users">GET /users</a></li>
  <li>POST /users</li>
  <li>GET /users/&lt;nick_or_id&gt;</li>
  <li>PATCH /users/&lt;nick_or_id&gt;</li>
  <li>PUT /users/&lt;nick_or_id&gt;/password</li>
</ul>
"""


def _to_objid(data):
    try:
        return ObjectId(data)
    except Exception:
        return None


def _nick_or_id_lookup(nick_or_id):
    return {"$or": [{"nick": nick_or_id}, {"_id": _to_objid(nick_or_id)}]}


class Error(Exception):
    pass


@app.handle_errors(Error)
def error(request, failure):
    code, data = failure.value.args
    request.setResponseCode(code)
    return data


@app.route("/users/<nick_or_id>", methods=["GET"])
@locale_from_request
@inlineCallbacks
def get_user(request, nick_or_id):
    user = yield User.find_one(_nick_or_id_lookup(nick_or_id))
    if not user:
        raise Error(404, "Not found")
    returnValue(jsonify(request, dump_user_no_pass(user)))


@app.route("/users/<nick_or_id>", methods=["PATCH"])
@locale_from_request
@inlineCallbacks
def update_user(request, nick_or_id):
    payload = get_json(request)
    if payload is None:
        raise Error(
            400,
            "Request body must be json with Content-type: application/json",
        )
    user = yield User.find_one(_nick_or_id_lookup(nick_or_id))
    if not user:
        raise Error(404, "Not found")
    try:
        data = user_update_schema.load(payload)
        user.update(data)
        yield user.commit()
    except ValidationError as ve:
        raise Error(400, jsonify(request, message=ve.args[0])) from ve
    returnValue(jsonify(request, dump_user_no_pass(user)))


@app.route("/users/<nick_or_id>", methods=["DELETE"])
@locale_from_request
@inlineCallbacks
def delete_user(request, nick_or_id):
    user = yield User.find_one(_nick_or_id_lookup(nick_or_id))
    if not user:
        raise Error(404, "Not Found")
    try:
        yield user.delete()
    except ValidationError as ve:
        raise Error(400, jsonify(message=ve.args[0])) from ve
    returnValue("Ok")


@app.route("/users/<nick_or_id>/password", methods=["PUT"])
@locale_from_request
@inlineCallbacks
def change_password_user(request, nick_or_id):
    payload = get_json(request)
    if payload is None:
        raise Error(
            400,
            "Request body must be json with Content-type: application/json",
        )
    user = yield User.find_one(_nick_or_id_lookup(nick_or_id))
    if not user:
        raise Error(404, "Not found")

    try:
        data = change_password_schema.load(payload)
        user.password = data["password"]
        yield user.commit()
    except ValidationError as ve:
        raise Error(400, jsonify(request, message=ve.args[0])) from ve
    returnValue(jsonify(request, dump_user_no_pass(user)))


@app.route("/users", methods=["GET"])
@locale_from_request
@inlineCallbacks
def list_users(request):
    page = int(request.args.get("page", 1))
    users = yield User.find(limit=10, skip=(page - 1) * 10)
    returnValue(
        jsonify(
            request,
            {
                "_total": (yield User.count()),
                "_page": page,
                "_per_page": 10,
                "_items": [dump_user_no_pass(u) for u in users],
            },
        ),
    )


@app.route("/users", methods=["POST"])
@locale_from_request
@inlineCallbacks
def create_user(request):
    payload = get_json(request)
    if payload is None:
        raise Error(
            400,
            "Request body must be json with Content-type: application/json",
        )
    try:
        user = User(**payload)
        yield user.commit()
    except ValidationError as ve:
        raise Error(400, jsonify(request, message=ve.args[0])) from ve
    returnValue(jsonify(request, dump_user_no_pass(user)))


if __name__ == "__main__":
    reactor.callWhenRunning(populate_db)
    app.run("localhost", 5000)
