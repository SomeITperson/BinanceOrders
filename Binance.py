import json
import hmac
import time
import requests
import hashlib
from urllib.parse import urlencode
import random
import os
from dotenv import load_dotenv


class FieldNotExists(Exception):
    def __init__(self, field, message="Отсутствует поле в данных с frontend"):
        self.field = field
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message}: {self.field}"


class BinancePlaceOrder():
    def __init__(self, frontend_data):
        self.frontend_data = frontend_data
        self.spot = self._get_spot()
        self.base_url = 'https://testnet.binance.vision'
        self.key = os.getenv("KEY")
        self.secret = os.getenv("SECRET")
    
    def _hashing(self, query_string):
        return hmac.new(self.secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256).hexdigest()
    
    def _get_spot(self):
        spot = requests.get('https://api.binance.com/api/v3/ticker/price').json()
        return spot

    def _get_timestamp(self):
        return int(time.time() * 1000)
    
    def _dispatch_request(self, http_method):
        session = requests.Session()
        session.headers.update(
            {"Content-Type": "application/json;charset=utf-8", "X-MBX-APIKEY": self.key}
        )
        return {
            "GET": session.get,
            "DELETE": session.delete,
            "PUT": session.put,
            "POST": session.post,
        }.get(http_method, "GET")
    
    def get_randint(self, val1, val2):
        return random.randint(val1, val2)
    
    def create_order_data(self):
        volume = self.get_randint(
            self.frontend_data['volume'] - self.frontend_data['amountDif'],
            self.frontend_data['volume'] + self.frontend_data['amountDif']
        ) / frontend['number']
        orders_list = [{
            "symbol": self.frontend_data['symbol'],
            "side": frontend['side'],
            "type": "LIMIT",
            "timeInForce": "GTC",
            "quantity": round(volume / float([q for q in self.spot if q['symbol'] == self.frontend_data['symbol']][0]['price']), 3),
            "price": self.get_randint(
                self.frontend_data['priceMin'],
                self.frontend_data['priceMax']
            ),
        } for val in range(0, self.frontend_data['number']) if val != self.frontend_data['number']]
        return orders_list

    def send_signed_request(self, http_method, url_path, payload={}):
        query_string = urlencode(payload, True)
        if query_string:
            query_string = "{}&timestamp={}".format(query_string, self._get_timestamp())
        else:
            query_string = "timestamp={}".format(self._get_timestamp())
        url = (
            self.base_url + url_path + "?" + query_string + "&signature=" + self._hashing(query_string)
        )
        params = {"url": url, "params": {}}
        response = self._dispatch_request(http_method)(**params)
        return response.json()
    
    def output(self, response, order):
        print(
            f"""{self.frontend_data['side']} ордер размещен за {response['price']}
            в количестве {order['quantity']}\nОтвет Binance:\n{response}\n"""
        )


if __name__ == "__main__":
    load_dotenv()

    with open("Frontend.json", "r+") as f:
        required_fields = ['volume', 'number', 'amountDif', 'side', 'priceMin', 'priceMax', 'symbol']
        frontend = json.loads(f.read())
        for field in required_fields:
            if field not in frontend:
                raise FieldNotExists(field)

    binance = BinancePlaceOrder(frontend_data=frontend)
    orders = binance.create_order_data()
    avaliable_volume = False if sum([order['price'] for order in orders]) > frontend['volume'] - frontend['amountDif'] else True
    
    if (avaliable_volume and frontend['side'] == "BUY") or frontend['side'] == "SELL":
        for order in orders:
            response = binance.send_signed_request("POST", "/api/v3/order", order)
            if not 'code' in response:
                binance.output(response, order)
                continue
            print(response)
    else:
        print(f"Сумма всех ордеров(сумма всех 'price' ордеров) превышает установленный минимальный баланс {frontend['volume']-frontend['amountDif']}")