# Post 1 de LinkedIn: ángulo de datos

Adjuntar: `carrusel_post1.pdf` (9 láminas). Link al repositorio en el **primer comentario**, no en el post.
Publicar martes o miércoles entre 8:00 y 9:00 (hora de Chile) y responder comentarios durante la primera hora.

---

Mi agente de IA tiene 80% de contención. El intervalo de confianza va de 63% a 90%.

Construí un agente de WhatsApp para una tienda online (ficticia): vende, consulta pedidos y deriva a un ejecutivo cuando corresponde. Lo evalué como evaluaría un modelo. Cuatro decisiones de datos:

1. Definí los KPIs en SQL antes de mirar resultados. Contención, conversión, ticket promedio, costo por conversación y latencia p50/p90, cada uno definido una sola vez en una vista de BigQuery.

2. Medí cada componente y después el sistema completo. Recuperación (RAG): hit@4 = 1,00 y MRR = 0,93. Router: 30/30. Guardrails: 16/16. Aun así, la evaluación de punta a punta encontró 4 fallas. La precisión en el uso de herramientas fue 90%, luego 87% y luego 100% en tres iteraciones. Bajó antes de subir.

3. Desconfié de mis propios números. Mi set de evaluación dio 100%, pero lo escribí yo sabiendo cómo funcionaba el agente: es como evaluar con datos de entrenamiento. Y el juez automático (un LLM que califica respuestas) todavía no está calibrado contra etiquetas humanas. Las dos cosas están en el backlog.

4. Segmenté antes de concluir. La contención total fue 80%, pero en FAQ era 37,5%. No era un error: ahí caían los "quiero hablar con una persona", que se derivan correctamente. El embudo de ventas mostró dónde se pierde la venta: 92% recibe recomendaciones, 33% agrega al carrito.

Son 30 conversaciones simuladas contra el agente real. Con n = 30, la contención de 80% va de 63% a 90%. Con n = 12, la conversión de 33% va de 14% a 61%. Sirve para encontrar problemas, no para decidir. Eso lo decidirá un piloto con clientes reales.

Lo que sí está medido con precisión: US$0,0011 por conversación y una latencia p90 de 18 segundos, sobre la meta de 15.

Código, evaluaciones y definiciones de KPIs en el primer comentario.

#DataScience #LLM #GenAI #Analytics

---

**Primer comentario:**

Repositorio: https://github.com/JulioPradenas/agente-comercio-whatsapp
(Gemini, LangGraph, pgvector, WhatsApp Cloud API, Langfuse, BigQuery. Los intervalos son de Wilson al 95%.)
