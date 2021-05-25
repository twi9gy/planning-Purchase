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
import calendar


##############################################
#   Глобальные переменные
##############################################

##############################################
#   Модель
##############################################

###########################################

class Wilson:
    """docstring"""

    def __init__(self, file, freq_interval, service_level, storage_costs, product_price, shipping_costs, time_shipping,
                 delayed_deliveries):
        """Constructor"""
        self.file = file
        self.freq_interval = freq_interval
        self.service_level = service_level / 100
        self.storage_costs = storage_costs
        self.shipping_costs = shipping_costs
        self.time_shipping = int(time_shipping)
        self.product_price = product_price
        self.delayed_deliveries = int(delayed_deliveries)
        self.prediction = pd.Series(json.load(file)['prediction'])

    # Метод для получения плана закупок
    def getPurchase(self):
        freq_index = 1
        if self.freq_interval == '7D':
            freq_index = 7
        elif self.freq_interval == '1M':
            freq_index = 30

        # Получение интенсивности потребления запаса [ед.товара / ед.времени]
        demand_mean = self.prediction.values.mean()
        demand_sum = self.prediction.values.sum()

        # Определение страховаго запаса [ед.товара]
        self.reserve = sps.norm.ppf(self.service_level) * math.sqrt(
            self.time_shipping * self.prediction.values.std() + demand_mean * self.delayed_deliveries)

        # Получение размера заказа [ед.товара]
        self.size_order = math.sqrt(
            (2 * demand_sum * self.shipping_costs) / (len(self.prediction.values) * freq_index * self.storage_costs))

        # Период потребления одной поставки [ед.времени]
        freq_delivery = self.size_order * len(self.prediction.values) * freq_index / demand_sum

        freq = dt.timedelta(days=freq_delivery).days
        if round(dt.timedelta(days=freq_delivery).seconds / 60) > 0:
            freq += 1

        # Количетсво необходимых поставок
        count_orders = demand_mean * len(self.prediction.values) / self.size_order

        # Получение затрат на управление запасами
        total_costs = demand_sum * self.product_price + demand_sum * self.shipping_costs / self.size_order + self.storage_costs * self.size_order / 2

        # Определение точки заказа
        self.P = demand_mean / freq_index * (self.time_shipping + freq / 2) + self.reserve

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
        # Получаем начало и конец интервала
        dt_start = self.prediction.index[0]
        dt_end = self.prediction.index[-1]

        # Конвертируем в dateTime
        dt_start_datetime = dt.datetime.strptime(dt_start, '%Y-%m-%d %H:%M:%S')
        dt_end_datetime = dt.datetime.strptime(dt_end, '%Y-%m-%d %H:%M:%S')

        # Генерация периода прогнозирования
        delta = dt_end_datetime - dt_start_datetime

        # Получение спроса
        demand = pd.DataFrame({'Count': self.prediction.values})

        index_day = 0
        current_demand = 0
        index_demand = 0
        forecast_period = []
        purchase_count = []
        month_count_day = 0
        current_date = dt.datetime.strptime(self.prediction.index[index_demand], '%Y-%m-%d %H:%M:%S')
        month_count_day = int(calendar.monthrange(current_date.year, current_date.month)[1])

        for i in range(delta.days):
            forecast_period.append(dt_start_datetime + dt.timedelta(i))
            if self.freq_interval == '1D':
                purchase_count.append(round(demand['Count'][i]))
            elif self.freq_interval == '7D':
                if index_day % 7 == 0:
                    current_demand = demand['Count'][index_demand] / 7
                    index_demand += 1
                purchase_count.append(round(current_demand))
            elif self.freq_interval == '1M':
                if index_day == month_count_day * index_demand:
                    current_date = dt.datetime.strptime(self.prediction.index[index_demand], '%Y-%m-%d %H:%M:%S')
                    month_count_day = int(calendar.monthrange(current_date.year, current_date.month)[1])
                    current_demand = demand['Count'][index_demand] / month_count_day
                    index_demand += 1
                purchase_count.append(current_demand)
            index_day += 1

        # Преобразование периода к Series
        generated_time = pd.DataFrame({'Date': forecast_period})
        generated_time['Date'] = pd.to_datetime(generated_time['Date'])

        # Устанавлием количество запасов на первый день
        currentQ = {generated_time['Date'][0]: self.P}
        orders = {}
        orders_origin = []
        index_day = 0

        # Имитация работы предприятия
        for i in range(len(generated_time)):
            order = None
            if len(orders) > 0:
                if generated_time['Date'][i] in orders:
                    order = orders[generated_time['Date'][i]]
            # Прошлый заказ уже пришел ?
            try:
                if order is not None:
                    currentQ[generated_time['Date'][i + 1]] = currentQ[generated_time['Date'][i]] + self.size_order
                else:
                    if currentQ[generated_time['Date'][i]] - purchase_count[i] > 0:
                        currentQ[generated_time['Date'][i + 1]] = currentQ[generated_time['Date'][i]] - purchase_count[i]
                    else:
                        currentQ[generated_time['Date'][i + 1]] = 0
            except LookupError:
                print('Ошибка. Выход за пределы массива.')
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
            index_day += 1
        return currentQ, orders, orders_origin