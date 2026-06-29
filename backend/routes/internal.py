from flask import Blueprint, request, jsonify
from db import get_conn, ok, err, _parse_json_fields

bp = Blueprint("internal", __name__)
_JSON_FIELDS = ["risk_points", "examples", "default_result"]


@bp.route("/internal/contract-types/match", methods=["GET"])
def match_contract_type():
    name = request.args.get("name", "").strip()
    stance = request.args.get("stance", "").strip()
    if not name or not stance:
        return jsonify(err(40001, "name 和 stance 不能为空")[0]), 400
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, code, name, stance, keywords FROM contract_type WHERE name=%s AND stance=%s AND enabled=1 AND deleted_at IS NULL",
                (name, stance),
            )
            row = cur.fetchone()
        if not row:
            return jsonify(err(40401, "合同类型不存在")[0]), 404
        _parse_json_fields(row, ["keywords"])
        return jsonify(ok(row))
    finally:
        conn.close()


@bp.route("/internal/contract-types/<int:ct_id>/audit-points", methods=["GET"])
def load_audit_points(ct_id):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT ap.id, ap.name, ap.instruction, ap.risk_points, ap.examples, ap.default_result
                   FROM contract_type_audit_point ctap
                   JOIN audit_point ap ON ap.id=ctap.audit_point_id
                   WHERE ctap.contract_type_id=%s AND ctap.enabled=1 AND ap.enabled=1 AND ap.deleted_at IS NULL
                   ORDER BY ctap.sort_order""",
                (ct_id,),
            )
            rows = cur.fetchall()
        for r in rows:
            _parse_json_fields(r, ["risk_points", "examples", "default_result"])
            r["riskPoints"] = r.pop("risk_points")
            r["defaultResult"] = r.pop("default_result")
        return jsonify(ok(rows))
    finally:
        conn.close()
