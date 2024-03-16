import json
import logging
import time

import pymysql
import requests
from flask import Blueprint
from flask import Flask, request, jsonify
from flask_cors import CORS

from model import Users, Address, db, Device
from routes import routes_bp
from utils import get_all_columns, get_database_name, get_columns_to_select, construct_select_clause, execute_query, \
    convert_to_json, table_exists

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# 设置数据库连接字符串
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:122600@localhost/eviroment_data?charset=utf8'
# 配置连接池大小（可选）
app.config['SQLALCHEMY_POOL_SIZE'] = 10
app.config['SQLALCHEMY_POOL_TIMEOUT'] = 30
app.config['SQLALCHEMY_POOL_RECYCLE'] = 3600
db.init_app(app)

cors = CORS(app)

# 数据库连接参数
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "122600",
    "database": "eviroment_data",
    "charset": "utf8",
}

# 最大连接数
MAX_DB_CONNECTIONS = 1000

# 全局数据库连接池
db_connections = []

# 创建名为"agriculture_bp"的Blueprint，并指定前缀
agriculture_bp = Blueprint('agriculture', __name__, url_prefix='/agriculture')

# 全局变量，用于存储预测方法和模型
method = "0"
model = "0"


# 函数用于获取数据库连接
def get_db_connection():
    if len(db_connections) < MAX_DB_CONNECTIONS:
        conn = pymysql.connect(**DB_CONFIG)
        if conn is None:
            logger.error("Failed to create a database connection.")
            raise Exception("Failed to create a database connection.")
        db_connections.append(conn)
        logger.info(f"New database connection created. Total connections: {len(db_connections)}")
        return conn
    else:
        # 如果连接池已满，等待并尝试重新获取连接
        for conn in db_connections:
            if not conn.open:
                conn.ping(reconnect=True)
                logger.info(f"Database connection reopened. Total connections: {len(db_connections)}")
                return conn
        time.sleep(1)  # 等待1秒后重试
        return get_db_connection()


# 获取用户设备列表
@agriculture_bp.route("/user/deviceList", methods=['GET'])
def get_device_list():
    try:
        # 查询所有站点
        sites = Address.query.all()

        # 查询每个站点的设备
        device_list = []

        for site in sites:
            site_info = {
                'id': str(site.id),
                'name': site.name,
                'isSite': True,  # 添加isSite字段
                'children': [{'id': str(device.id), 'name': device.device_name, 'isDevice': True} for device in
                             site.devices]
            }

            device_list.append(site_info)

        # 构建响应 JSON
        response = {
            'code': 200,
            'data': device_list,
            'message': '成功'
        }

        return jsonify(response)

    except Exception as e:
        response = {
            'code': 500,
            'message': '服务器错误: {}'.format(str(e))
        }
        return jsonify(response), 500


@agriculture_bp.route('/menu/list', methods=['GET'])
def mock_response():
    headers = request.headers
    access_token = headers.get('X-Access-Token')
    if access_token == 'bqddxxwqmfncffacvbpkuxvwvqrhln':
        with open('config.json', 'r', encoding='utf-8') as file:
            response_data = json.load(file)['menu']
        return jsonify({"code": 200, "data": response_data, "message": "成功"})
    else:
        return jsonify({"code": 401, "message": "Unauthorized"})


# 返回站点列表
@agriculture_bp.route("/address/select", methods=['GET'])
def address_select():
    try:
        # 查询所有地址
        addresses = Address.query.all()

        # 构建响应数据
        rows = [{'id': address.id, 'name': address.name} for address in addresses]
        response_data = {'code': 200, 'data': rows, 'message': 'Success'}
        return jsonify(response_data)
    except Exception as e:
        response_data = {'code': 500, 'message': f'Server Error: {str(e)}'}
        return jsonify(response_data), 500


# 返回仪表盘数据
@agriculture_bp.route('/device/count', methods=['GET'])
def get_device_count():
    conn = None
    try:
        conn = get_db_connection()  # 获取数据库连接

        # 执行查询获取设备数量
        with conn.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) FROM device;')
            device_count = cursor.fetchone()[0]  # 获取设备数量

        # 执行查询获取站点数量
        with conn.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) FROM env_db;')
            site_count = cursor.fetchone()[0]  # 获取站点数量

        # 查询mihoutao39表的数据记录数量
        with conn.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) FROM mihoutao39;')
            mihoutao39_count = cursor.fetchone()[0]  # 获取mihoutao39表的数据记录数量

        # 查询pingguo42表的数据记录数量
        with conn.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) FROM pingguo42;')
            pingguo42_count = cursor.fetchone()[0]  # 获取pingguo42表的数据记录数量

        # 查询putao41表的数据记录数量
        with conn.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) FROM putao41;')
            putao41_count = cursor.fetchone()[0]  # 获取putao41表的数据记录数量

        # 查询shucai44表的数据记录数量
        with conn.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) FROM shucai44;')
            shucai44_count = cursor.fetchone()[0]  # 获取shucai44表的数据记录数量

        total_number_of_device_records = mihoutao39_count + pingguo42_count + putao41_count + shucai44_count

        response_data = {
            'code': 200,
            'message': '成功',
            'data': {
                'deviceCount': device_count,
                'totalDeviceDataCount': total_number_of_device_records,
                'siteCount': site_count,
                'siteValues':
                    [
                        {
                            'name': "武功猕猴桃试验站",
                            'value': mihoutao39_count
                        },
                        {
                            'name': "白水苹果试验站",
                            'value': pingguo42_count
                        },
                        {
                            'name': "临渭葡萄研究所",
                            'value': putao41_count
                        },
                        {
                            'name': "泾阳蔬菜示范站",
                            'value': shucai44_count
                        }
                    ]
            }
        }

        return jsonify(response_data)

    except Exception as e:
        response_data = {
            'code': 500,
            'message': f'服务器错误: {str(e)}'
        }
        return jsonify(response_data), 500

    finally:
        if conn and conn.open:
            conn.close()


# 返回传感器设备列表（根据地区）
@agriculture_bp.route("/device/select", methods=['GET'])
def device_select():
    try:
        # 获取请求参数
        address_id = request.args.get("address_id", default=1, type=int)

        # 查询符合条件的设备列表
        devices = Device.query.filter_by(address_id=address_id).all()

        # 构建响应数据
        rows = [{'id': device.id, 'device_name': device.device_name,
                 'business_id': device.business_id, 'device_id': device.device_id,
                 'collect_run': device.collect_run} for device in devices]

        response_data = {'code': 200, 'data': rows, 'message': 'Success'}
        return jsonify(response_data)
    except Exception as e:
        response_data = {'code': 500, 'message': f'Server Error: {str(e)}'}
        return jsonify(response_data), 500


# 根据参数返回数据库中的数据
@agriculture_bp.route("/data/show", methods=['GET'])
def data_base():
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            device_id = request.args.get("deviceId", default=1, type=str)
            hour = request.args.get("hour", default=24, type=int)
            columns_param = request.args.get("columns")

            dbname = get_database_name(cur, device_id)
            if not table_exists(cur, dbname):
                response_data = {
                    'code': 404,
                    'message': 'No data found',
                }
                return jsonify(response_data)

            all_columns = get_all_columns(cur, dbname)
            columns_to_select = get_columns_to_select(columns_param, all_columns)

            select_clause = construct_select_clause(columns_to_select)
            results = execute_query(cur, dbname, select_clause, hour)

            json_data = convert_to_json(results, columns_to_select)

            response_data = {
                'code': 200,
                'message': 'Success',
                'data': json_data
            }

            return jsonify(response_data)

    except IndexError:
        response_data = {
            'code': 404,
            'message': 'No data found',
        }
        return jsonify(response_data)

    except Exception as e:
        print("服务器错误:", str(e))
        response_data = {
            'code': 500,
            'message': '服务器错误: {}'.format(str(e))
        }
        return jsonify(response_data), 500


# 返回实时数据或者设备属性等等
@agriculture_bp.route("/device/api", methods=['GET'])
def device_api():
    conn = None  # 初始化连接为 None，以确保无论如何都能关闭连接
    try:
        conn = get_db_connection()
        # 创建数据库游标
        cur = conn.cursor()
        device_id = request.args.get("id", default=1, type=str)
        api_method = request.args.get("method", default=1, type=str)
        cur.execute("SELECT api,business_id, device_id, equipment, version, collect_run FROM device WHERE id = %s;",
                    device_id)
        conn.commit()
        res_device = cur.fetchone()
        if res_device is None:
            print("未查询到此设备")
            response = {
                "code": 404,
                "message": "未查询到此设备"
            }
            return jsonify(response), 404

        if res_device[5] == '0':
            response = {
                "code": 403,
                "message": "没有访问权限"
            }
            return jsonify(response), 403

        res_device[0] + '/' + api_method + '?' + 'Version=' + res_device[4] + '&Business=' + res_device[
            1] + '&Equipment=' + res_device[3] + '&RequestTime=' + str(
            int(time.time())) + '&Value={ "page": 1,"length": 5,"deviceId":' + res_device[2] + '}'
        # device_api_last_index = res_api.rfind("/")
        device_url = res_device[0] + '/' + api_method
        value = "{ 'page': 1,'length': 5, 'deviceId': " + res_device[2] + " }"
        device_params = {
            "Version": res_device[4],
            "Business": res_device[1],
            "Equipment": res_device[3],
            "RequestTime": str(int(time.time())),
            "Value": value
        }
        result_data = requests.get(device_url, device_params)
        result = json.loads(result_data.text)

        return jsonify(result)

    except Exception as e:
        # 处理异常，您可以根据需要进行记录或其他操作
        response_data = {
            'code': 500,
            'message': '服务器错误: {}'.format(str(e))
        }
        return jsonify(response_data), 500

    finally:
        # 在 finally 块中关闭连接，确保无论如何都会关闭连接
        if conn and conn.open:
            conn.close()


if __name__ == "__main__":
    # 注册Blueprint到Flask应用中
    app.register_blueprint(routes_bp)
    app.register_blueprint(agriculture_bp)
    app.run(debug=True, host="0.0.0.0", port=5000)
    print('the db is closed')
