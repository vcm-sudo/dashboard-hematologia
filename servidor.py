#!/usr/bin/env python3
"""Servidor local do Dashboard Hemato.

Faz duas coisas:
  1) serve os arquivos estáticos (HTML, vendor/, etc.) como o `python3 -m http.server`;
  2) expõe POST /extrair-agenda, que recebe UMA imagem (base64 JPEG vinda do navegador),
     salva num arquivo temporário e chama o Claude Code CLI (`claude`) pela ASSINATURA
     — sem usar a API por token — para extrair os pacientes do print da agenda.

Mesmo padrão do lab_transcribe.py: a ANTHROPIC_API_KEY é removida do ambiente de
propósito, forçando o login da assinatura (Max/Pro) e evitando cobrança por token.

Requisitos: `claude` (Claude Code CLI) instalado e logado. Rode `claude` uma vez e autentique.
"""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import base64
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

PORT = 8741
CLI_MODEL = "claude-sonnet-4-6"
TIMEOUT = 180  # segundos por imagem

# Serve a partir da pasta onde este script está (a do dashboard).
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def hoje() -> str:
    return datetime.date.today().isoformat()


def build_prompt(caminho_img: str) -> str:
    return (
        f"Leia a imagem em {caminho_img}. É uma print de uma agenda médica hospitalar.\n"
        "Extraia TODOS os nomes de pacientes visíveis (ignore linhas como \"FECHOU HORARIO\", "
        "\"REUNIAO\" ou bloqueios de agenda).\n"
        "Para cada paciente, extraia o que for visível: nome completo, número de prontuário "
        "(se aparecer antes do nome), número de atendimento, horário.\n"
        f"A data de hoje é {hoje()}.\n\n"
        "Retorne APENAS um array JSON válido, sem markdown, sem explicação. Formato exato:\n"
        "[\n"
        "  {\n"
        "    \"nome\": \"NOME COMPLETO DO PACIENTE\",\n"
        "    \"prontuario\": \"123456\",\n"
        "    \"atendimento\": \"7037268\",\n"
        f"    \"data\": \"{hoje()}\",\n"
        "    \"hora\": \"09:00\"\n"
        "  }\n"
        "]\n"
        "Se algum campo não for visível, omita-o ou use null. Retorne só o JSON, nada mais."
    )


def call_claude(caminho_img: str) -> list:
    """Chama o CLI `claude` (assinatura) para extrair os pacientes da imagem."""
    if shutil.which("claude") is None:
        raise RuntimeError(
            "CLI 'claude' (Claude Code) não encontrado no PATH. "
            "Instale e faça login uma vez: rode `claude` e autentique."
        )

    # Remove a key da API: força o login da assinatura (evita cobrança por token).
    env = {k: v for k, v in os.environ.items()
           if k not in ("ANTHROPIC_API_KEY", "CLAUDECODE")}

    cmd = ["claude", "-p", build_prompt(caminho_img),
           "--allowedTools", "Read",
           "--model", CLI_MODEL]

    proc = subprocess.run(
        cmd, env=env, stdin=subprocess.DEVNULL,
        capture_output=True, text=True, timeout=TIMEOUT,
    )
    if proc.returncode != 0:
        err = (proc.stderr or "").strip().splitlines()
        raise RuntimeError(
            "O CLI 'claude' falhou (exit %d). %s "
            "Verifique se o `claude` está logado (rode `claude` e autentique)."
            % (proc.returncode, (err[-1][:300] if err else ""))
        )

    texto = (proc.stdout or "").strip()
    # Remove cercas de markdown, se vierem.
    texto = re.sub(r"```json|```", "", texto).strip()
    # Se vier algo antes/depois, isola o primeiro array JSON.
    if not texto.startswith("["):
        m = re.search(r"\[.*\]", texto, re.DOTALL)
        if m:
            texto = m.group(0)
    dados = json.loads(texto)
    if not isinstance(dados, list):
        raise ValueError("A resposta não é um array JSON.")
    return dados


class Handler(SimpleHTTPRequestHandler):
    # Silencia o log de cada GET de arquivo estático (mantém erros).
    def log_message(self, fmt, *args):
        if "extrair-agenda" in (self.path or ""):
            super().log_message(fmt, *args)

    def do_POST(self):
        if self.path != "/extrair-agenda":
            self.send_error(404, "Not found")
            return

        tmp_path = None
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            payload = json.loads(body)
            b64 = payload.get("b64") or payload.get("data")
            media = payload.get("mediaType") or payload.get("mt") or "image/jpeg"
            if not b64:
                raise ValueError("payload sem 'b64'")

            ext = ".png" if "png" in media else ".jpg"
            fd, tmp_path = tempfile.mkstemp(suffix=ext, prefix="agenda_")
            with os.fdopen(fd, "wb") as f:
                f.write(base64.b64decode(b64))

            pacientes = call_claude(tmp_path)
            self._send_json(200, {"pacientes": pacientes})
        except subprocess.TimeoutExpired:
            self._send_json(504, {"error": "Timeout (%ds) ao extrair com o Claude." % TIMEOUT})
        except Exception as e:  # noqa: BLE001
            self._send_json(500, {"error": str(e)})
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def _send_json(self, code: int, obj: dict):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    if shutil.which("claude") is None:
        print("⚠️  Aviso: CLI 'claude' não encontrado no PATH — a extração de agenda vai falhar.")
        print("   Instale o Claude Code e faça login (rode `claude` e autentique).\n")
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Dashboard Hemato rodando em http://localhost:{PORT}/dashboard-hematologia-v2.html")
    print("Extração de agenda: Claude Code CLI (assinatura). Ctrl+C para encerrar.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando…")
        server.shutdown()


if __name__ == "__main__":
    sys.exit(main())
