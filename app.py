from flask import Flask, jsonify
from flask_cors import CORS
import mysql.connector
import os

app = Flask(__name__)
CORS(app)


# =========================
# MySQL 連線
# =========================

def get_connection():

    return mysql.connector.connect(
        host=os.environ.get("MYSQL_HOST"),
        port=int(os.environ.get("MYSQL_PORT", 3306)),
        user=os.environ.get("MYSQL_USER"),
        password=os.environ.get("MYSQL_PASSWORD"),
        database=os.environ.get("MYSQL_DATABASE"),
        ssl_disabled=False
    )


# =========================
# 首頁測試
# =========================

@app.route("/")
def home():

    return "Sales Dashboard API is running!"


# =========================
# Dashboard API
# =========================

@app.route("/api/dashboard")
def dashboard():
    @app.route("/api/set-table/<table_name>", methods=["GET"])
def set_table(table_name):

    allowed_tables = [
        "sales_original_300",
        "sales_updated_300"
    ]

    if table_name not in allowed_tables:
        return jsonify({
            "error": "不允許的資料表"
        }), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales_config (
                id INT PRIMARY KEY,
                active_table VARCHAR(100) NOT NULL
            )
        """)

        cursor.execute("""
            INSERT INTO sales_config (id, active_table)
            VALUES (1, %s)
            ON DUPLICATE KEY UPDATE
            active_table = %s
        """, (table_name, table_name))

        conn.commit()

        return jsonify({
            "success": True,
            "table_name": table_name
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        conn.close()

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        # --------------------------------
        # 找目前使用的資料表
        # --------------------------------

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales_config (
                id INT PRIMARY KEY,
                active_table VARCHAR(100) NOT NULL
            )
        """)

        cursor.execute("""
            SELECT active_table
            FROM sales_config
            WHERE id = 1
        """)

        config = cursor.fetchone()

        # 如果還沒有設定，預設使用 original
        if config is None:

            active_table = "sales_original_300"

            cursor.execute("""
                INSERT INTO sales_config (id, active_table)
                VALUES (1, %s)
            """, (active_table,))

            conn.commit()

        else:

            active_table = config["active_table"]


        # --------------------------------
        # 安全限制
        # --------------------------------

        allowed_tables = [
            "sales_original_300",
            "sales_updated_300"
        ]

        if active_table not in allowed_tables:

            active_table = "sales_original_300"


        # --------------------------------
        # 基本資料
        # --------------------------------

        cursor.execute(f"""
            SELECT
                COUNT(*) AS total_records,
                SUM(unit_price * (quantity - returned_quantity)) AS total_sales,
                SUM(quantity) AS total_quantity,
                SUM(returned_quantity) AS total_returned
            FROM `{active_table}`
        """)

        summary = cursor.fetchone()


        # --------------------------------
        # 每日銷售
        # --------------------------------

        cursor.execute(f"""
            SELECT
                sale_date,
                SUM(
                    unit_price *
                    (quantity - returned_quantity)
                ) AS net_sales
            FROM `{active_table}`
            GROUP BY sale_date
            ORDER BY sale_date
        """)

        daily = cursor.fetchall()


        # --------------------------------
        # 商品銷售
        # --------------------------------

        cursor.execute(f"""
            SELECT
                product_name,
                SUM(
                    unit_price *
                    (quantity - returned_quantity)
                ) AS net_sales
            FROM `{active_table}`
            GROUP BY product_name
            ORDER BY net_sales DESC
        """)

        product = cursor.fetchall()


        # --------------------------------
        # 分類銷售
        # --------------------------------

        cursor.execute(f"""
            SELECT
                category,
                SUM(
                    unit_price *
                    (quantity - returned_quantity)
                ) AS net_sales
            FROM `{active_table}`
            GROUP BY category
            ORDER BY net_sales DESC
        """)

        category = cursor.fetchall()


        # --------------------------------
        # 通路銷售
        # --------------------------------

        cursor.execute(f"""
            SELECT
                channel,
                SUM(
                    unit_price *
                    (quantity - returned_quantity)
                ) AS net_sales
            FROM `{active_table}`
            GROUP BY channel
            ORDER BY net_sales DESC
        """)

        channel = cursor.fetchall()


        # --------------------------------
        # 日期轉成文字
        # --------------------------------

        for row in daily:

            row["sale_date"] = str(row["sale_date"])


        # --------------------------------
        # 數字處理
        # --------------------------------

        for row in daily:
            row["net_sales"] = float(row["net_sales"] or 0)

        for row in product:
            row["net_sales"] = float(row["net_sales"] or 0)

        for row in category:
            row["net_sales"] = float(row["net_sales"] or 0)

        for row in channel:
            row["net_sales"] = float(row["net_sales"] or 0)


        summary["total_sales"] = float(
            summary["total_sales"] or 0
        )

        summary["total_quantity"] = int(
            summary["total_quantity"] or 0
        )

        summary["total_returned"] = int(
            summary["total_returned"] or 0
        )

        summary["total_records"] = int(
            summary["total_records"] or 0
        )


        # --------------------------------
        # 回傳 JSON
        # --------------------------------

        return jsonify({

            "table_name": active_table,

            "summary": summary,

            "daily": daily,

            "product": product,

            "category": category,

            "channel": channel

        })


    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


    finally:

        cursor.close()
        conn.close()


# =========================
# 啟動 Flask
# =========================

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port
    )
