import urllib.request, urllib.error, urllib.parse
from datetime import datetime, timedelta
from integration.udaan import get_session_cookie
from integration import home
import csv


headers = {'accept-encoding': 'gzip', 'cookie': 's={}'.format(get_session_cookie())}


class OrderItem(object):

    def __init__(self, row):
        self.phone = row[7].split('-')[1]
        self.GSTIN = row[8] if 'Cant find GSTIN' not in row[8] and 'Buyer' not in row[8] else ''
        self.company_name = row[6]
        self.customer_name = row[5]
        address_splits = row[11].split('\n', 1)
        self.address_1 = address_splits[0]
        self.address_2 = address_splits[1] if len(address_splits) > 1 else ''
        self.state = row[10]
        self.city = row[9]
        self.units = row[13]
        self.units_price = row[14]
        self.listing_id = row[19]
        self.listing_title = row[20]
        self.order_id = row[1]
        self.order_datetime = row[0],
        self.status = row[3]


def download_orders(past_x_days, status='SELLER_ORDER_PAYMENT_RECEIVED'):
    params = get_params(past_x_days, status)
    qs = urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request('https://udaan.com/sellercentral/orders/download?' + qs)
    for h in list(headers.keys()):
        req.add_header(h, headers[h])
    print(qs)
    output_file = home + '/new-orders-{}.csv'.format(status)
    retries = 3
    while retries > 0:
        try:
            with urllib.request.urlopen(req) as response, open(output_file, 'wb') as out_file:
                data = response.read()
                out_file.write(data)
            break
        except urllib.error.HTTPError as e:
            print(e)
            print("Retrying. Tries Left: {}".format(retries - 1))
            retries -= 1
            if retries <= 0:
                raise Exception(e)
    return output_file


def get_params(past_x_days, status):
    now = datetime.now()
    end_time = now.strftime("%Y-%m-%d")
    start_time = (datetime.today() - timedelta(days=past_x_days)).strftime("%Y-%m-%d")
    params = {'start_time': start_time,
              'end_time': end_time,
              'state': status,
              'action': 'download'}
    return params


def _parse_orders(orders_file):
    line_count = 0
    orders = dict()
    with open(orders_file) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        for row in csv_reader:
            if line_count != 0:
                order_item = OrderItem(row)
                order_items = orders.get(order_item.order_id, [])
                order_items.append(order_item)
                orders[order_item.order_id] = order_items
            line_count += 1
    return orders

def parse_orders_csv_dict(orders_file):
    orders = dict()
    order_keys = ['Date', 'Order-Id', 'Order Type', 'Order Status', 'Seller Org Name', 'Buyer Name', 'Buyer Org Name', 'Buyer Mobile Number', 'GSTIN', 'Buyer City', 'Buyer State', 'Buyer Org Address', 'Invoice Id', 'AWB Num', 'Logistic Partner']
    with open(orders_file) as csv_file:
        csv_reader = csv.DictReader(csv_file, delimiter=',')
        for row in csv_reader:
            if None in row.keys():
                row['SetContent'] = row[None]
                del row[None]
            for k in row.keys():
                if isinstance(row[k], type([])):
                    for a in range(len(row[k])):
                        if not row[k][a]:
                            row[k][a] = None
                elif not row[k]:
                    row[k] = None

            order_id = row['Order-Id']
            if order_id in orders:
                order_details = orders[order_id]
            else:
                order_details = {k: row[k] for k in row if k in order_keys}
                orders[order_id] = order_details
                order_details['items'] = []
            order_details['items'].append(row)
    return orders


def fetch_orders(past):
    orders_file = download_orders(past)
    return _parse_orders(orders_file)


def download_orders_all_status(past_x_days):
    all_statuses = ['SELLER_ORDER_PAYMENT_RECEIVED', 'SELLER_ORDER_RTS', 'SELLER_ORDER_PICKED', 'SELLER_ORDER_SHIPPED', 'SELLER_ORDER_DELIVERED', 'SELLER_ORDER_SELLER_CANCEL', 'SELLER_ORDER_BUYER_CANCEL']
    files = {}
    for status in all_statuses:
        files[status] = download_orders(past_x_days, status)
    return files

