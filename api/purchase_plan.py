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

ALLOWED_EXTENSIONS = {'csv', 'json'}


##############################################
#   Методы
##############################################

#   Метод для фильтрации файлов
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


#   Метод для создания плана закупок
def create(file, service_level, storage_costs, product_price, shipping_costs, time_shipping, delayed_deliveries=1):
    try:
        # Проверяем метод у запроса
        if request.method == 'POST':
            file = request.files['file']
            # Проверяем наличие файла и его расширение
            if file and allowed_file(file.filename):
                wilson = Wilson(file, service_level, storage_costs, product_price, shipping_costs, time_shipping,
                                delayed_deliveries)
                return jsonify(wilson.getPurchase())
            else:
                return 'Файл не имеет расширения json', 400
        return 'Метод имеет доступ POST', 400
    except Exception:
        return Exception, 400
