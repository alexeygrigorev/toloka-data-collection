import os

token = os.environ['TOLOKA_TOKEN']
host = 'https://toloka.dev'

headers = {
    'Authorization': 'OAuth %s' % token
}