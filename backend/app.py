from flask import Flask, jsonify, request
from routes.dimension import bp as dim_bp
from routes.audit_point import bp as ap_bp
from routes.contract_type import bp as ct_bp
from routes.internal import bp as internal_bp

app = Flask(__name__)

@app.after_request
def cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = request.headers.get("Origin", "*")
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
    return resp

@app.route("/api/v1/config/auth/login", methods=["POST", "OPTIONS"])
def auth_login():
    if request.method == "OPTIONS":
        return "", 204
    return jsonify({"code": 0, "data": {"token": "dev-token", "user": {"name": "管理员", "account": "admin@dev"}}})

@app.route("/api/v1/config/auth/profile", methods=["GET"])
def auth_profile():
    return jsonify({"code": 0, "data": {"name": "管理员", "account": "admin@dev"}})


prefix = "/api/v1/config"
app.register_blueprint(dim_bp, url_prefix=prefix)
app.register_blueprint(ap_bp, url_prefix=prefix)
app.register_blueprint(ct_bp, url_prefix=prefix)
app.register_blueprint(internal_bp, url_prefix=prefix)


@app.errorhandler(404)
def not_found(e):
    return jsonify({"code": 40401, "msg": str(e)}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"code": 40501, "msg": str(e)}), 405

@app.errorhandler(Exception)
def handle_error(e):
    app.logger.exception(e)
    return jsonify({"code": 50001, "msg": "内部服务错误"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
