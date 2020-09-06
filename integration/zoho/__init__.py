from books.service.ZohoBooks import ZohoBooks
from books.exception.BooksException import BooksException
from httplib2 import Http
from books.util import ZohoHttpClient
import pathlib
from integration.zoho.core.constants import *

home = pathlib.Path(os.environ.get('UDAAN_HOME', '/tmp'))


def read_organization_id(access_token):
    zoho_books = ZohoBooks(access_token, '')
    api = zoho_books.get_organizations_api()
    return api.get_organizations()[0].organization_id


def refresh_token(request_data):
    http = Http(timeout=60*1000)
    url = 'https://accounts.zoho.in/oauth/v2/token'
    url += '?' + ZohoHttpClient.form_query_string(request_data)
    resp, content = http.request(url, 'POST')
    return json.loads(content)['access_token']


def dump_to_json_file(json_file, data):
    path = home / json_file
    with open(path, mode='w', encoding='utf-8') as f:
        json.dump(data, f, default=lambda x:  x.to_json() if 'to_json' in dir(x) else x.__dict__)


def read_json_file(json_file, default=[]):
    path = home / json_file
    if not os.path.exists(path):
        with open(path, mode='w', encoding='utf-8') as f:
            json.dump(default, f)
    with open(path, 'r') as f:
        data = json.load(f)
    return data


def get_credentials():
    secret_file = 'secret_file.json'
    auth_data = read_json_file(secret_file, default={})
    try:
        organization_id = read_organization_id(auth_data['access_token'])
    except BooksException as e:
        if e.code == '57':
            print("Token Expired. Refreshing !")
            auth_data['access_token'] = refresh_token(auth_data['refresh_token_req'])
            organization_id = read_organization_id(auth_data['access_token'])
            dump_to_json_file(secret_file, auth_data)
        else:
            raise e
    return auth_data['access_token'], organization_id


zoho_books = ZohoBooks(*get_credentials())
contact_api = zoho_books.get_contacts_api()
items_api = zoho_books.get_items_api()

state_info = { "Andhra Pradesh": ('37', 'AD'),
                "Arunachal Pradesh": ('12', 'AR'),
                "Assam": ('18', 'AS'),
                "Bihar": ('10', 'BR'),
                "Chattisgarh": ('22', 'CG'),
                "Chhattisgarh": ('22', 'CG'),
                "Delhi": ('07', 'DL'),
                "Goa": ('30', 'GA'),
                "Gujarat": ('24', 'GJ'),
                "Haryana": ('06', 'HR'),
                "Himachal Pradesh": ('02', 'HP'),
                "Jammu and Kashmir": ('01', 'JK'),
                "Jammu & Kashmir": ('01', 'JK'),
                "Jharkhand": ('20', 'JH'),
                "Karnataka": ('29', 'KA'),
                "Kerala": ('32', 'KL'),
                "Lakshadweep Islands": ('31', 'LD'),
                "Madhya Pradesh": ('23', 'MP'),
                "Maharashtra": ('27', 'MH'),
                "Manipur": ('14', 'MN'),
                "Meghalaya": ('17', 'ML'),
                "Mizoram": ('15', 'MZ'),
                "Nagaland": ('13', 'NL'),
                "Odisha": ('21', 'OD'),
                "Orissa": ('21', 'OD'),
                "Pondicherry": ('34', 'PY'),
                "Puducherry": ('34', 'PY'),
                "Punjab": ('03', 'PB'),
                "Rajasthan": ('08', 'RJ'),
                "Sikkim": ('11', 'SK'),
                "Tamil Nadu": ('33', 'TN'),
                "Telangana": ('36', 'TS'),
                "Tripura": ('16', 'TR'),
                "Uttar Pradesh": ('09', 'UP'),
                "Uttarakhand": ('05', 'UK'),
                "West Bengal": ('19', 'WB'),
                "Andaman and Nicobar Islands": ('35', 'AN'),
                "Chandigarh": ('04', 'CH'),
                "Dadra and Nagar Haveli": ('26', 'DN'),
                "Daman and Diu": ('25', 'DD'),
                "Daman & Diu'": ('25', 'DD'),
                "Other Territory": ('97', 'OT')}


def find_all_contacts(cached=True):
    json_file = 'zoho_contacts.json'
    if cached:
        return read_json_file(json_file)
    all_contacts = []
    contacts_page = contact_api.get_contacts()
    all_contacts.extend([contact.__dict__ for contact in contacts_page.get_contacts()])
    while contacts_page.page_context.has_more_page:
        contacts_page = contact_api.get_contacts({'page': contacts_page.get_page_context().get_page() + 1})
        all_contacts.extend([contact.__dict__ for contact in contacts_page.get_contacts()])
    dump_to_json_file(json_file, all_contacts)
    return all_contacts


def find_all_items(cached=True):
    json_file = 'zoho_items.json'
    if cached:
        return read_json_file(json_file)
    all_items = []
    items_page = items_api.list_items()
    all_items.extend([item.__dict__ for item in items_page.get_items()])
    while items_page.page_context.has_more_page:
        items_page = items_api.list_items({'page': items_page.get_page_context().get_page() + 1})
        all_items.extend([item.__dict__ for item in items_page.get_items()])
    dump_to_json_file(json_file, all_items)
    return all_items


#
# if __name__ == '__main__':
#     find_all_contacts(cached=False)
