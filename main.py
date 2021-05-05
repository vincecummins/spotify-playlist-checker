import requests
import datetime
from urllib.parse import urlencode
import urllib.parse as urllibparse
import base64
import json
import pymongo
from pymongo import MongoClient
from config import client_id, client_secret, uri

cluster = MongoClient(uri)
db = cluster['spotify-users']
collection = db['users']

def html_processor(set_):
    _str = ''
    arr = list(set_)
    arr.sort()
    for i in arr:
        _str += i + ', '
    return _str

class SpotifyAPI(object):
    auth_token = None
    access_token = None
    client_id = None
    redirect_uri = 'http://127.0.0.1:5000/search'
    client_secret = None
    token_url = "https://accounts.spotify.com/api/token"
    usr_tracks = set()
    usr_artists = set()
    usr_albums = set()

    SCOPE = "playlist-modify playlist-modify-public playlist-modify-private user-read-recently-played user-top-read"
    STATE = ""
    
    auth_query_parameters = {
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": "user-library-read playlist-modify playlist-modify-public playlist-modify-private user-read-recently-played user-top-read",
        # "state": STATE,
        # "show_dialog": SHOW_DIALOG_str,
        "client_id": '74476a178680423dbc90cab914967207'
    }

    URL_ARGS = urlencode(auth_query_parameters)

    AUTH_URL = f"https://accounts.spotify.com/authorize/?{URL_ARGS}"

    def __init__(self, client_id, client_secret, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client_id = client_id
        self.client_secret = client_secret

    def authorize(self, auth_token):
        code_payload = {
            "grant_type": "authorization_code",
            "code": str(auth_token),
            "redirect_uri": 'http://127.0.0.1:5000/search'
        }

        post_request = requests.post(self.token_url, data=code_payload, headers=self.get_token_headers())
        response_data = json.loads(post_request.text)
        acc_token = response_data["access_token"]
        """ now = datetime.datetime.now()
        expires_in = response_data['expires_in']  # seconds
        expires = now + datetime.timedelta(seconds=expires_in)
        self.access_token = response_data["access_token"]
        self.access_token_expires = expires
        self.access_token_did_expire = expires < now """

        auth_header = {"Authorization": f"Bearer {acc_token}"}

        try:
            r2 = requests.get('https://api.spotify.com/v1/me', headers=auth_header)
            _id = r2.json()['id']
            name = r2.json()['display_name']
            if (collection.count_documents({'id': _id})) == 0:
                offset=0
                offs_inc = True
                while offs_inc:
                    r2 = requests.get(f'https://api.spotify.com/v1/me/tracks?offset={offset}', headers=auth_header)
                    print(offset)
                    if offset >= r2.json()['total']:
                        offs_inc = False
                        continue
                    t = r2.json()['items']
                    for x in t:
                        self.usr_artists.add(x['track']['artists'][0]['id'])
                        self.usr_tracks.add(x['track']['id'])
                        self.usr_albums.add(x['track']['album']['id'])
                    offset +=20
                collection.insert_one({'id': _id, 'name': name, 'tracks': list(self.usr_tracks), 'albums': list(self.usr_albums), 'artists': list(self.usr_artists)})
        except:
            print('cant get user library')

        return auth_header

    def get_client_credentials(self):
        client_id = self.client_id
        client_secret = self.client_secret
        if client_secret == None or client_id == None:
            raise Exception("You must set client_id and client_secret")
        client_creds = f"{client_id}:{client_secret}"
        client_creds_b64 = base64.b64encode(client_creds.encode())
        return client_creds_b64.decode()

    def get_token_headers(self):
        client_creds_b64 = self.get_client_credentials()
        return {
            "Authorization": f"Basic {client_creds_b64}"
        }

    def get_token_data(self):
        return {
            "grant_type": "client_credentials"
        }

    def get_playlist(self, _id, auth_header):
        tracks_got = set()
        artists_got = set()
        albums_got = set()
        tracks_not_got = set()
        artists_not_got = set()
        albums_not_got = set()
        r2 = requests.get('https://api.spotify.com/v1/me', headers=auth_header)
        __id = r2.json()['id']
        xx = collection.find_one({'id': __id})
        name = r2.json()['display_name']
        offs = 0
        offs_inc = True
        while offs_inc:
            r = requests.get(f"https://api.spotify.com/v1/playlists/{_id}/tracks?market=AU&offset={offs}", headers=auth_header).json()['items'][:50]
            if len(r) == 0:
                offs_inc = False
                continue
            for x in r:
                try:
                    if x['track']['id'] in xx['tracks']:
                        tracks_got.add(x['track']['name'])
                    else:
                        tracks_not_got.add(x['track']['name'])
                    if x['track']['artists'][0]['id'] in xx['artists']:
                        artists_got.add(x['track']['artists'][0]['name'])
                    else:
                        artists_not_got.add(x['track']['artists'][0]['name'])
                    if x['track']['album']['id'] in xx['albums']:
                        albums_got.add(x['track']['album']['name'])
                    else:
                        albums_not_got.add(x['track']['album']['name'])
                except:
                    print('did not work')
                    continue
            offs +=50
        pl_name = requests.get(f"https://api.spotify.com/v1/playlists/{_id}/", headers=auth_header).json()['name']
        art_p = str(round(len(artists_got)/(len(artists_got) + len(artists_not_got)) *100, 2)) + '%'
        art_np = str(round(len(artists_not_got)/(len(artists_got) + len(artists_not_got)) *100, 2)) + '%'
        alb_p = str(round(len(albums_got)/(len(albums_got) + len(albums_not_got)) *100, 2)) + '%'
        t_p = str(round(len(tracks_got)/(len(tracks_got) + len(tracks_not_got)) *100, 2)) + '%'
        return_obj = {'p': pl_name, 
            'art': html_processor(artists_got), 
            'art_p': art_p,
            'art_n': html_processor(artists_not_got),
            'art_np': art_np,
            'alb': html_processor(albums_got), 
            'alb_p': alb_p,
            't': html_processor(tracks_got), 
            't_p': t_p
        }
        return return_obj

    def base_search(self, query_params, auth_header):  # type
        endpoint = "https://api.spotify.com/v1/search"
        lookup_url = f"{endpoint}?{query_params}"
        r = requests.get(lookup_url, headers=auth_header)
        if r.status_code not in range(200, 299):
            print(r.json(), auth_header)
            return {}
        return self.get_playlist(r.json()['playlists']['items'][0]['id'], auth_header)

    def search(self, auth_header, query=None, operator=None, operator_query=None, search_type='playlist'):
        if query == None:
            raise Exception("A query is required")
        if isinstance(query, dict):
            query = " ".join([f"{k}:{v}" for k, v in query.items()])
        if operator != None and operator_query != None:
            if operator.lower() == "or" or operator.lower() == "not":
                operator = operator.upper()
                if isinstance(operator_query, str):
                    query = f"{query} {operator} {operator_query}"
        query_params = urlencode({"q": query, "type": search_type.lower()})
        return self.base_search(query_params, auth_header)

spotify = SpotifyAPI(client_id, client_secret)
