
import os
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv


# ==========================================
# PostgreSQL 資料庫連線設定
# ==========================================

load_dotenv(
    os.path.join(
        os.path.dirname(__file__),
        '..',
        '.env'
    )
)

USER = os.getenv('DB_USER')
PASSWORD = os.getenv('DB_PASSWORD')
DBNAME = os.getenv('DB_NAME')
HOST = os.getenv('DB_HOST')
PORT = os.getenv('DB_PORT')


# ==========================================
# 資料庫操作類別
# ==========================================

class DB:

    connection_pool = pool.SimpleConnectionPool(
        1, 100,
        user=USER,
        password=PASSWORD,
        host=HOST,
        port=PORT,
        dbname=DBNAME
    )

    @staticmethod
    def connect():
        return DB.connection_pool.getconn()

    @staticmethod
    def release(connection):
        DB.connection_pool.putconn(connection)

    @staticmethod
    def execute_input(sql, input_data):

        if not isinstance(input_data, (tuple, list)):
            raise TypeError(
                "Input should be a tuple or list"
            )

        connection = DB.connect()

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, input_data)

            connection.commit()

        except psycopg2.Error as e:
            connection.rollback()
            print(f"Error executing SQL: {e}")
            raise

        finally:
            DB.release(connection)

    @staticmethod
    def execute(sql):

        connection = DB.connect()

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql)

            connection.commit()

        except psycopg2.Error as e:
            connection.rollback()
            print(f"Error executing SQL: {e}")
            raise

        finally:
            DB.release(connection)

    @staticmethod
    def fetchall(sql, input_data=None):

        connection = DB.connect()

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, input_data)
                result = cursor.fetchall()

            connection.rollback()
            return result

        except psycopg2.Error as e:
            connection.rollback()
            print(f"Error fetching data: {e}")
            raise

        finally:
            DB.release(connection)

    @staticmethod
    def fetchone(sql, input_data=None):

        connection = DB.connect()

        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, input_data)
                result = cursor.fetchone()

            connection.rollback()
            return result

        except psycopg2.Error as e:
            connection.rollback()
            print(f"Error fetching data: {e}")
            raise

        finally:
            DB.release(connection)


# ==========================================
# 系所資料
# ==========================================

class Department:

    @staticmethod
    def get_all():

        sql = """
            SELECT did, dname
            FROM department
            ORDER BY dname
        """

        return DB.fetchall(sql)


# ==========================================
# 校園系統使用者
# ==========================================

class AppUser:

    # 使用 UID 查詢帳號
    @staticmethod
    def get_user(uid):

        sql = """
            SELECT
                uid,
                user_name,
                password_hash,
                identity,
                email,
                phone,
                did
            FROM app_user
            WHERE uid = %s
        """

        return DB.fetchone(sql, (uid,))

    # 取得使用者身分與姓名
    @staticmethod
    def get_role(uid):

        sql = """
            SELECT
                identity,
                user_name
            FROM app_user
            WHERE uid = %s
        """

        return DB.fetchone(sql, (uid,))

    # 檢查 Email 是否重複
    @staticmethod
    def get_user_by_email(email):

        sql = """
            SELECT uid
            FROM app_user
            WHERE email = %s
        """

        return DB.fetchone(sql, (email,))

    # 註冊新使用者
    @staticmethod
    def create_user(input_data):

        sql = """
            INSERT INTO app_user
            (
                uid,
                user_name,
                password_hash,
                identity,
                email,
                phone,
                did
            )
            VALUES
            (
                %s, %s, %s, %s,
                %s, %s, %s
            )
        """

        DB.execute_input(sql, (
            input_data['uid'],
            input_data['user_name'],
            input_data['password_hash'],
            'student',
            input_data['email'],
            input_data['phone'],
            input_data['did']
        ))


# ==========================================
# 原始書店系統：會員
# ==========================================

class Member:

    @staticmethod
    def get_member(account):

        sql = """
            SELECT account, password, mid,
                   identity, name
            FROM member
            WHERE account = %s
        """

        return DB.fetchall(sql, (account,))

    @staticmethod
    def get_all_account():

        sql = "SELECT account FROM member"

        return DB.fetchall(sql)

    @staticmethod
    def create_member(input_data):

        sql = """
            INSERT INTO member
            (name, account, password, identity)
            VALUES (%s, %s, %s, %s)
        """

        DB.execute_input(sql, (
            input_data['name'],
            input_data['account'],
            input_data['password'],
            input_data['identity']
        ))

    @staticmethod
    def delete_product(tno, pid):

        sql = """
            DELETE FROM record
            WHERE tno = %s AND pid = %s
        """

        DB.execute_input(sql, (tno, pid))

    @staticmethod
    def get_order(userid):

        sql = """
            SELECT *
            FROM order_list
            WHERE mid = %s
            ORDER BY ordertime DESC
        """

        return DB.fetchall(sql, (userid,))

    @staticmethod
    def get_role(userid):

        sql = """
            SELECT identity, name
            FROM member
            WHERE mid = %s
        """

        return DB.fetchone(sql, (userid,))


# ==========================================
# 原始書店系統：購物車
# ==========================================

class Cart:

    @staticmethod
    def check(user_id):

        sql = """
            SELECT *
            FROM cart, record
            WHERE cart.mid = %s::bigint
              AND cart.tno = record.tno::bigint
        """

        return DB.fetchone(sql, (user_id,))

    @staticmethod
    def get_cart(user_id):

        sql = """
            SELECT *
            FROM cart
            WHERE mid = %s
        """

        return DB.fetchone(sql, (user_id,))

    @staticmethod
    def add_cart(user_id, time):

        sql = """
            INSERT INTO cart
            (mid, carttime, tno)
            VALUES (%s, %s, nextval('cart_tno_seq'))
        """

        DB.execute_input(sql, (user_id, time))

    @staticmethod
    def clear_cart(user_id):

        sql = """
            DELETE FROM cart
            WHERE mid = %s
        """

        DB.execute_input(sql, (user_id,))


# ==========================================
# 原始書店系統：商品
# ==========================================

class Product:

    @staticmethod
    def count():

        sql = "SELECT COUNT(*) FROM product"

        return DB.fetchone(sql)

    @staticmethod
    def get_product(pid):

        sql = """
            SELECT *
            FROM product
            WHERE pid = %s
        """

        return DB.fetchone(sql, (pid,))

    @staticmethod
    def get_all_product():

        sql = "SELECT * FROM product"

        return DB.fetchall(sql)

    @staticmethod
    def get_name(pid):

        sql = """
            SELECT pname
            FROM product
            WHERE pid = %s
        """

        return DB.fetchone(sql, (pid,))[0]

    @staticmethod
    def add_product(input_data):

        sql = """
            INSERT INTO product
            (pid, pname, price, category, pdesc)
            VALUES (%s, %s, %s, %s, %s)
        """

        DB.execute_input(sql, (
            input_data['pid'],
            input_data['pname'],
            input_data['price'],
            input_data['category'],
            input_data['pdesc']
        ))

    @staticmethod
    def delete_product(pid):

        sql = """
            DELETE FROM product
            WHERE pid = %s
        """

        DB.execute_input(sql, (pid,))

    @staticmethod
    def update_product(input_data):

        sql = """
            UPDATE product
            SET pname = %s,
                price = %s,
                category = %s,
                pdesc = %s
            WHERE pid = %s
        """

        DB.execute_input(sql, (
            input_data['pname'],
            input_data['price'],
            input_data['category'],
            input_data['pdesc'],
            input_data['pid']
        ))


# ==========================================
# 原始書店系統：購買紀錄
# ==========================================

class Record:

    @staticmethod
    def get_total_money(tno):

        sql = """
            SELECT SUM(total)
            FROM record
            WHERE tno = %s
        """

        return DB.fetchone(sql, (tno,))[0]

    @staticmethod
    def check_product(pid, tno):

        sql = """
            SELECT *
            FROM record
            WHERE pid = %s AND tno = %s
        """

        return DB.fetchone(sql, (pid, tno))

    @staticmethod
    def get_price(pid):

        sql = """
            SELECT price
            FROM product
            WHERE pid = %s
        """

        return DB.fetchone(sql, (pid,))[0]

    @staticmethod
    def add_product(input_data):

        sql = """
            INSERT INTO record
            (pid, tno, amount, saleprice, total)
            VALUES (%s, %s, 1, %s, %s)
        """

        DB.execute_input(sql, (
            input_data['pid'],
            input_data['tno'],
            input_data['saleprice'],
            input_data['total']
        ))

    @staticmethod
    def get_record(tno):

        sql = """
            SELECT *
            FROM record
            WHERE tno = %s
        """

        return DB.fetchall(sql, (tno,))

    @staticmethod
    def get_amount(tno, pid):

        sql = """
            SELECT amount
            FROM record
            WHERE tno = %s AND pid = %s
        """

        return DB.fetchone(sql, (tno, pid))[0]

    @staticmethod
    def update_product(input_data):

        sql = """
            UPDATE record
            SET amount = %s,
                total = %s
            WHERE pid = %s AND tno = %s
        """

        DB.execute_input(sql, (
            input_data['amount'],
            input_data['total'],
            input_data['pid'],
            input_data['tno']
        ))

    @staticmethod
    def delete_check(pid):

        sql = """
            SELECT *
            FROM record
            WHERE pid = %s
        """

        return DB.fetchone(sql, (pid,))

    @staticmethod
    def get_total(tno):

        sql = """
            SELECT SUM(total)
            FROM record
            WHERE tno = %s
        """

        return DB.fetchone(sql, (tno,))[0]


# ==========================================
# 原始書店系統：訂單
# ==========================================

class Order_List:

    @staticmethod
    def add_order(input_data):

        sql = """
            INSERT INTO order_list
            (oid, mid, ordertime, price, tno)
            VALUES (
                DEFAULT,
                %s,
                TO_TIMESTAMP(%s, %s),
                %s,
                %s
            )
        """

        DB.execute_input(sql, (
            input_data['mid'],
            input_data['ordertime'],
            input_data['format'],
            input_data['total'],
            input_data['tno']
        ))

    @staticmethod
    def get_order():

        sql = """
            SELECT
                o.oid,
                m.name,
                o.price,
                o.ordertime
            FROM order_list o
            NATURAL JOIN member m
            ORDER BY o.ordertime DESC
        """

        return DB.fetchall(sql)

    @staticmethod
    def get_orderdetail():

        sql = """
            SELECT
                o.oid,
                p.pname,
                r.saleprice,
                r.amount
            FROM order_list o
            JOIN record r
                ON o.tno = r.tno
            JOIN product p
                ON r.pid = p.pid
        """

        return DB.fetchall(sql)


# ==========================================
# 原始書店系統：統計分析
# ==========================================

class Analysis:

    @staticmethod
    def month_price(i):

        sql = """
            SELECT
                EXTRACT(MONTH FROM ordertime),
                SUM(price)
            FROM order_list
            WHERE EXTRACT(MONTH FROM ordertime) = %s
            GROUP BY EXTRACT(MONTH FROM ordertime)
        """

        return DB.fetchall(sql, (i,))

    @staticmethod
    def month_count(i):

        sql = """
            SELECT
                EXTRACT(MONTH FROM ordertime),
                COUNT(oid)
            FROM order_list
            WHERE EXTRACT(MONTH FROM ordertime) = %s
            GROUP BY EXTRACT(MONTH FROM ordertime)
        """

        return DB.fetchall(sql, (i,))

    @staticmethod
    def category_sale():

        sql = """
            SELECT
                SUM(total),
                category
            FROM product, record
            WHERE product.pid = record.pid
            GROUP BY category
        """

        return DB.fetchall(sql)

    @staticmethod
    def member_sale():

        sql = """
            SELECT
                SUM(price),
                member.mid,
                member.name
            FROM order_list, member
            WHERE order_list.mid = member.mid
              AND member.identity = %s
            GROUP BY member.mid, member.name
            ORDER BY SUM(price) DESC
        """

        return DB.fetchall(sql, ('user',))

    @staticmethod
    def member_sale_count():

        sql = """
            SELECT
                COUNT(*),
                member.mid,
                member.name
            FROM order_list, member
            WHERE order_list.mid = member.mid
              AND member.identity = %s
            GROUP BY member.mid, member.name
            ORDER BY COUNT(*) DESC
        """

        return DB.fetchall(sql, ('user',))
