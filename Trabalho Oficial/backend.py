import os
import io
import re
from flask import Flask, request, jsonify, send_file
from pytubefix import YouTube

app = Flask(__name__)

def safe_filename(s: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", s)

@app.route("/")
def home():
    return send_file(os.path.join(os.path.dirname(__file__), "index.html"))

@app.route("/info", methods=["GET"])
def get_info():
    video_url = request.args.get("url")
    if not video_url:
        return jsonify({"error": "URL é obrigatória"}), 400

    try:
        yt = YouTube(video_url)
    except Exception as exc:
        return jsonify({"error": "Falha ao carregar informações do YouTube", "detail": str(exc)}), 400

    streams = []
    try:
        for stream in yt.streams.order_by("resolution").desc():
            try:
                # filesize pode não estar disponível; usa approx como fallback
                size_bytes = getattr(stream, "filesize", None)
                if not size_bytes:
                    size_bytes = getattr(stream, "filesize_approx", None)
                tamanho_mb = round((size_bytes or 0) / (1024 * 1024), 2)
            except Exception:
                tamanho_mb = 0

            resolucao_val = stream.resolution if getattr(stream, "resolution", None) else "N/A"
            streams.append({
                "itag": stream.itag,
                "resolução": resolucao_val,
                "resolucao": resolucao_val,  # chave ASCII para compatibilidade no frontend
                "resolution": resolucao_val,  # chave em inglês para fallback
                "fps": stream.fps if getattr(stream, "fps", None) else "N/A",
                "tamanho_MB": tamanho_mb,
                "tem_audio": bool(getattr(stream, "includes_audio_track", False)),
                "progressivo": bool(getattr(stream, "is_progressive", False)),
                "mime": getattr(stream, "mime_type", "")
            })
    except Exception as exc:
        return jsonify({"error": "Falha ao listar streams", "detail": str(exc)}), 500

    return jsonify({
        "title": yt.title,
        "author": yt.author,
        "length": yt.length,
        "views": yt.views,
        "thumbnail": yt.thumbnail_url,
        "streams": streams
    })

@app.route("/download", methods=["GET"])
def download_video():
    video_url = request.args.get("url")
    itag = request.args.get("itag")
    inline = request.args.get("inline") in ("1", "true", "True")

    if not video_url or not itag:
        return jsonify({"error": "URL e itag são obrigatórios"}), 400

    try:
        yt = YouTube(video_url)
        stream = yt.streams.get_by_itag(int(itag))
        if stream is None:
            return jsonify({"error": "Stream não encontrado"}), 404

        # Se o stream escolhido não tiver áudio, pega um progressive (vídeo+áudio)
        if not getattr(stream, "includes_audio_track", False) or not getattr(stream, "is_progressive", False):
            target_res = getattr(stream, "resolution", None)
            candidate = yt.streams.filter(progressive=True, resolution=target_res).first()
            if not candidate:
                candidate = yt.streams.filter(progressive=True).order_by("resolution").desc().first()
            stream = candidate
            if stream is None:
                return jsonify({"error": "Nenhum stream progressive disponível"}), 404

        buffer = io.BytesIO()
        stream.stream_to_buffer(buffer)
        buffer.seek(0)
    except Exception as exc:
        return jsonify({"error": "Falha ao preparar stream", "detail": str(exc)}), 500

    filename = safe_filename(yt.title) + ".mp4"
    return send_file(
        buffer,
        as_attachment=not inline,
        download_name=filename,
        mimetype="video/mp4"
    )

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
