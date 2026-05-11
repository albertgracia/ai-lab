Pendiente: implementar failover real por request.
No basta con /v1/models online; hay que probar /v1/chat/completions y saltar de nodo si devuelve 500 o HTML.

Estado actual:
- Main LM Studio: ONLINE y funcional
- RX9070XT LM Studio: online en /v1/models pero falla /v1/chat/completions
- RX7900XT: offline
- Router priorizado temporalmente a Main LM Studio
- Pendiente: failover real por request y reparación LM Studio RX9070XT

- Failover real por request
- Detectar upstream inválido HTML/500
- Auto fallback nodo siguiente
- Health scoring por LM Studio