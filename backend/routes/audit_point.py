import json
from flask import Blueprint, request, jsonify
from db import get_conn, ok, err, _parse_json_fields

bp = Blueprint("audit_point", __name__)
_JSON_FIELDS = ["risk_points", "examples", "default_result"]


@bp.route("/audit-points", methods=["GET"])
def list_audit_points():
    dim_id = request.args.get("dimId")
    keyword = request.args.get("keyword")
    enabled = request.args.get("enabled")
    sql = """
        SELECT ap.id, ap.name, ap.description, ap.dim_id, d.name AS dim_name,
               ap.risk_points, ap.enabled, ap.updated_at
        FROM audit_point ap
        JOIN dimension d ON d.id = ap.dim_id
        WHERE ap.deleted_at IS NULL
    """
    params = []
    if dim_id:
        sql += " AND ap.dim_id=%s"
        params.append(int(dim_id))
    if keyword:
        sql += " AND ap.name LIKE %s"
        params.append(f"%{keyword}%")
    if enabled is not None:
        sql += " AND ap.enabled=%s"
        params.append(int(enabled))
    sql += " ORDER BY ap.sort_order, ap.id"
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        result = []
        for r in rows:
            rp = r.get("risk_points")
            if isinstance(rp, str):
                try:
                    rp = json.loads(rp)
                except Exception:
                    rp = []
            names = [x.get("name") for x in (rp or []) if isinstance(x, dict) and x.get("name")]
            result.append({
                "id": r["id"], "name": r["name"], "description": r["description"],
                "dimId": r["dim_id"], "dimName": r["dim_name"],
                "riskPoints": names, "enabled": r["enabled"],
                "updatedAt": r["updated_at"].isoformat() if r.get("updated_at") else None,
            })
        return jsonify(ok(result))
    finally:
        conn.close()


@bp.route("/audit-points", methods=["POST"])
def create_audit_point():
    body = request.get_json() or {}
    if not body.get("dimId") or not (body.get("name") or "").strip():
        return jsonify(err(40001, "dimId 和 name 不能为空")[0]), 400
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO audit_point
                   (dim_id, name, description, instruction, risk_points, examples, default_result, enabled, sort_order)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    body["dimId"], body["name"].strip(), body.get("description"),
                    body.get("instruction"),
                    json.dumps(body["riskPoints"], ensure_ascii=False) if body.get("riskPoints") is not None else None,
                    json.dumps(body["examples"], ensure_ascii=False) if body.get("examples") is not None else None,
                    json.dumps(body["defaultResult"], ensure_ascii=False) if body.get("defaultResult") is not None else None,
                    body.get("enabled", 1), body.get("sortOrder", 0),
                ),
            )
            conn.commit()
            return jsonify(ok({"id": cur.lastrowid}))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@bp.route("/audit-points/<int:ap_id>", methods=["GET"])
def get_audit_point(ap_id):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT ap.*, d.name AS dim_name FROM audit_point ap
                   JOIN dimension d ON d.id=ap.dim_id
                   WHERE ap.id=%s AND ap.deleted_at IS NULL""",
                (ap_id,),
            )
            row = cur.fetchone()
        if not row:
            return jsonify(err(40401, "审查点不存在")[0]), 404
        _parse_json_fields(row, _JSON_FIELDS)
        return jsonify(ok({
            "id": row["id"], "dimId": row["dim_id"], "dimName": row["dim_name"],
            "name": row["name"], "description": row["description"], "instruction": row["instruction"],
            "riskPoints": row.get("risk_points"), "examples": row.get("examples"),
            "defaultResult": row.get("default_result"), "enabled": row["enabled"],
            "updatedAt": row["updated_at"].isoformat() if row.get("updated_at") else None,
        }))
    finally:
        conn.close()


@bp.route("/audit-points/<int:ap_id>", methods=["PUT"])
def update_audit_point(ap_id):
    body = request.get_json() or {}
    fields, vals = [], []
    simple = [("dim_id", "dimId"), ("name", "name"), ("description", "description"),
              ("instruction", "instruction"), ("enabled", "enabled"), ("sort_order", "sortOrder")]
    for col, key in simple:
        if key in body:
            fields.append(f"{col}=%s")
            vals.append(body[key])
    for col, key in [("risk_points", "riskPoints"), ("examples", "examples"), ("default_result", "defaultResult")]:
        if key in body:
            fields.append(f"{col}=%s")
            vals.append(json.dumps(body[key], ensure_ascii=False) if body[key] is not None else None)
    if not fields:
        return jsonify(ok())
    vals.append(ap_id)
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE audit_point SET {','.join(fields)} WHERE id=%s AND deleted_at IS NULL", vals)
            conn.commit()
            return jsonify(ok())
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@bp.route("/audit-points/<int:ap_id>/enabled", methods=["PATCH"])
def toggle_audit_point(ap_id):
    body = request.get_json() or {}
    if "enabled" not in body:
        return jsonify(err(40001, "enabled 不能为空")[0]), 400
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE audit_point SET enabled=%s WHERE id=%s AND deleted_at IS NULL", (body["enabled"], ap_id))
            conn.commit()
            return jsonify(ok())
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@bp.route("/audit-points/<int:ap_id>", methods=["DELETE"])
def delete_audit_point(ap_id):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE audit_point SET deleted_at=NOW() WHERE id=%s AND deleted_at IS NULL", (ap_id,))
            conn.commit()
            return jsonify(ok())
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
