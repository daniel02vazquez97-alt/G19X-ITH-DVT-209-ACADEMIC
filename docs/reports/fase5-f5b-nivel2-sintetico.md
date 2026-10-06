# Fase 5 — F5b: simulador de Nivel 2 aplicado a los baselines

> **SYNTHETIC.** La demanda de la simulación es la demanda latente del dataset sintético (`demand.csv`); con
> datos REAL no existe y este informe no es reproducible tal cual. No elige el baseline oficial, ni la métrica
> primaria (`DT-021`, `DT-078`), ni umbrales o tolerancias (`DT-079`), ni promueve nada (`DT-084`).
> Generado por `python -m ml simulate`; no editar a mano.

## 1. Ejecución

| Campo | Valor |
|---|---|
| Fecha | 2026-10-05 |
| Comando | `PYTHONPATH=backend python -m ml simulate --data data/synthetic/output --out ml/out --report docs/reports/fase5-f5b-nivel2-sintetico.md --generated-on 2026-10-05 --workers 2 --cache-dir ml/out/f5b-cache --time-budget 140` |
| Dataset | `ds-6c8ad65b4999` (SYNTHETIC) |
| Código | `ml` 0.1.0 |
| Motor U1 (`ENGINE_VERSION`) | 0.1.0; versiones vistas en las decisiones: 0.1.0 |
| Commit | `4830657fc0d4bc45a1d285463aabd4b51119f57a` (cambios sin commit en archivos versionados: False) |
| Python | 3.11.16 |
| Aleatoriedad | none (no randomness) |
| `results_sha256` | `0a83fe3daa06030a04760c3f7b65ce303d371344a60ab9bc044a61a79e05c3e3` |

## 2. Protocolo (`DT-080`, OD-S1 a OD-S4 aceptadas en `DT-088`)

- Periodo: del corte 2024-03-27 (semana 64) al 2025-09-24; nada posterior se lee.
- Bucle cerrado: cada rama ve su propio consumo simulado y su propio inventario; el estado inicial (inventario reconstruido desde `inventory_movements`, `reserved = 0`, órdenes reales abiertas al primer corte) y los eventos exógenos son idénticos en todas las ramas. Las órdenes reales emitidas después del primer corte se descartan.
- Día simulado (`DT-038`): recepciones, demanda latente, consumo = mín(disponible, demanda), ventas perdidas = demanda − consumo; inventario nunca negativo. Decisión cada 7 días tras el consumo del día.
- Cada decisión recalcula el forecast de la rama con su historia simulada y llama a U1 sin cambios (misma `engine_version` en todas las ramas). Un `RECOMMEND` coloca una orden en la fecha de decisión que llega tras el `L` usado por el motor; cuenta como tránsito en las decisiones siguientes. **Esto aísla el efecto del forecast pero no mide la variabilidad del proveedor.**
- Métricas en unidades: unidades faltantes, días y tasa de desabasto, *fill rate*, nivel de servicio por ciclos de 7 días, inventario medio (disponible al final del día) en unidades y en valor (`unit_cost` del proveedor preferente), rotación, unidades pedidas y órdenes. Sin costes (`BR-X04`); sin «exceso de inventario» (OD-S4: sin umbral absoluto) ni «órdenes urgentes» (todas usan el lead time del motor).

## 3. Valores provisionales y pendientes

- Cadencia de reentrenamiento: cada 1 decisión(es) semanal(es) (provisional).
- Calentamiento excluido del segundo periodo: 8 semanas (provisional).
- Llegada de las órdenes abiertas al primer corte: `EXPECTED_ON` — DT-080 point 7 by default; ACTUAL_RECEIPTS pending the responsable (OD-S1).
- Tolerancia de inventario del cruce de `DT-078`: 0.0 (OPEN until G1 (DT-079); provisional).
- Modelos de las ramas: los de F5a (SES provisional de `DT-076` punto 7 incluido).

## 4. Población y decisiones

- Series simuladas: 95; órdenes reales abiertas al primer corte (exógenas): 93.
- Fuera de la simulación (sin `L + R` o no vigentes en el primer corte): producto 3 (NO_ACTIVE_PREFERRED_SUPPLIER), producto 20 (NO_ACTIVE_PREFERRED_SUPPLIER), producto 57 (NO_ACTIVE_PREFERRED_SUPPLIER), producto 71 (NO_ACTIVE_PREFERRED_SUPPLIER), producto 74 (NO_ACTIVE_PREFERRED_SUPPLIER).

| Rama | NOT_CALCULABLE | NO_NEED | RECOMMEND | Motivos `NOT_CALCULABLE` |
|---|---|---|---|---|
| naïve | 151 | 2835 | 4424 | PRODUCT_OUT_OF_VALIDITY: 151 |
| naïve estacional | 151 | 2523 | 4736 | PRODUCT_OUT_OF_VALIDITY: 151 |
| media móvil 13 | 151 | 2494 | 4765 | PRODUCT_OUT_OF_VALIDITY: 151 |
| SES (provisional) | 151 | 2494 | 4765 | PRODUCT_OUT_OF_VALIDITY: 151 |

## 5. Resultados de Nivel 2 por rama, segmento y periodo (SYNTHETIC)

### periodo completo (2024-03-28 a 2025-09-24)

| Segmento | Rama | Series | Unidades faltantes | Días con desabasto | Tasa de desabasto | *Fill rate* | Servicio por ciclos | Inventario medio | Relativo a media móvil 13 | Valor medio | Rotación | Unidades pedidas | Órdenes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| todos | naïve | 95 | 5,137 | 336 | 0.006 | 0.993 | 0.981 | 19,236.7 | 1.065 | 22,250,957 | 35.425 | 678,882 | 4372 |
| todos | naïve estacional | 95 | 11,953 | 755 | 0.015 | 0.983 | 0.944 | 17,056.4 | 0.944 | 19,847,289 | 39.554 | 670,238 | 4689 |
| todos | media móvil 13 | 95 | 3,882 | 255 | 0.005 | 0.994 | 0.984 | 18,062.9 | 1.000 | 20,865,858 | 37.797 | 680,133 | 4714 |
| todos | SES (provisional) | 95 | 3,860 | 255 | 0.005 | 0.994 | 0.984 | 17,892.9 | 0.991 | 20,608,290 | 38.157 | 679,586 | 4715 |
| intermitente | naïve | 10 | 68 | 10 | 0.002 | 0.993 | 0.990 | 1,498.5 | 2.037 | 1,640,164 | 6.886 | 11,181 | 126 |
| intermitente | naïve estacional | 10 | 789 | 69 | 0.013 | 0.924 | 0.941 | 692.9 | 0.942 | 784,342 | 13.852 | 9,288 | 256 |
| intermitente | media móvil 13 | 10 | 605 | 56 | 0.010 | 0.942 | 0.949 | 735.8 | 1.000 | 823,208 | 13.294 | 9,759 | 263 |
| intermitente | SES (provisional) | 10 | 496 | 52 | 0.010 | 0.952 | 0.949 | 719.6 | 0.978 | 808,308 | 13.746 | 9,881 | 269 |
| suave | naïve | 85 | 5,069 | 326 | 0.007 | 0.993 | 0.980 | 17,738.2 | 1.024 | 20,610,792 | 37.836 | 667,701 | 4246 |
| suave | naïve estacional | 85 | 11,164 | 686 | 0.015 | 0.983 | 0.944 | 16,363.5 | 0.944 | 19,062,947 | 40.642 | 660,950 | 4433 |
| suave | media móvil 13 | 85 | 3,277 | 199 | 0.004 | 0.995 | 0.988 | 17,327.1 | 1.000 | 20,042,650 | 38.837 | 670,374 | 4451 |
| suave | SES (provisional) | 85 | 3,364 | 203 | 0.004 | 0.995 | 0.988 | 17,173.3 | 0.991 | 19,799,982 | 39.180 | 669,705 | 4446 |

### sin las semanas de calentamiento (2024-05-23 a 2025-09-24)

| Segmento | Rama | Series | Unidades faltantes | Días con desabasto | Tasa de desabasto | *Fill rate* | Servicio por ciclos | Inventario medio | Relativo a media móvil 13 | Valor medio | Rotación | Unidades pedidas | Órdenes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| todos | naïve | 95 | 2,540 | 168 | 0.004 | 0.996 | 0.988 | 19,492.7 | 1.066 | 22,475,188 | 31.432 | 605,437 | 3928 |
| todos | naïve estacional | 95 | 8,375 | 554 | 0.012 | 0.986 | 0.948 | 17,080.1 | 0.934 | 19,804,103 | 35.530 | 600,453 | 4226 |
| todos | media móvil 13 | 95 | 1,166 | 87 | 0.002 | 0.998 | 0.991 | 18,280.5 | 1.000 | 21,073,774 | 33.592 | 608,821 | 4244 |
| todos | SES (provisional) | 95 | 1,180 | 89 | 0.002 | 0.998 | 0.991 | 18,098.0 | 0.990 | 20,799,937 | 33.930 | 608,462 | 4254 |
| intermitente | naïve | 10 | 42 | 6 | 0.001 | 0.996 | 0.993 | 1,570.8 | 2.150 | 1,711,953 | 5.920 | 9,207 | 106 |
| intermitente | naïve estacional | 10 | 737 | 64 | 0.013 | 0.921 | 0.940 | 683.3 | 0.935 | 772,051 | 12.594 | 8,413 | 240 |
| intermitente | media móvil 13 | 10 | 559 | 50 | 0.010 | 0.940 | 0.949 | 730.4 | 1.000 | 817,968 | 12.024 | 8,823 | 242 |
| intermitente | SES (provisional) | 10 | 468 | 47 | 0.010 | 0.950 | 0.949 | 715.1 | 0.979 | 801,229 | 12.410 | 8,935 | 248 |
| suave | naïve | 85 | 2,498 | 162 | 0.004 | 0.996 | 0.987 | 17,921.9 | 1.021 | 20,763,235 | 33.668 | 596,230 | 3822 |
| suave | naïve estacional | 85 | 7,638 | 490 | 0.012 | 0.987 | 0.949 | 16,396.8 | 0.934 | 19,032,052 | 36.486 | 592,040 | 3986 |
| suave | media móvil 13 | 85 | 607 | 37 | 0.001 | 0.999 | 0.996 | 17,550.1 | 1.000 | 20,255,805 | 34.489 | 599,998 | 4002 |
| suave | SES (provisional) | 85 | 712 | 42 | 0.001 | 0.999 | 0.996 | 17,382.9 | 0.990 | 19,998,708 | 34.815 | 599,527 | 4006 |

### Dispersión entre las ventanas de 14 semanas de los 17 cortes de F5a (todas las series)

| Rama | Unidades faltantes por ventana: media (de; mín–máx) | *Fill rate* | Tasa de desabasto | Inventario medio |
|---|---|---|---|---|
| naïve | 617.000 (634.428; 173.000–2,979.000) | 0.995 (0.005; 0.976–0.999) | 0.005 (0.005; 0.002–0.021) | 19,325.701 (935.639; 17,015.816–20,369.980) |
| naïve estacional | 1,902.059 (915.103; 617.000–4,644.000) | 0.985 (0.007; 0.963–0.995) | 0.014 (0.006; 0.004–0.029) | 16,985.463 (854.283; 15,935.378–18,664.969) |
| media móvil 13 | 406.000 (750.927; 12.000–3,212.000) | 0.997 (0.006; 0.974–1.000) | 0.003 (0.005; 0.000–0.022) | 18,136.588 (1,242.358; 15,782.949–19,392.327) |
| SES (provisional) | 400.765 (811.958; 23.000–3,404.000) | 0.997 (0.006; 0.973–1.000) | 0.003 (0.005; 0.000–0.023) | 17,938.088 (1,209.557; 15,629.276–19,220.418) |

## 6. Cruce informativo con el Nivel 1 (`DT-078`, sin elegir métrica)

Para cada par de ramas y cada (serie, corte): ¿la métrica candidata de Nivel 1 y las unidades faltantes de Nivel 2 en las 14 semanas siguientes prefieren la misma rama? Sin contar empates. «Con inventario»: además, la rama preferida no tiene más inventario medio que la otra (tolerancia `OPEN`, provisional 0).

| Horizonte de Nivel 1 | Métrica | Pares comparados | Empates | Acuerdo | Acuerdo y restricción de inventario (sobre comparados) | Acuerdos que cumplen la restricción |
|---|---|---|---|---|---|---|
| h = 1 | MASE | 1742 | 7858 | 0.594 | 0.128 | 0.215 |
| h = 1 | RMSSE | 1742 | 7858 | 0.594 | 0.128 | 0.215 |
| h = 1 | WAPE | 1568 | 7498 | 0.607 | 0.128 | 0.211 |
| L + R | MASE | 1782 | 7776 | 0.607 | 0.153 | 0.251 |
| L + R | RMSSE | 1782 | 7776 | 0.607 | 0.153 | 0.251 |
| L + R | WAPE | 1782 | 7776 | 0.607 | 0.153 | 0.251 |

En cada serie-corte, MASE, RMSSE y WAPE ordenan las ramas igual (las tres son monótonas en |e| con la misma escala para todas las ramas): sí. Por eso el acuerdo serie-corte no distingue entre ellas; las diferencias aparecen al agregar.

Spearman entre las ramas (4 puntos por corte): agregado de la métrica de Nivel 1 frente al total de unidades faltantes en la ventana, sobre las mismas series.

| Horizonte | Métrica | ρ medio | mín | máx | Cortes |
|---|---|---|---|---|---|
| h = 1 | MASE | 0.718 | 0.200 | 1.000 | 17 |
| h = 1 | RMSSE | 0.729 | 0.200 | 1.000 | 17 |
| h = 1 | WAPE | 0.635 | 0.200 | 1.000 | 17 |
| L + R | MASE | 0.776 | 0.200 | 1.000 | 17 |
| L + R | RMSSE | 0.788 | 0.200 | 1.000 | 17 |
| L + R | WAPE | 0.694 | -0.400 | 1.000 | 17 |

## 7. Salidas

Junto a este informe se versiona un JSON resumido (mismo nombre, `.json`): metadatos, configuración, huella y agregados. El detalle (`f5b-windows.csv` por rama × producto × ventana de cada corte, con las mismas claves que `f5a-observations.csv`; `f5b-orders.csv`; `f5b-decisions.csv`; `f5b-summary.json`) se regenera de forma determinista con el comando de §1 en `ml/out/`, ignorado por Git. Huellas:

- `f5b-decisions.csv`: `a9fd7608fc7a0ba21154e13ac71766da14617e8c876e6dfa0a0e7d9a7bb3eb4c`
- `f5b-orders.csv`: `823c72d74d034a0a60863826577bf687adff475494b30811d2370fb3e89f31f6`
- `f5b-windows.csv`: `895488760c0745b93da433233caada459c673057594337b4b9518d3e0a1a062d`
