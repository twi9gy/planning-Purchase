##############################################
#   Библиотеки
##############################################

from flask import jsonify
from random import randint
import numpy as np
import pandas as pd
import json
import math
import datetime as dt
import time
import scipy.stats as sps
import json


##############################################
#   Глобальные переменные
##############################################

##############################################
#   Модель
##############################################

###########################################

class Wilson:
    """docstring"""

    def __init__(self, file, service_level, storage_costs, product_price, shipping_costs, time_shipping,
                 delayed_deliveries):
        """Constructor"""
        self.file = file
        self.service_level = service_level / 100
        self.storage_costs = storage_costs
        self.shipping_costs = shipping_costs
        self.time_shipping = int(time_shipping)
        self.product_price = product_price
        self.delayed_deliveries = int(delayed_deliveries)
        self.prediction = pd.Series(json.load(file)['prediction'])

    # Метод для получения плана закупок
    def getPurchase(self):
        # Получение интенсивности потребления запаса [ед.товара / ед.времени]
        demand_mean = self.prediction.values.mean()
        demand_sum = self.prediction.values.sum()

        # Определение страховаго запаса [ед.товара]
        self.reserve = sps.norm.ppf(self.service_level) * math.sqrt(self.time_shipping * self.prediction.values.std() + demand_mean * self.delayed_deliveries)

        # Получение размера заказа [ед.товара]
        self.size_order = math.sqrt((2 * demand_sum * self.shipping_costs) / (len(self.prediction.values) * self.storage_costs))

        # Период потребления одной поставки [ед.времени]
        freq_delivery = self.size_order * len(self.prediction.values) / demand_sum

        freq = dt.timedelta(days=freq_delivery).days
        if round(dt.timedelta(days=freq_delivery).seconds / 60) > 0:
            freq = freq + 1

        # Количетсво необходимых поставок
        count_orders = demand_mean * len(self.prediction.values) / self.size_order

        # Получение затрат на управление запасами
        total_costs = demand_sum * self.product_price + demand_sum * self.shipping_costs / self.size_order + self.storage_costs * self.size_order / 2

        # Определение точки заказа
        self.P = demand_mean * (self.time_shipping + freq / 2) + self.reserve

        # Симуляция деятельности предприятия
        Q, orders, orders_origin = self.getOrders(freq)

        keys = Q.keys()
        Q_result = {str(k): 0 for k in keys}
        for i in keys:
            Q_result[str(i)] = round(Q[i])

        keys = orders.keys()
        orders_result = {str(k): 0 for k in keys}
        for i in keys:
            orders_result[str(i)] = round(orders[i])

        return {
            'freq_delivery': freq,
            'size_order': round(self.size_order),
            'point_order': round(self.P),
            'reserve': round(self.reserve),
            'count_orders': round(count_orders),
            'total_costs': round(total_costs, 2),
            'product_count': Q_result,
            'start_date': self.prediction.index[0],
            'end_date': self.prediction.index[-1],
            'orders': orders_result,
            'orders_origin': orders_origin
        }

    # Метод для моделирования закупок
    def getOrders(self, freq):
        # Получение времени генерации выборки
        generated_time = pd.DataFrame({'Date': self.prediction.index})
        generated_time['Date'] = pd.to_datetime(generated_time['Date'])

        # Получение спроса
        demand = pd.DataFrame({'Count': self.prediction.values})

        # Устанавлием количество запасов на первый день
        currentQ = { generated_time['Date'][0]: self.P }
        orders = {}
        orders_origin = []
        index_day = 0

        # Имитация работы предприятия
        for i in range(len(generated_time['Date']) - 1):
            order = None
            if len(orders) > 0:
                if generated_time['Date'][i] in orders:
                    order = orders[generated_time['Date'][i]]
            # Прошлый заказ уже пришел ?
            if order is not None:
                currentQ[generated_time['Date'][i + 1]] = currentQ[generated_time['Date'][i]] + self.size_order
            else:
                currentQ[generated_time['Date'][i + 1]] = currentQ[generated_time['Date'][i]] - demand['Count'][i]
            # Не пришло ли время проверки ?
            if index_day % freq == 0:
                # Время проверки
                if self.P >= currentQ[generated_time['Date'][i]]:
                    # Генерируем время доставки
                    delivery = randint(self.time_shipping, self.time_shipping + self.delayed_deliveries)
                    # Делаем заказ
                    try:
                        orders[generated_time['Date'][i + delivery]] = self.size_order
                        orders_origin.append(generated_time['Date'][i])
                    except LookupError:
                        orders_origin.append(generated_time['Date'][i])
            index_day = index_day + 1
        return currentQ, orders, orders_origin
