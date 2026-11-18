---
title: HogarTec Agente WhatsApp
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8080
pinned: false
short_description: Agente de compra y postventa por WhatsApp (LangGraph + Gemini)
---

# HogarTec: agente de compra y postventa por WhatsApp

Backend del agente conversacional: webhook de WhatsApp Cloud API, agente LangGraph con RAG
y function calling, y una API de comercio simulada con la forma de VTEX.

- `GET /health`: estado del servicio
- `POST /webhook`: mensajes de WhatsApp (requiere firma de Meta)
- `/commerce/api/...`: API de comercio simulada

Código, arquitectura y evaluaciones: https://github.com/JulioPradenas/agente-comercio-whatsapp
