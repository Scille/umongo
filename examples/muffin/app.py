import json
import datetime
import muffin
from bson import ObjectId
from aiohttp.web import json_response
from motor.motor_asyncio import AsyncIOMotorClient
from functools import partial

from umongo import Instance, Document, fields, ValidationError, set_gettext
from umongo.marshmallow_bonus import SchemaFromUmongo

import logging
logging.basicConfig(level=logging.DEBUG)


app = muffin.Application(__name__,
    PLUGINS=(
        'muffin_babel',
    ),
    BABEL_LOCALES_DIRS=['translations']
)
db = AsyncIOMotorClient()['demo_umongo']
instance = Instance(db)


set_gettext(app.ps.babel.gettext)


@app.ps.babel.locale_selector
def set_locale(request):
    """Get locale based on request Accept-Language header"""
    return app.ps.babel.select_locale_by_request(request)


class MongoJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        elif isinstance(obj, ObjectId):
            return str(obj)
        return json.JSONEncoder.default(self, obj)


def jsonify(request, *args, **kwargs):
    """
    jsonify with support for MongoDB ObjectId
    """
    dumps = partial(json.dumps, cls=MongoJsonEncoder, indent=True)
    return json_response(dict(*args, **kwargs), dumps=dumps)


@instance.register
class User(Document):
    nick = fields.StrField(required=True, unique=True)
    firstname = fields.StrField()
    lastname = fields.StrField()
    birthday = fields.DateTimeField()
    password = fields.StrField()  # Don't store it in clear in real life !


async def populate_db():
    await User.collection.drop()
    await User.ensure_indexes()
    for data in [
        {
            'nick': 'mze', 'lastname': 'Mao', 'firstname': 'Zedong',
            'birthday': datetime.datetime(1893, 12, 26),
            'password': 'Serve the people'
        },
        {
            'nick': 'lsh', 'lastname': 'Liu', 'firstname': 'Shaoqi',
            'birthday': datetime.datetime(1898, 11, 24),
            'password': 'Dare to think, dare to act'
        },
        {
            'nick': 'lxia', 'lastname': 'Li', 'firstname': 'Xiannian',
            'birthday': datetime.datetime(1909, 6, 23),
            'password': 'To rebel is justified'
        },
        {
            'nick': 'ysh', 'lastname': 'Yang', 'firstname': 'Shangkun',
            'birthday': datetime.datetime(1907, 7, 5),
            'password': 'Smash the gang of four'
        },
        {
            'nick': 'jze', 'lastname': 'Jiang', 'firstname': 'Zemin',
            'birthday': datetime.datetime(1926, 8, 17),
            'password': 'Seek truth from facts'
        },
        {
            'nick': 'huji', 'lastname': 'Hu', 'firstname': 'Jintao',
            'birthday': datetime.datetime(1942, 12, 21),
            'password': 'It is good to have just 1 child'
        },
        {
            'nick': 'xiji', 'lastname': 'Xi', 'firstname': 'Jinping',
            'birthday': datetime.datetime(1953, 6, 15),
            'password': 'Achieve the 4 modernisations'
        }
    ]:
        await User(**data).commit()


# Create a custom marshmallow schema from User document in order to avoid some fields
class UserNoPassSchema(User.schema.as_marshmallow_schema()):
    class Meta:
        read_only = ('password',)
        load_only = ('password',)
no_pass_schema = UserNoPassSchema()

def dump_user_no_pass(u):
    return no_pass_schema.dump(u)


@app.register('/', methods=['GET'])
async def root(request):
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
    return {'$or': [{'nick': nick_or_id}, {'_id': _to_objid(nick_or_id)}]}


def build_error(status=400, msg=None):
    if status == 404 and not msg:
        msg = 'Not found'
    return json_response({'message': msg}, status=status)


@app.register('/users/{nick_or_id}', methods=['GET'])
async def get_user(request):
    nick_or_id = request.match_info['nick_or_id']
    user = await User.find_one(_nick_or_id_lookup(nick_or_id))
    if not user:
        return build_error(404)
    return jsonify(request, dump_user_no_pass(user))


@app.register('/users/{nick_or_id}', methods=['PATCH'])
async def update_user(request):
    nick_or_id = request.match_info['nick_or_id']
    payload = await request.json()
    if payload is None:
        return build_error(400, 'Request body must be json with Content-type: application/json')
    user = await User.find_one(_nick_or_id_lookup(nick_or_id))
    if not user:
        return build_error(404)
    # Define a custom schema from the default one to ignore read-only fields
    UserUpdateSchema = User.Schema.as_marshmallow_schema(params={
        'password': {'dump_only': True},
        'nick': {'dump_only': True}
    })()
    # with `strict`, marshmallow raise ValidationError if something is wrong
    schema = UserUpdateSchema(strict=True)
    try:
        data, _ = schema.load(payload)
        user.update(data)
        await user.commit()
    except ValidationError as ve:
        return build_error(400, ve.args[0])
    return jsonify(request, dump_user_no_pass(user))


@app.register('/users/{nick_or_id}', methods=['DELETE'])
async def delete_user(request):
    nick_or_id = request.match_info['nick_or_id']
    user = await User.find_one(_nick_or_id_lookup(nick_or_id))
    if not user:
        return build_error(404)
    try:
        await user.remove()
    except ValidationError as ve:
        return build_error(400, ve.args[0])
    return 'Ok'


@app.register('/users/{nick_or_id}/password', methods=['PUT'])
async def change_password_user(request):
    nick_or_id = request.match_info['nick_or_id']
    payload = await request.json()
    if payload is None:
        return build_error(400, 'Request body must be json with Content-type: application/json')
    user = await User.find_one(_nick_or_id_lookup(nick_or_id))
    if not user:
        return build_error(404, 'Not found')

    # Use a field from our document to create a marshmallow schema
    # Note that we use `SchemaFromUmongo` to get unknown fields check on
    # deserialization and skip missing fields instead of returning None
    class ChangePasswordSchema(SchemaFromUmongo):
        password = User.schema.fields['password'].as_marshmallow_field(params={'required': True})
    # with `strict`, marshmallow raises a ValidationError if something is wrong
    schema = ChangePasswordSchema(strict=True)
    try:
        data, _ = schema.load(payload)
        user.password = data['password']
        await user.commit()
    except ValidationError as ve:
        return build_error(400, ve.args[0])
    return jsonify(request, dump_user_no_pass(user))


@app.register('/users', methods=['GET'])
async def list_users(request):
    page = int(request.GET.get('page', 1))
    per_page = 10
    cursor = User.find(limit=per_page, skip=(page - 1) * per_page)
    return jsonify(request, {
        '_total': (await cursor.count()),
        '_page': page,
        '_per_page': per_page,
        '_items': [dump_user_no_pass(u) for u in (await cursor.to_list(per_page))]
    })


@app.register('/users', methods=['POST'])
async def create_user(request):
    payload = await request.json()
    if payload is None:
        return build_error(400, 'Request body must be json with Content-type: application/json')
    try:
        user = User(**payload)
        await user.commit()
    except ValidationError as ve:
        return build_error(400, ve.args[0])
    return jsonify(request, dump_user_no_pass(user))


if __name__ == '__main__':
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(populate_db())
    # Needed to bootstrap plugins
    loop.run_until_complete(app.start())

    from aiohttp import web
    web.run_app(app, port=5000)
