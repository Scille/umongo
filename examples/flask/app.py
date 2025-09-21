import datetime as dt

from bson import ObjectId
from pymongo import MongoClient

from flask import Flask, abort, jsonify, request
from flask_babel import Babel, gettext

from umongo import Document, RemoveMissingSchema, ValidationError, fields, set_gettext
from umongo.frameworks import PyMongoInstance

app = Flask(__name__)
db = MongoClient().demo_umongo
instance = PyMongoInstance(db)
babel = Babel(app)
set_gettext(gettext)


# available languages
LANGUAGES = {
    "en": "English",
    "fr": "Français",
}


@babel.localeselector
def get_locale():
    return request.accept_languages.best_match(LANGUAGES.keys())


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

    class Meta:
        collection_name = "user"


def populate_db():
    User.collection.drop()
    User.ensure_indexes()
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
        User(**data).commit()


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
def root():
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


@app.route("/users/<nick_or_id>", methods=["GET"])
def get_user(nick_or_id):
    user = User.find_one(_nick_or_id_lookup(nick_or_id))
    if not user:
        abort(404)
    return jsonify(dump_user_no_pass(user))


@app.route("/users/<nick_or_id>", methods=["PATCH"])
def update_user(nick_or_id):
    payload = request.get_json()
    if payload is None:
        abort(400, "Request body must be json with Content-type: application/json")
    user = User.find_one(_nick_or_id_lookup(nick_or_id))
    if not user:
        abort(404)
    try:
        data = user_update_schema.load(payload)
        user.update(data)
        user.commit()
    except ValidationError as ve:
        resp = jsonify(message=ve.args[0])
        resp.status_code = 400
        return resp
    return jsonify(dump_user_no_pass(user))


@app.route("/users/<nick_or_id>", methods=["DELETE"])
def delete_user(nick_or_id):
    user = User.find_one(_nick_or_id_lookup(nick_or_id))
    if not user:
        abort(404)
    try:
        user.delete()
    except ValidationError as ve:
        resp = jsonify(message=ve.args[0])
        resp.status_code = 400
        return resp
    return "Ok"


@app.route("/users/<nick_or_id>/password", methods=["PUT"])
def change_user_password(nick_or_id):
    payload = request.get_json()
    if payload is None:
        abort(400, "Request body must be json with Content-type: application/json")
    user = User.find_one(_nick_or_id_lookup(nick_or_id))
    if not user:
        abort(404)
    try:
        data = change_password_schema.load(payload)
        user.password = data["password"]
        user.commit()
    except ValidationError as ve:
        resp = jsonify(message=ve.args[0])
        resp.status_code = 400
        return resp
    return jsonify(dump_user_no_pass(user))


@app.route("/users", methods=["GET"])
def list_users():
    page = int(request.args.get("page", 1))
    users = User.find().limit(10).skip((page - 1) * 10)
    return jsonify(
        {
            "_total": users.count(),
            "_page": page,
            "_per_page": 10,
            "_items": [dump_user_no_pass(u) for u in users],
        },
    )


@app.route("/users", methods=["POST"])
def create_user():
    payload = request.get_json()
    if payload is None:
        abort(400, "Request body must be json with Content-type: application/json")
    try:
        user = User(**payload)
        user.commit()
    except ValidationError as ve:
        resp = jsonify(message=ve.args[0])
        resp.status_code = 400
        return resp
    return jsonify(dump_user_no_pass(user))


if __name__ == "__main__":
    populate_db()
    app.run(debug=True)
