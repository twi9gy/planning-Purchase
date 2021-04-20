##############################################
#   Библиотеки
##############################################

from flask import jsonify
import numpy as np
import pandas as pd
import json
import math
import datetime as dt
import time
import scipy.stats as sps


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
        self.time_shipping = time_shipping
        self.product_price = product_price
        self.delayed_deliveries = delayed_deliveries
        self.prediction = pd.DataFrame(pd.read_json(file, convert_dates=False, convert_axes=False))['prediction']

    # Метод для получения плана закупок
    def getPurchase(self):
        # Получение интенсивности потребления запаса [ед.товара / ед.времени]
        demand_mean = self.prediction.values.mean()
        demand_sum = self.prediction.values.sum()

        # Определение страховаго запаса [ед.товара]
        self.reserve = sps.norm.ppf(self.service_level) * math.sqrt(
            self.time_shipping * self.prediction.values.std() + demand_mean * self.delayed_deliveries)

        # Получение размера заказа [ед.товара]
        self.size_order = math.sqrt(
            (2 * demand_sum * self.shipping_costs) / (len(self.prediction.values) * self.storage_costs))

        # Период потребления одной поставки [ед.времени]
        self.freq_delivery = self.size_order * len(self.prediction.values) / demand_sum

        freq = dt.timedelta(days=self.freq_delivery).days
        if round(dt.timedelta(days=self.freq_delivery).seconds / 60) > 0:
            freq = freq + 1

        # Количетсво необходимых поставок
        count_orders = demand_mean * len(self.prediction.values) / self.size_order

        # Получение затрат на управление запасами
        total_costs = demand_sum * self.product_price + demand_sum * self.shipping_costs / self.size_order + self.storage_costs * self.size_order / 2

        # Определение точки заказа
        self.P = demand_mean * (self.time_shipping + freq / 2) + self.reserve

        # Симуляция деятельности предприятия
        Q, orders = self.getOrders(freq)

        keys = Q.keys()
        Q_result = {str(k): 0 for k in keys}
        for i in Q.keys():
            Q_result[str(i)] = round(Q[i])

        keys = orders.keys()
        orders_result = {str(k): 0 for k in keys}
        for i in orders.keys():
            orders_result[str(i)] = round(orders[i])

        return {
            'freq_delivery': freq,
            'size_order': round(self.size_order),
            'point_order': round(self.P),
            'reserve': round(self.reserve),
            'count_orders': round(count_orders),
            'total_costs': round(total_costs, 2),
            'Q': Q_result,
            'orders': orders_result
        }

    # Метод для моделирования закупок
    def getOrders(self, freq):
        # Получение времени генерации выборки
        generated_time = pd.DataFrame({'Date': self.prediction.index})
        generated_time['Date'] = pd.to_datetime(generated_time['Date'])

        # Получение спроса
        demand = pd.DataFrame({'Count': self.prediction.values})

        # Генерация периодов проверки
        step = dt.timedelta(days=round(freq))
        periods = [i + step for i in generated_time['Date']]
        check = []
        for i in range(0, len(periods), step.days):
            check.append(periods[i])

        # Устанавлием количество запасов на первый день
        currentQ = {generated_time['Date'][0]: self.size_order + self.reserve}
        orders = {}

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
            if int(generated_time['Date'][i].day) % freq == 0 and i != 0:
                # Время проверки
                if self.P >= currentQ[generated_time['Date'][i]]:
                    # Делаем заказ
                    orders[generated_time['Date'][i + 1]] = self.size_order
        return currentQ, orders
