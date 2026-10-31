"""Public native-extraction demo, separate from the protected automation worker."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException, RequestEntityTooLarge

from web_demo import service

ROOT = Path(__file__).resolve().parent


def create_app() -> Flask:
    app = Flask(__name__, template_folder=str(ROOT / "web_demo" / "templates"),
                static_folder=str(ROOT / "web_demo" / "static"))
    app.config.update(MAX_CONTENT_LENGTH=service.MAX_FILE_BYTES + 64 * 1024,
                      MAX_FORM_MEMORY_SIZE=128 * 1024, MAX_FORM_PARTS=6)

    @app.before_request
    def reject_cross_site():
        if request.method not in {"POST", "PUT", "DELETE", "PATCH"}:
            return None
        if request.headers.get("Sec-Fetch-Site") == "cross-site":
            raise service.DemoError("foreign_origin", "Origine de la requête refusée.", 403)
        origin = request.headers.get("Origin")
        if origin:
            try:
                parsed = urlsplit(origin)
            except ValueError:
                raise service.DemoError("foreign_origin", "Origine de la requête refusée.", 403) from None
            schemes = {request.scheme}
            if os.environ.get("VERCEL"):
                schemes.add("https")
            if (parsed.scheme not in schemes or parsed.netloc.lower() != request.host.lower()
                    or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password):
                raise service.DemoError("foreign_origin", "Origine de la requête refusée.", 403)

    @app.after_request
    def private_headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'; object-src 'none'"
        return response

    @app.errorhandler(service.DemoError)
    def demo_error(error):
        return jsonify(error=error.code, message=error.message), error.status

    @app.errorhandler(RequestEntityTooLarge)
    def too_large(_error):
        return jsonify(error="file_size", message="La requête dépasse la limite autorisée de 2 Mio par fichier."), 413

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error="invalid_request", message="Requête non prise en charge."), error.code

    @app.errorhandler(Exception)
    def unexpected_error(_error):
        # Do not log exceptions containing an uploaded document or its paths.
        return jsonify(error="service_unavailable", message="Le service est temporairement indisponible."), 503

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/capabilities")
    @app.get("/health")
    def capabilities():
        return jsonify(service.capabilities())

    @app.post("/api/process")
    def process():
        if request.mimetype != "multipart/form-data":
            raise service.DemoError("invalid_request", "Utilisez un formulaire multipart.", 415)
        if any(len(request.form.getlist(key)) != 1 for key in request.form) or any(len(request.files.getlist(key)) != 1 for key in request.files):
            raise service.DemoError("invalid_request", "Champs en double refusés.", 400)
        if set(request.form) - {"sample", "keywords"} or set(request.files) - {"file"}:
            raise service.DemoError("invalid_request", "Champ non pris en charge.", 400)
        sample = request.form.get("sample") or None
        file = request.files.get("file")
        if (file is None) == (sample is None):
            raise service.DemoError("invalid_request", "Choisissez un fichier ou un exemple.", 400)
        keywords = service.parse_keywords(request.form.get("keywords"))
        if sample is not None:
            return jsonify(service.process_document(sample=sample, keywords=keywords))
        name, document_type = service.validate_upload_name(file.filename, file.mimetype)
        body = file.stream.read(service.MAX_FILE_BYTES + 1)
        return jsonify(service.process_document(body=body, name=name, document_type=document_type, keywords=keywords))

    @app.post("/api/decision")
    def decision():
        if not request.is_json:
            raise service.DemoError("invalid_request", "Utilisez un objet JSON.", 415)
        return jsonify(service.manual_decision(request.get_json(silent=True)))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5182, debug=False)
