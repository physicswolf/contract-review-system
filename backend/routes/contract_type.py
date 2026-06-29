import json
from flask import Blueprint, request, jsonify
from db import get_conn, ok, err, _parse_json_fields

bp = Blueprint("contract_type", __name__)


@bp.route("/contract-types", methods=["GET"])
def list_contract_types():
    enabled = request.args.get("enabled")
    keyword = request.args.get("keyword")
    sql = """
        SELECT ct.id, ct.code, ct.name, ct.stance, ct.description, ct.enabled,
               COUNT(ctap.id) AS linked_point_count
        FROM contract_type ct
        LEFT JOIN contract_type_audit_point ctap ON ctap.contract_type_id=ct.id
        WHERE ct.deleted_at IS NULL
    """
    params = []
    if enabled is not None:
        sql += " AND ct.enabled=%s"
        params.append(int(enabled))
    if keyword:
        sql += " AND (ct.name LIKE %s OR ct.code LIKE %s)"
        params += [f"%{keyword}%", f"%{keyword}%"]
    sql += " GROUP BY ct.id ORDER BY ct.id"
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        for r in rows:
            r["linkedPointCount"] = r.pop("linked_point_count")
        return jsonify(ok(rows))
    finally:
        conn.close()


@bp.route("/contract-types", methods=["POST"])
def create_contract_type():
    body = request.get_json() or {}
    name = (body.get("name") or "").strip()
    stance = (body.get("stance") or "").strip()
    if not name or not stance:
        return jsonify(err(40001, "name 和 stance 不能为空")[0]), 400
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "INSERT INTO contract_type (code, name, stance, description, keywords, enabled) VALUES (%s,%s,%s,%s,%s,%s)",
                    (
                        body.get("code"), name, stance, body.get("description"),
                        json.dumps(body["keywords"], ensure_ascii=False) if body.get("keywords") is not None else None,
                        body.get("enabled", 1),
                    ),
                )
                conn.commit()
                return jsonify(ok({"id": cur.lastrowid}))
            except Exception as e:
                conn.rollback()
                if "Duplicate" in str(e):
                    return jsonify(err(40901, "该合同类型-立场已存在")[0]), 409
                raise
    finally:
        conn.close()


@bp.route("/contract-types/<int:ct_id>", methods=["GET"])
def get_contract_type(ct_id):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM contract_type WHERE id=%s AND deleted_at IS NULL", (ct_id,)
            )
            row = cur.fetchone()
            if not row:
                return jsonify(err(40401, "合同类型不存在")[0]), 404
            _parse_json_fields(row, ["keywords"])
            cur.execute(
                "SELECT audit_point_id, enabled FROM contract_type_audit_point WHERE contract_type_id=%s",
                (ct_id,),
            )
            linked = [{"auditPointId": r["audit_point_id"], "enabled": r["enabled"]} for r in cur.fetchall()]
        return jsonify(ok({
            "id": row["id"], "code": row["code"], "name": row["name"],
            "stance": row["stance"], "description": row["description"],
            "keywords": row.get("keywords"), "enabled": row["enabled"],
            "linkedAuditPoints": linked,
        }))
    finally:
        conn.close()


@bp.route("/contract-types/<int:ct_id>", methods=["PUT"])
def update_contract_type(ct_id):
    body = request.get_json() or {}
    fields, vals = [], []
    for col, key in [("code", "code"), ("name", "name"), ("stance", "stance"),
                     ("description", "description"), ("enabled", "enabled")]:
        if key in body:
            fields.append(f"{col}=%s")
            vals.append(body[key])
    if "keywords" in body:
        fields.append("keywords=%s")
        vals.append(json.dumps(body["keywords"], ensure_ascii=False) if body["keywords"] is not None else None)
    if not fields:
        return jsonify(ok())
    vals.append(ct_id)
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    f"UPDATE contract_type SET {','.join(fields)} WHERE id=%s AND deleted_at IS NULL", vals
                )
                conn.commit()
                return jsonify(ok())
            except Exception as e:
                conn.rollback()
                if "Duplicate" in str(e):
                    return jsonify(err(40901, "该合同类型-立场已存在")[0]), 409
                raise
    finally:
        conn.close()


@bp.route("/contract-types/<int:ct_id>", methods=["DELETE"])
def delete_contract_type(ct_id):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE contract_type SET deleted_at=NOW() WHERE id=%s AND deleted_at IS NULL", (ct_id,))
            cur.execute("DELETE FROM contract_type_audit_point WHERE contract_type_id=%s", (ct_id,))
            conn.commit()
            return jsonify(ok())
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@bp.route("/contract-types/<int:ct_id>/audit-points", methods=["PUT"])
def save_audit_points(ct_id):
    body = request.get_json() or {}
    ids = body.get("auditPointIds", [])
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM contract_type_audit_point WHERE contract_type_id=%s", (ct_id,))
            if ids:
                vals = [(ct_id, ap_id, i, 1) for i, ap_id in enumerate(ids)]
                cur.executemany(
                    "INSERT INTO contract_type_audit_point (contract_type_id, audit_point_id, sort_order, enabled) VALUES (%s,%s,%s,%s)",
                    vals,
                )
            conn.commit()
            return jsonify(ok())
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@bp.route("/contract-types/<int:ct_id>/audit-points/<int:ap_id>/enabled", methods=["PATCH"])
def toggle_ct_audit_point(ct_id, ap_id):
    body = request.get_json() or {}
    if "enabled" not in body:
        return jsonify(err(40001, "enabled 不能为空")[0]), 400
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE contract_type_audit_point SET enabled=%s WHERE contract_type_id=%s AND audit_point_id=%s",
                (body["enabled"], ct_id, ap_id),
            )
            conn.commit()
            return jsonify(ok())
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
