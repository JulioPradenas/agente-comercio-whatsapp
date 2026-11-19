# Guion del video demo (2 minutos)

Objetivo: que alguien que no conoce el proyecto entienda en 2 minutos qué hace el agente, que está en
producción, cómo se controla su calidad y qué resultados de negocio entrega.

## Preparación (antes de grabar)

1. **Despierta el servicio en Render** 2 minutos antes: abre `https://agente-comercio-whatsapp.onrender.com/health`.
   El plan gratuito se suspende tras 15 minutos sin tráfico y el primer mensaje tardaría ~1 minuto.
2. **Usa WhatsApp Desktop** (o WhatsApp Web) en tu Mac en vez del teléfono: se graba mejor y se lee más grande.
3. **Pestañas abiertas en este orden:** WhatsApp, Langfuse (Tracing), GitHub Actions (último run de CI en
   verde), dashboard de Looker Studio (página Resumen ejecutivo).
4. **Grabación:** QuickTime (Archivo → Nueva grabación de pantalla) o Loom. Resolución 1920 × 1080, micrófono
   externo si tienes. Oculta notificaciones (modo No molestar).
5. **Ensaya una vez los mensajes** del bloque 2: si el bot tarda, recorta la espera en la edición.
6. Las respuestas del bot varían un poco entre ejecuciones. Graba hasta tener una toma limpia del bloque 2 y
   graba los demás bloques por separado.

## Guion

| Tiempo | En pantalla | Narración |
|---|---|---|
| **0:00 – 0:12** | WhatsApp con el chat abierto. Título superpuesto: "Agente de compra y postventa por WhatsApp". | "Este es un agente de IA en producción que atiende a los clientes de una tienda online por WhatsApp: vende, consulta pedidos, gestiona devoluciones y deriva a un ejecutivo cuando corresponde." |
| **0:12 – 0:45** | Envía: *"hola, busco un refri no frost grande que no pase de 700 lucas"*. Espera la respuesta. Envía: *"me gusta el más grande, agrégalo al carro"*. Muestra el link de pago. | "Entiende lenguaje chileno, como '700 lucas', lo convierte en un filtro de precio y busca en el catálogo. Los precios vienen siempre del sistema de comercio, nunca los inventa el modelo. Al pedir agregarlo, arma el carrito y entrega el link de pago." |
| **0:45 – 1:00** | Envía: *"en qué va mi último pedido?"*. Luego: *"necesito hablar con una persona"*. Muestra el número de caso. | "También atiende postventa con los datos reales del pedido, y cuando el cliente lo pide, crea un ticket para un ejecutivo con el resumen de la conversación." |
| **1:00 – 1:20** | Langfuse: abre la traza del mensaje del refrigerador. Muestra el árbol router → subagente → herramientas, y la latencia y el costo. | "Cada mensaje queda trazado: qué decidió el router, qué herramientas usó, cuánto tardó y cuánto costó. Una conversación cuesta alrededor de una décima de centavo de dólar." |
| **1:20 – 1:38** | GitHub Actions: run en verde, abre el Summary con el reporte de evaluación. | "Antes de cada cambio, 30 conversaciones de prueba se ejecutan de punta a punta y un segundo modelo califica las respuestas. Si la calidad baja, el cambio no se integra." |
| **1:38 – 1:55** | Dashboard de Looker Studio, página Resumen ejecutivo. Señala contención, conversión y latencia p90. | "Y se mide como producto: 80% de contención, 33% de conversión en conversaciones de venta, y la latencia, que hoy no cumple la meta, es la próxima mejora." |
| **1:55 – 2:00** | Pantalla final con el link al repositorio. | "El código, las evaluaciones y las decisiones de diseño están en el repositorio." |

## Edición

- Corta las esperas de respuesta del bot a 1–2 segundos (un corte con transición simple es suficiente).
- Agrega subtítulos: muchos ven videos en LinkedIn sin sonido.
- Resalta con un recuadro o zoom los números clave (precio, link de pago, costo en Langfuse, contención).
- Exporta en 1080p, MP4. Sube a YouTube como "No listado" o directamente a LinkedIn, y agrega el link en el README.

## Qué no mostrar

- El archivo `.env`, el panel de Environment de Render o cualquier token.
- Tu número de teléfono: en WhatsApp Desktop, el chat muestra el número del bot, no el tuyo, pero revisa la
  barra lateral antes de grabar.
