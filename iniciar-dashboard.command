#!/bin/bash
cd "$(dirname "$0")"

# Mata qualquer servidor anterior na porta 8741
lsof -ti:8741 | xargs kill -9 2>/dev/null

# Inicia o servidor em background
python3 -m http.server 8741 &
SERVER_PID=$!

# Aguarda o servidor subir
sleep 1

# Abre no Chrome (necessário para sincronização com pCloud)
if open -a "Google Chrome" "http://localhost:8741/dashboard-hematologia-v2.html" 2>/dev/null; then
  echo "Dashboard aberto no Chrome."
else
  # Fallback: abre no navegador padrão
  open "http://localhost:8741/dashboard-hematologia-v2.html"
  echo "AVISO: Use Google Chrome para que a sincronização com pCloud funcione."
fi

echo "Servidor rodando (PID $SERVER_PID). Feche esta janela para encerrar."
wait $SERVER_PID
