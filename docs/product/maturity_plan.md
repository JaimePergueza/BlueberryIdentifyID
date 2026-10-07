# Ruta hacia un producto profesional

## Objetivo

Analizar una fotografía de placa y una fotografía microscópica de la misma muestra de arándanos, describir microorganismos compatibles con la evidencia, contar colonias cuando sea posible y registrar una decisión experta verificable.

El nivel taxonómico que puede ofrecerse depende de datos y validación. Dos fotografías no garantizan por sí mismas distinguir especies parecidas, cultivos mixtos ni microorganismos fuera del catálogo. El producto debe devolver una categoría o abstenerse; las hipótesis de género y especie solo se habilitarán cuando se demuestre su desempeño con confirmación independiente.

El primer escenario de trabajo asumido es investigación en un laboratorio. Un servicio para varios laboratorios requiere además aislamiento entre organizaciones, políticas de datos y operación compartida.

## Entrega inicial preparada

- Conteo preliminar de regiones candidatas, abstención por calidad/confluencia y corrección manual.
- Revisiones atribuidas a cuentas autenticadas, con historial y resultado automático inmutable.
- Transacción para los registros de carga/análisis y compensación de archivos.
- Lectura limitada, tope de píxeles y límite de gateway compatible con dos imágenes.
- Ejecución síncrona fuera del event loop y limpieza de caché al cambiar de sesión.
- Protección inicial de login por IP en el gateway.

Estado: propuesta para revisión y pruebas completas. No es una declaración de producto final ni de precisión científica.

## Hito 1: piloto operativo estable

Verificar en CI y navegador: login/logout/expiración, roles, cargas grandes/corruptas, dos imágenes del mismo caso, resultado e imágenes protegidas, revisión, sustitución de revisión final, conteo cero/manual y búsqueda en historial. Confirmar rollback con una base real, migración desde 0028 a 0029 y conservación de revisiones anteriores.

Completar: cola persistida del motor oficial, recuperación tras caída, métricas de tiempos/errores, readiness de PostgreSQL/Redis, reconciliación de archivos, límites por usuario y cuenta, dependencias reproducibles, TLS, respaldo/restauración conjunta de imágenes y datos. No reutilizar el worker MockInferenceEngine como si analizara píxeles reales.

Criterio de salida: suites completas verdes, pruebas de fallos y restauración demostradas, captura de errores observada y piloto reproducible en otro equipo.

## Hito 2: datos y catálogo de identificación

Inspeccionar el Excel del laboratorio cuando esté disponible. El enlace de SharePoint no pudo leerse en el entorno; no se asumió su contenido. Mapear sus columnas al contrato de datos, documentar faltantes y confirmar las unidades de conteo. No generar etiquetas de entrenamiento desde puntuaciones del motor actual.

Cada muestra necesita: identificador estable, lote, pares de fotos, cultivo/tiempo/temperatura, preparación y tinción, aumento y equipo; etiqueta confirmada con método, fecha y responsable; nivel de certeza; conteo manual o motivo de no contabilidad. Conservar las réplicas y registrar si el cultivo es puro o mixto.

Empezar por clases que los datos permitan distinguir, incluyendo desconocidos y muestras no concluyentes. El catálogo de microorganismos asociados a arándanos orienta la selección de clases, pero no permite descartar contaminantes u organismos fuera del catálogo.

Criterio de salida: datos trazables y revisión de etiquetas por especialistas; protocolo de captura; catálogo definido; particiones por muestra/lote y conjunto de evaluación independiente reservado antes de entrenar.

## Hito 3: conteo validado

Anotar centros o máscaras de colonias y regiones excluidas: borde, reflejos, burbujas, polvo y crecimiento confluente. Comparar el conteo actual con el manual por placa y tipo de captura. Medir error absoluto, sesgo y errores de detección; informar cuándo el sistema se abstiene. Evaluar por dispositivo, tamaño de colonia, densidad y medio.

Añadir edición de marcas con historial, revisión de colonias pegadas y exportación de resultados. El protocolo del laboratorio debe definir rangos aceptables y, si se desea UFC/mL, diluciones, volumen y tratamiento de réplicas.

Criterio de salida: tolerancias acordadas antes de evaluar y resultados dentro de ellas en datos independientes. No utilizar el límite heurístico de 300 como prueba de validez científica.

## Hito 4: identificación multimodal validada

Comparar tres enfoques en las mismas particiones: reglas actuales, modelos de cada modalidad y fusión de ambas. Evaluar precisión y sensibilidad por clase, matriz de confusión, calibración, rechazo de desconocidos y relación entre cobertura y errores de abstención. Separar independencia biológica de independencia de fotografías: imágenes/recortes de una muestra no deben dividirse entre entrenamiento y evaluación.

Reservar una evaluación prospectiva con muestras y equipos nuevos. Determinar hasta qué rango taxonómico es justificable el resultado. Si el género o especie no es separable, limitar el producto al grupo o al diferencial compatible y solicitar confirmación de laboratorio.

Criterio de salida: objetivos de desempeño definidos por el laboratorio antes de evaluar, intervalos de incertidumbre reportados y desempeño confirmado prospectivamente. Una métrica global alta no sustituye desempeño aceptable para cada clase relevante.

## Hito 5: versión profesional

Añadir informes exportables con versión de motor, evidencia, conteo automático/manual y método de confirmación; búsqueda por lote y muestra, permisos según operación real, trazabilidad de cambios y documentación de usuario. Probar cargas simultáneas, interrupciones, actualización y restauración en un entorno de preproducción.

Publicar solo las capacidades que superaron sus criterios de salida. Mantener monitoreo de captura y desempeño, revisión de deriva, cambios de versión reproducibles y un procedimiento para retirar o sustituir un modelo.

La duración de esta fase depende del volumen y diversidad de muestras confirmadas, acceso al laboratorio y pruebas prospectivas; no se fija una fecha de identificación confiable sin esa evidencia.
