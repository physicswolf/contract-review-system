from flask import Blueprint, request, jsonify
from db import get_conn, ok, err

bp = Blueprint("dimension", __name__)


@bp.route("/dimensions", methods=["GET"])
def list_dimensions():
    enabled = request.args.get("enabled")
    sql = "SELECT id, name, description, sort_order, enabled, updated_at FROM dimension"
    params = []
    if enabled is not None:
        sql += " WHERE enabled = %s"
        params.append(int(enabled))
    sql += " ORDER BY sort_order, id"
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        for r in rows:
            if r.get("updated_at"):
                r["updatedAt"] = r.pop("updated_at").isoformat()
            r["sortOrder"] = r.pop("sort_order")
        return jsonify(ok(rows))
    finally:
        conn.close()


@bp.route("/dimensions", methods=["POST"])
def create_dimension():
    body = request.get_json() or {}
    name = (body.get("name") or "").strip()
    if not name:
        return jsonify(err(40001, "name 不能为空")[0]), 400
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "INSERT INTO dimension (name, description, sort_order, enabled) VALUES (%s,%s,%s,%s)",
                    (name, body.get("description"), body.get("sortOrder", 0), body.get("enabled", 1)),
                )
                conn.commit()
                return jsonify(ok({"id": cur.lastrowid}))
            except Exception as e:
                conn.rollback()
                if "Duplicate" in str(e):
                    return jsonify(err(40901, "维度名称已存在")[0]), 409
                raise
    finally:
        conn.close()


@bp.route("/dimensions/<int:dim_id>", methods=["PUT"])
def update_dimension(dim_id):
    body = request.get_json() or {}
    fields, vals = [], []
    for col, key in [("name", "name"), ("description", "description"), ("sort_order", "sortOrder"), ("enabled", "enabled")]:
        if key in body:
            fields.append(f"{col}=%s")
            vals.append(body[key])
    if not fields:
        return jsonify(ok())
    vals.append(dim_id)
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute(f"UPDATE dimension SET {','.join(fields)} WHERE id=%s", vals)
                conn.commit()
                return jsonify(ok())
            except Exception as e:
                conn.rollback()
                if "Duplicate" in str(e):
                    return jsonify(err(40901, "维度名称已存在")[0]), 409
                raise
    finally:
        conn.close()


@bp.route("/dimensions/<int:dim_id>", methods=["DELETE"])
def delete_dimension(dim_id):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS cnt FROM audit_point WHERE dim_id=%s AND deleted_at IS NULL", (dim_id,))
            cnt = cur.fetchone()["cnt"]
            if cnt:
                return jsonify(err(40901, f"该维度下存在 {cnt} 个审查点，请先删除或迁移后再操作")[0]), 409
            cur.execute("DELETE FROM dimension WHERE id=%s", (dim_id,))
            conn.commit()
            return jsonify(ok())
    finally:
        conn.close()
