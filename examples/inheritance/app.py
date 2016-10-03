from bson import ObjectId
from pymongo import MongoClient

from umongo import Instance, Document, fields, ValidationError, validate


db = MongoClient().demo_umongo
instance = Instance(db)


@instance.register
class Vehicle(Document):
    model = fields.StrField(required=True)

    class Meta:
        collection = db.vehicle
        allow_inheritance = True


@instance.register
class Car(Vehicle):
    doors = fields.IntField(validate=validate.OneOf([3, 5]))


@instance.register
class MotorBike(Vehicle):
    engine_type = fields.StrField(validate=validate.OneOf(['2-stroke', '4-stroke']))


def populate_db():
    Vehicle.collection.drop()
    Vehicle.ensure_indexes()
    for data in [
        {'model': 'Chevrolet Impala 1966', 'doors': 5},
        {'model': 'Ford Grand Torino', 'doors': 3},
    ]:
        Car(**data).commit()
    for data in [
        {'model': 'Honda CB125', 'engine_type': '2-stroke'}
    ]:
        MotorBike(**data).commit()


class Repl(object):

    USAGE = """help: print this message
new: create a vehicle
ls: list vehicles
get <id>: retrieve a vehicle from it id
quit: leave the console"""

    def get_vehicle(self, *args):
        if len(args) != 1:
            print("Error: need only vehicle's id")
        id = args[0]
        vehicle = None
        try:
            vehicle = Vehicle.find_one({'_id': ObjectId(id)})
        except Exception as exc:
            print('Error: %s' % exc)
            return
        if vehicle:
            print(vehicle)
        else:
            print('Error: unknown vehicle `%s`' % id)

    def list_vehicles(self):
        print('Found %s vehicles' % Vehicle.find().count())
        print('\n'.join([str(v) for v in Vehicle.find()]))

    def new_vehicle(self):
        vehicle_type = input('Type ? car/bike ') or 'car'
        data = {
            'model': input('Model ? ') or 'unknown'
        }
        if vehicle_type == 'car':
            try:
                data['doors'] = int(input('# of doors ? 3/5 '))
            except ValueError:
                pass
            vehicle = Car(**data)
        else:
            strokes = input('Type of stroke-engine ? 2/4 ')
            if strokes:
                data['engine_type'] = '2-stroke' if strokes == '2' else '4-stroke'
            vehicle = MotorBike(**data)
        try:
            vehicle.commit()
        except ValidationError as exc:
            print('Error: %s' % exc)
        else:
            print('Created %s' % vehicle)

    def start(self):
        quit = False
        print("Welcome to the garage, type `help` if you're lost")
        while not quit:
            cmd = input('> ')
            cmd = cmd.strip()
            if cmd == 'help':
                print(self.USAGE)
            elif cmd.startswith("ls"):
                self.list_vehicles()
            elif cmd.startswith("new"):
                self.new_vehicle()
            elif cmd.startswith("get"):
                self.get_vehicle(*cmd.split()[1:])
            elif cmd == 'quit':
                quit = True
            else:
                print('Error: Unknow command !')


if __name__ == '__main__':
    populate_db()
    Repl().start()
