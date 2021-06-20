##############################################
#   Библиотеки
##############################################

from flask import request, jsonify
from flask import jsonify
from api.model.wilson_model import Wilson
import scipy.stats as sps

##############################################
#   Глобальные переменные
##############################################

ALLOWED_EXTENSIONS = {'json'}


##############################################
#   Методы
##############################################

#   Метод для фильтрации файлов
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


#   Метод для создания плана закупок
def create(file, freq_interval, service_level, storage_costs, product_price, shipping_costs, time_shipping,
           delayed_deliveries=1, production_quantity=30):
    try:
        # Проверяем метод у запроса
        if request.method == 'POST':
            file = request.files['file']
            # Проверяем наличие файла и его расширение
            if file and allowed_file(file.filename):
                wilson = Wilson(file, freq_interval, service_level, storage_costs, product_price, shipping_costs,
                                time_shipping, delayed_deliveries, production_quantity)
                return jsonify(wilson.getPurchase()), 200
            else:
                return 'Файл не имеет расширения json', 400
        return 'Метод имеет доступ POST', 400
    except Exception:
        return Exception, 400
