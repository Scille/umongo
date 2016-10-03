#! /usr/bin/env python

import requests


class Tester:

    def __init__(self, test_name):
        self.name = test_name

    def __enter__(self):
        print('%s...' % self.name, flush=True, end='')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            print(' Error !')
        else:
            print(' OK')


def test_list(total):
    r = requests.get('http://localhost:5000/users')
    assert r.status_code == 200, r.status_code
    data = r.json()
    assert data['_total'] == total, 'expected %s, got %s' % (total, data['_total'])
    assert len(data['_items']) == total, 'expected %s, got %s' % (total, len(data['_items']))
    return data


with Tester('List all'):
    data = test_list(7)

with Tester('Get one by id'):
    user = data['_items'][0]
    r = requests.get('http://localhost:5000/users/%s' % user['id'])
    assert r.status_code == 200, r.status_code
    data = r.json()
    assert user == data, 'user: %s, data: %s' % (user, data)

with Tester('Get one by nick'):
    r = requests.get('http://localhost:5000/users/%s' % user['nick'])
    assert r.status_code == 200, r.status_code
    assert data == r.json(), 'data: %s, nick_data: %s' % (data, r.json())

with Tester('404 on one'):
    r = requests.get('http://localhost:5000/users/572c59bf13abf21bf84890a0')
    assert r.status_code == 404, r.status_code

with Tester('Create one'):
    payload = {
        'nick': 'n00b',
        'birthday': '2016-05-18T11:40:32+00:00',
        'password': '123456'
    }
    r = requests.post('http://localhost:5000/users', json=payload)
    assert r.status_code == 200, r.status_code
    data = r.json()
    new_user_id = data.pop('id')
    expected = {
        'nick': 'n00b',
        'birthday': '2016-05-18T11:40:32+00:00',
    }
    assert data == expected, 'data: %s, expected: %s' % (data, expected)
    test_list(8)

with Tester('Change password'):
    r = requests.put('http://localhost:5000/users/%s/password' % new_user_id,
                     json={'password': 'abcdef'})
    assert r.status_code == 200, r.status_code
    data = r.json()
    assert new_user_id == data.pop('id')
    assert data == expected, 'data: %s, expected: %s' % (data, expected)

with Tester('Bad change password'):
    r = requests.put('http://localhost:5000/users/%s/password' % new_user_id,
                     json={'password': 'abcdef', 'dummy': 42})
    assert r.status_code == 400, r.status_code
    data = r.json()
    expected = {'message': {'_schema': ['Unknown field name dummy.']}}
    assert data == expected, 'data: %s, expected: %s' % (data, expected)

with Tester('404 on change password'):
    r = requests.put('http://localhost:5000/users/572c59bf13abf21bf84890a0/password',
                     json={'password': 'abcdef'})
    assert r.status_code == 404, r.status_code

with Tester('Delete one'):
    r = requests.delete('http://localhost:5000/users/%s' % new_user_id)
    assert r.status_code == 200, r.status_code
    test_list(7)

with Tester('404 on delete one'):
    r = requests.delete('http://localhost:5000/users/572c59bf13abf21bf84890a0')
    assert r.status_code == 404, r.status_code

with Tester('Create one missing field'):
    r = requests.post('http://localhost:5000/users', json={})
    assert r.status_code == 400, r.status_code
    data = r.json()
    expected = {'message': {'nick': ['Missing data for required field.']}}
    assert data == expected, 'data: %s, expected: %s' % (data, expected)

with Tester('Create one i18n'):
    headers = {'Accept-Language': 'fr, en-gb;q=0.8, en;q=0.7'}
    r = requests.post('http://localhost:5000/users', headers=headers, json={})
    assert r.status_code == 400, r.status_code
    data = r.json()
    expected = {'message': {'nick': ['Valeur manquante pour un champ obligatoire.']}}
    assert data == expected, 'data: %s, expected: %s' % (data, expected)
