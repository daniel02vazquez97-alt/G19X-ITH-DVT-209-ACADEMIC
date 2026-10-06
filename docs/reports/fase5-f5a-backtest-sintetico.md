# Fase 5 — F5a: backtesting de baselines, Nivel 1 y segmentación provisional

> **SYNTHETIC.** Evidencia sobre el dataset sintético; debe revalidarse con datos REAL (`docs/05` §20).
> Este informe **no** elige el baseline oficial, ni la métrica primaria (`DT-021`, `DT-078`), ni umbrales
> (`DT-077`, `DT-079`), ni promueve nada (`DT-084`). Las cifras se presentan sin conclusiones de promoción.
> Generado por `python -m ml backtest`; no editar a mano.

## 1. Ejecución

| Campo | Valor |
|---|---|
| Fecha | 2026-10-05 |
| Comando | `PYTHONPATH=backend python -m ml backtest --data data/synthetic/output --out ml/out --report docs/reports/fase5-f5a-backtest-sintetico.md --generated-on 2026-10-05` |
| Dataset | `ds-6c8ad65b4999` (SYNTHETIC) |
| Código F5a | `ml` 0.1.0 |
| Motor U1 (`ENGINE_VERSION`) | 0.1.0 |
| Baselines U3 | `baseline.moving_average` 1.0.0, `baseline.naive` 1.0.0, `baseline.seasonal_naive` 1.0.0 |
| SES | `ml.ses` 0.1.0-provisional (PROPUESTA, `DT-076` punto 7) |
| Commit | `2c3d9c6bf68fcf1f3a1aabe2680e041ddff889de` (cambios sin commit en archivos versionados: False) |
| Python | 3.11.16 |
| Aleatoriedad | none (no randomness) |
| `results_sha256` | `67608e958eb87ad5cb02e40532b47b6a54940e3b153d56fbd266b32d6bbe433a` |

## 2. Protocolo (`DT-075`, `DT-076`)

- 17 cortes, ventana expansiva, horizonte de 14 semanas: 2024-03-27, 2024-04-24, 2024-05-22, 2024-06-19, 2024-07-17, 2024-08-14, 2024-09-11, 2024-10-09, 2024-11-06, 2024-12-04, 2025-01-01, 2025-01-29, 2025-02-26, 2025-03-26, 2025-04-23, 2025-05-21, 2025-06-18.
- *Holdout*: corte 2025-09-24; ningún camino lee datos posteriores al 2025-09-24 (guarda en el lector y en cada corte).
- Horizontes: `h = 1` y `L + R` días por producto (`L` con las reglas de U1 en el corte, `R = 7`; demanda con `supply_engine.rules.demand_over_horizon`, exacta como en el motor).
- Verdad: consumo observado; nunca `demand.csv` ni valores imputados. Dos vistas: todas las semanas y solo objetivos sin ningún día con desabasto.
- Comparación: solo sobre el conjunto común serie-corte-horizonte (todos los modelos elegibles y verdad completa). Celdas: media entre cortes (desviación poblacional; mínimo–máximo).
- Error `e = F − Y`: sesgo positivo = sobrepronóstico. MASE/RMSSE escaladas con el naïve a un paso dentro del entrenamiento de cada corte.

## 3. Valores provisionales usados (PROPUESTA)

- Población por corte: `AS_OF_VALIDITY` (DT-087 (ACEPTADA)); la otra regla se compara en §6.
- SES: rejilla α 0.05–0.95 (paso 0,05); minimum one-step SSE inside the training window; ties → smallest alpha; nivel inicial `FIRST_OBSERVATION`; mínimo 25 semanas; nearest-rank 10/90 of DT-056 on SES errors per horizon (fixed alpha).
- Segmentación: ADI ≥ 1.32, CV² ≥ 0.49, histórico corto < 25 semanas; estacionalidad OPEN (no criterion, DT-077).
- Denominador cero de MASE/RMSSE: `EXCLUDE_AND_COUNT`; escala en L + R: `WEEKLY_SCALE_PRORATED`.
- Política de U1 para `L`: {'lt_max': 90, 'n': 12, 'n_min': 3, 'policy_set': 'V1_PROVISIONAL', 'r': 7, 'z': '33/20'}.

## 4. Población, elegibilidad y segmentos por corte

| Corte | Población | Excluidos | naïve | naïve estacional | media móvil 13 | SES (provisional) | Común h=1 | Común L+R | Desabasto h=1 | Desabasto L+R | L+R días (mín–máx) | Segmentos |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2024-03-27 | 100 | 0 | 100 | 100 | 100 | 100 | 100 | 95 | 17 | 38 | 27–46 | intermitente 14, irregular 1, suave 85 |
| 2024-04-24 | 100 | 0 | 100 | 100 | 100 | 100 | 100 | 95 | 18 | 38 | 27–46 | intermitente 14, irregular 1, suave 85 |
| 2024-05-22 | 100 | 0 | 100 | 100 | 100 | 100 | 100 | 95 | 18 | 43 | 21–44 | intermitente 14, irregular 1, suave 85 |
| 2024-06-19 | 100 | 0 | 100 | 100 | 100 | 100 | 100 | 95 | 25 | 49 | 27–48 | intermitente 14, irregular 1, suave 85 |
| 2024-07-17 | 100 | 0 | 100 | 100 | 100 | 100 | 100 | 95 | 12 | 36 | 28–50 | intermitente 14, irregular 1, suave 85 |
| 2024-08-14 | 100 | 0 | 100 | 100 | 100 | 100 | 100 | 95 | 15 | 39 | 30–42 | intermitente 14, irregular 1, suave 85 |
| 2024-09-11 | 100 | 0 | 100 | 100 | 100 | 100 | 100 | 95 | 15 | 33 | 28–49 | intermitente 14, irregular 1, suave 85 |
| 2024-10-09 | 100 | 0 | 100 | 100 | 100 | 100 | 100 | 95 | 16 | 43 | 27–46 | intermitente 14, irregular 1, suave 85 |
| 2024-11-06 | 100 | 0 | 100 | 100 | 100 | 100 | 100 | 95 | 21 | 40 | 29–48 | intermitente 14, irregular 1, suave 85 |
| 2024-12-04 | 100 | 0 | 100 | 100 | 100 | 100 | 100 | 95 | 14 | 38 | 30–45 | intermitente 14, irregular 1, suave 85 |
| 2025-01-01 | 100 | 0 | 100 | 100 | 100 | 100 | 100 | 95 | 12 | 36 | 26–46 | intermitente 14, irregular 1, suave 85 |
| 2025-01-29 | 100 | 0 | 100 | 100 | 100 | 100 | 100 | 95 | 10 | 37 | 27–42 | intermitente 14, irregular 1, suave 85 |
| 2025-02-26 | 100 | 0 | 100 | 100 | 100 | 100 | 100 | 93 | 23 | 44 | 22–42 | intermitente 14, irregular 1, suave 85 |
| 2025-03-26 | 100 | 0 | 100 | 100 | 100 | 100 | 100 | 90 | 19 | 42 | 27–48 | intermitente 14, irregular 1, suave 85 |
| 2025-04-23 | 95 | INACTIVE_OR_OUT_OF_VALIDITY: 5 | 95 | 95 | 95 | 95 | 95 | 90 | 24 | 40 | 26–47 | descontinuado 5, intermitente 14, irregular 1, suave 80 |
| 2025-05-21 | 95 | INACTIVE_OR_OUT_OF_VALIDITY: 5 | 95 | 95 | 95 | 95 | 95 | 90 | 14 | 40 | 28–46 | descontinuado 5, intermitente 14, irregular 1, suave 80 |
| 2025-06-18 | 95 | INACTIVE_OR_OUT_OF_VALIDITY: 5 | 95 | 95 | 95 | 95 | 95 | 90 | 17 | 42 | 27–41 | descontinuado 5, intermitente 14, irregular 1, suave 80 |

### 4.1 Población, descontinuados y series fuera de L + R

- Población por corte con la regla de vigencia al corte (`DT-087`): 100 (2024-03-27 a 2025-03-26); 95 (2025-04-23 a 2025-06-18), de 100 candidatas.
- Fuera de la población (`INACTIVE_OR_OUT_OF_VALIDITY`; en el desglose por segmento figuran como «descontinuado»): ninguno (2024-03-27 a 2025-03-26); 21, 26, 37, 56, 61 (2025-04-23 a 2025-06-18). «Población» y «descontinuado» suman siempre las candidatas.
- Productos con `is_active = false` en la foto del dataset que están dentro de la población: 5 (2024-03-27 a 2025-03-26); 0 (2025-04-23 a 2025-06-18).
- Sin proveedor preferente activo (U1 se detiene antes de `H`: fuera de `L + R`, dentro de `h = 1`): productos 3, 20, 57, 71, 74 (2024-03-27 a 2025-06-18). El `is_active` de los proveedores es una foto sin historial: no se infiere ni se reconstruye (`DT-087`).

Productos con `valid_to` dentro del periodo legible: segmento mientras estaban en la población y recuento sobre el calendario de 156 semanas contando como cero las semanas posteriores a `valid_to` (cómo los clasificaría una medición del periodo completo como la orientativa de `DT-077`: 80 suaves, 19 intermitentes y 1 irregular). El recuento solo usa `valid_to`, un dato maestro; no lee datos posteriores.

| Producto | `is_active` (foto) | `valid_to` | Último corte en población | Segmento mientras vigente | Semanas no nulas / 156 | ADI (calendario completo) | CV² | Segmento (calendario completo) |
|---|---|---|---|---|---|---|---|---|
| 21 | false | 2025-04-02 | 2025-03-26 | suave ×14 | 116 / 156 | 1.345 | 0.013 | intermitente |
| 26 | false | 2025-04-02 | 2025-03-26 | suave ×14 | 117 / 156 | 1.333 | 0.061 | intermitente |
| 37 | false | 2025-04-02 | 2025-03-26 | suave ×14 | 117 / 156 | 1.333 | 0.030 | intermitente |
| 56 | false | 2025-04-02 | 2025-03-26 | suave ×14 | 114 / 156 | 1.368 | 0.084 | intermitente |
| 61 | false | 2025-04-02 | 2025-03-26 | suave ×14 | 117 / 156 | 1.333 | 0.002 | intermitente |

## 5. Resultados de Nivel 1 (SYNTHETIC)

### 5.1 h = 1 (semana 1) — todas las semanas — escaladas y relativas

| Segmento | Modelo | n | MASE | RMSSE | WAPE | sesgo relativo |
|---|---|---|---|---|---|---|
| todos | naïve | 1685 | 0.981 (0.249; 0.694–1.613) | 0.563 (0.092; 0.431–0.763) | 0.132 (0.037; 0.070–0.210) | -0.011 (0.022; -0.058–0.023) |
| todos | naïve estacional | 1685 | 1.688 (0.340; 1.334–2.819) | 0.987 (0.093; 0.834–1.266) | 0.199 (0.024; 0.163–0.243) | 0.001 (0.038; -0.084–0.064) |
| todos | media móvil 13 | 1685 | 0.983 (0.238; 0.768–1.840) | 0.555 (0.061; 0.472–0.733) | 0.135 (0.016; 0.106–0.159) | -0.010 (0.025; -0.061–0.038) |
| todos | SES (provisional) | 1685 | 0.886 (0.263; 0.668–1.824) | 0.492 (0.074; 0.409–0.716) | 0.119 (0.017; 0.085–0.147) | -0.014 (0.024; -0.054–0.041) |
| suave | naïve | 1430 | 1.034 (0.282; 0.700–1.725) | 0.569 (0.104; 0.407–0.791) | 0.117 (0.037; 0.060–0.201) | -0.012 (0.025; -0.079–0.029) |
| suave | naïve estacional | 1430 | 1.880 (0.401; 1.492–3.201) | 1.079 (0.111; 0.920–1.399) | 0.187 (0.025; 0.144–0.235) | 0.000 (0.040; -0.086–0.068) |
| suave | media móvil 13 | 1430 | 1.067 (0.276; 0.799–2.052) | 0.583 (0.068; 0.472–0.776) | 0.124 (0.018; 0.095–0.152) | -0.011 (0.025; -0.056–0.042) |
| suave | SES (provisional) | 1430 | 0.952 (0.306; 0.694–2.036) | 0.510 (0.084; 0.410–0.758) | 0.109 (0.018; 0.074–0.137) | -0.016 (0.024; -0.055–0.044) |
| intermitente | naïve | 238 | 0.732 (0.146; 0.470–1.050) | 0.563 (0.111; 0.362–0.793) | 1.582 (1.037; 0.771–4.500) | 0.442 (1.198; -0.771–3.955) |
| intermitente | naïve estacional | 238 | 0.658 (0.211; 0.296–1.024) | 0.509 (0.162; 0.231–0.781) | 1.562 (1.810; 0.395–8.591) | 0.399 (1.724; -0.463–7.136) |
| intermitente | media móvil 13 | 238 | 0.552 (0.099; 0.357–0.683) | 0.425 (0.076; 0.277–0.526) | 1.231 (0.968; 0.626–4.724) | 0.409 (1.059; -0.319–4.178) |
| intermitente | SES (provisional) | 238 | 0.552 (0.099; 0.376–0.709) | 0.425 (0.075; 0.290–0.544) | 1.223 (0.945; 0.575–4.624) | 0.411 (1.081; -0.352–4.229) |
| irregular | naïve | 17 | 0.000 (0.000; 0.000–0.000) | 0.000 (0.000; 0.000–0.000) | — | — |
| irregular | naïve estacional | 17 | 0.000 (0.000; 0.000–0.000) | 0.000 (0.000; 0.000–0.000) | — | — |
| irregular | media móvil 13 | 17 | 0.000 (0.000; 0.000–0.000) | 0.000 (0.000; 0.000–0.000) | — | — |
| irregular | SES (provisional) | 17 | 0.000 (0.000; 0.000–0.000) | 0.000 (0.000; 0.000–0.000) | — | — |

### 5.2 h = 1 (semana 1) — todas las semanas — absolutas, sesgo, cobertura y MAPE informativa

| Segmento | Modelo | n | MAE | RMSE | sesgo | cobertura | MAPE (inf.) |
|---|---|---|---|---|---|---|---|
| todos | naïve | 1685 | 11.132 (2.985; 5.960–17.290) | 30.783 (12.356; 11.396–58.580) | -0.929 (1.899; -4.850–1.970) | 0.841 (0.036; 0.790–0.900) | 0.262 (0.142; 0.127–0.604) |
| todos | naïve estacional | 1685 | 16.905 (2.003; 13.860–20.760) | 37.781 (8.241; 26.848–56.287) | -0.020 (3.284; -7.380–5.190) | 0.836 (0.034; 0.740–0.880) | 0.296 (0.095; 0.196–0.605) |
| todos | media móvil 13 | 1685 | 11.417 (1.343; 9.005–13.122) | 26.343 (5.459; 19.386–36.174) | -0.868 (2.118; -5.380–3.095) | 0.831 (0.038; 0.770–0.916) | 0.216 (0.085; 0.140–0.408) |
| todos | SES (provisional) | 1685 | 10.113 (1.369; 7.263–12.123) | 24.311 (6.203; 16.409–37.970) | -1.269 (2.034; -4.789–3.293) | 0.814 (0.038; 0.740–0.916) | 0.204 (0.091; 0.121–0.432) |
| suave | naïve | 1430 | 11.509 (3.466; 5.953–19.188) | 32.678 (13.556; 11.628–63.384) | -1.196 (2.470; -7.753–2.847) | 0.833 (0.037; 0.788–0.906) | 0.205 (0.124; 0.092–0.562) |
| suave | naïve estacional | 1430 | 18.492 (2.420; 14.247–23.163) | 40.500 (9.178; 28.195–61.202) | -0.028 (3.949; -8.765–6.376) | 0.827 (0.038; 0.718–0.882) | 0.264 (0.100; 0.170–0.594) |
| suave | media móvil 13 | 1430 | 12.247 (1.649; 9.408–14.448) | 28.192 (6.015; 20.537–39.081) | -1.126 (2.464; -5.672–3.879) | 0.824 (0.045; 0.741–0.912) | 0.196 (0.083; 0.126–0.399) |
| suave | SES (provisional) | 1430 | 10.717 (1.645; 7.347–13.082) | 25.950 (6.853; 17.281–40.980) | -1.589 (2.352; -5.629–4.137) | 0.810 (0.042; 0.741–0.912) | 0.185 (0.092; 0.102–0.433) |
| intermitente | naïve | 238 | 9.681 (2.632; 6.429–14.929) | 15.666 (5.093; 8.920–27.100) | 0.597 (4.571; -9.643–12.429) | 0.878 (0.073; 0.786–1.000) | 1.117 (0.563; 0.614–2.921) |
| intermitente | naïve estacional | 238 | 8.601 (3.036; 3.214–13.500) | 14.105 (5.579; 4.788–25.505) | 0.029 (3.550; -4.357–11.214) | 0.878 (0.088; 0.714–1.000) | 0.796 (0.212; 0.458–1.133) |
| intermitente | media móvil 13 | 238 | 7.258 (1.405; 4.775–9.885) | 11.169 (2.673; 7.238–18.310) | 0.629 (2.695; -3.989–6.566) | 0.866 (0.073; 0.786–1.000) | 0.518 (0.179; 0.342–1.058) |
| intermitente | SES (provisional) | 238 | 7.219 (1.423; 5.176–9.533) | 11.056 (2.637; 7.675–17.493) | 0.567 (2.851; -4.395–6.646) | 0.824 (0.074; 0.714–0.929) | 0.496 (0.160; 0.301–0.990) |
| irregular | naïve | 17 | 0.000 (0.000; 0.000–0.000) | 0.000 (0.000; 0.000–0.000) | 0.000 (0.000; 0.000–0.000) | 1.000 (0.000; 1.000–1.000) | — |
| irregular | naïve estacional | 17 | 0.000 (0.000; 0.000–0.000) | 0.000 (0.000; 0.000–0.000) | 0.000 (0.000; 0.000–0.000) | 1.000 (0.000; 1.000–1.000) | — |
| irregular | media móvil 13 | 17 | 0.000 (0.000; 0.000–0.000) | 0.000 (0.000; 0.000–0.000) | 0.000 (0.000; 0.000–0.000) | 1.000 (0.000; 1.000–1.000) | — |
| irregular | SES (provisional) | 17 | 0.000 (0.000; 0.000–0.000) | 0.000 (0.000; 0.000–0.000) | 0.000 (0.000; 0.000–0.000) | 1.000 (0.000; 1.000–1.000) | — |

### 5.3 h = 1 (semana 1) — solo objetivos sin desabasto — escaladas y relativas

| Segmento | Modelo | n | MASE | RMSSE | WAPE | sesgo relativo |
|---|---|---|---|---|---|---|
| todos | naïve | 1395 | 0.783 (0.164; 0.565–1.113) | 0.472 (0.064; 0.382–0.617) | 0.092 (0.028; 0.057–0.145) | -0.040 (0.030; -0.095–0.009) |
| todos | naïve estacional | 1395 | 1.623 (0.198; 1.407–2.105) | 0.983 (0.079; 0.866–1.144) | 0.172 (0.024; 0.137–0.234) | -0.033 (0.027; -0.091–0.008) |
| todos | media móvil 13 | 1395 | 0.822 (0.083; 0.651–0.954) | 0.491 (0.041; 0.394–0.574) | 0.107 (0.014; 0.087–0.132) | -0.043 (0.016; -0.079–-0.009) |
| todos | SES (provisional) | 1395 | 0.705 (0.096; 0.497–0.918) | 0.416 (0.045; 0.303–0.493) | 0.090 (0.013; 0.070–0.119) | -0.052 (0.016; -0.082–-0.015) |
| suave | naïve | 1239 | 0.760 (0.179; 0.496–1.120) | 0.439 (0.068; 0.327–0.592) | 0.078 (0.027; 0.045–0.133) | -0.040 (0.029; -0.095–0.005) |
| suave | naïve estacional | 1239 | 1.707 (0.233; 1.456–2.322) | 1.014 (0.091; 0.898–1.186) | 0.159 (0.025; 0.125–0.214) | -0.034 (0.027; -0.093–0.012) |
| suave | media móvil 13 | 1239 | 0.829 (0.086; 0.678–0.966) | 0.478 (0.040; 0.401–0.560) | 0.096 (0.014; 0.076–0.120) | -0.044 (0.015; -0.074–-0.016) |
| suave | SES (provisional) | 1239 | 0.697 (0.102; 0.494–0.936) | 0.393 (0.045; 0.292–0.465) | 0.079 (0.013; 0.060–0.107) | -0.053 (0.014; -0.082–-0.022) |
| intermitente | naïve | 156 | 0.964 (0.166; 0.674–1.295) | 0.742 (0.127; 0.521–0.976) | 1.433 (0.869; 0.771–4.091) | 0.297 (1.022; -0.771–2.818) |
| intermitente | naïve estacional | 156 | 0.948 (0.297; 0.423–1.433) | 0.732 (0.228; 0.331–1.093) | 1.607 (1.820; 0.479–8.591) | 0.408 (1.724; -0.463–7.136) |
| intermitente | media móvil 13 | 156 | 0.764 (0.154; 0.411–0.959) | 0.589 (0.118; 0.323–0.741) | 1.189 (0.942; 0.626–4.724) | 0.373 (1.039; -0.319–4.178) |
| intermitente | SES (provisional) | 156 | 0.766 (0.142; 0.491–0.992) | 0.590 (0.109; 0.373–0.762) | 1.188 (0.919; 0.575–4.624) | 0.370 (1.060; -0.352–4.229) |

### 5.4 h = 1 (semana 1) — solo objetivos sin desabasto — absolutas, sesgo, cobertura y MAPE informativa

| Segmento | Modelo | n | MAE | RMSE | sesgo | cobertura | MAPE (inf.) |
|---|---|---|---|---|---|---|---|
| todos | naïve | 1395 | 8.448 (2.569; 5.250–12.439) | 22.604 (11.951; 9.867–48.603) | -3.700 (2.756; -8.122–0.849) | 0.883 (0.025; 0.835–0.920) | 0.128 (0.028; 0.080–0.172) |
| todos | naïve estacional | 1395 | 15.831 (2.551; 12.541–21.523) | 34.864 (8.868; 22.174–50.566) | -3.094 (2.558; -8.341–0.705) | 0.864 (0.034; 0.813–0.922) | 0.202 (0.021; 0.170–0.240) |
| todos | media móvil 13 | 1395 | 9.800 (1.635; 7.851–13.908) | 21.197 (4.804; 15.944–31.526) | -3.962 (1.656; -7.557–-0.738) | 0.853 (0.037; 0.795–0.958) | 0.112 (0.011; 0.091–0.130) |
| todos | SES (provisional) | 1395 | 8.320 (1.557; 6.313–12.753) | 18.081 (4.935; 12.188–29.195) | -4.805 (1.631; -8.769–-1.221) | 0.840 (0.040; 0.788–0.958) | 0.096 (0.011; 0.076–0.114) |
| suave | naïve | 1239 | 7.964 (2.773; 4.462–12.806) | 23.055 (12.994; 8.461–51.645) | -4.131 (3.001; -9.657–0.462) | 0.886 (0.024; 0.847–0.936) | 0.073 (0.014; 0.052–0.098) |
| suave | naïve estacional | 1239 | 16.242 (2.672; 12.800–21.885) | 36.336 (9.513; 23.344–53.481) | -3.487 (2.857; -9.500–1.253) | 0.870 (0.038; 0.821–0.938) | 0.161 (0.017; 0.138–0.197) |
| suave | media móvil 13 | 1239 | 9.778 (1.738; 7.743–13.890) | 21.979 (5.045; 16.577–33.027) | -4.543 (1.699; -8.259–-1.444) | 0.858 (0.040; 0.770–0.953) | 0.088 (0.009; 0.074–0.103) |
| suave | SES (provisional) | 1239 | 8.116 (1.615; 6.080–12.659) | 18.590 (5.231; 12.469–29.924) | -5.476 (1.662; -9.687–-2.009) | 0.849 (0.041; 0.770–0.953) | 0.072 (0.009; 0.061–0.092) |
| intermitente | naïve | 156 | 12.417 (2.734; 8.571–18.500) | 16.945 (4.597; 10.043–27.263) | -0.285 (6.035; -13.500–13.222) | 0.863 (0.100; 0.700–1.000) | 0.937 (0.322; 0.614–2.000) |
| intermitente | naïve estacional | 156 | 12.433 (4.563; 4.889–18.900) | 17.138 (6.977; 6.334–30.178) | 0.091 (5.013; -6.100–15.700) | 0.823 (0.134; 0.600–1.000) | 0.797 (0.213; 0.458–1.133) |
| intermitente | media móvil 13 | 156 | 9.944 (2.143; 5.901–14.058) | 13.128 (3.464; 8.127–23.198) | 0.682 (3.684; -5.585–9.192) | 0.818 (0.111; 0.667–1.000) | 0.452 (0.141; 0.223–0.843) |
| intermitente | SES (provisional) | 156 | 9.911 (2.006; 7.030–13.535) | 12.989 (3.299; 9.307–22.172) | 0.557 (3.879; -6.154–9.304) | 0.767 (0.120; 0.600–1.000) | 0.434 (0.109; 0.292–0.701) |

### 5.5 L + R (horizonte de protección) — todas las semanas — escaladas y relativas

| Segmento | Modelo | n | MASE | RMSSE | WAPE | sesgo relativo |
|---|---|---|---|---|---|---|
| todos | naïve | 1593 | 0.951 (0.162; 0.766–1.283) | 0.540 (0.061; 0.459–0.653) | 0.134 (0.024; 0.097–0.188) | 0.002 (0.032; -0.035–0.086) |
| todos | naïve estacional | 1593 | 1.292 (0.103; 1.109–1.537) | 0.758 (0.043; 0.705–0.840) | 0.140 (0.012; 0.118–0.164) | 0.013 (0.014; -0.011–0.040) |
| todos | media móvil 13 | 1593 | 0.800 (0.082; 0.623–0.946) | 0.446 (0.031; 0.382–0.500) | 0.109 (0.012; 0.093–0.135) | 0.002 (0.016; -0.019–0.034) |
| todos | SES (provisional) | 1593 | 0.669 (0.108; 0.464–0.866) | 0.363 (0.043; 0.276–0.418) | 0.087 (0.010; 0.073–0.113) | -0.003 (0.017; -0.037–0.025) |
| suave | naïve | 1423 | 0.966 (0.181; 0.763–1.337) | 0.529 (0.068; 0.442–0.657) | 0.122 (0.024; 0.087–0.171) | 0.002 (0.034; -0.049–0.085) |
| suave | naïve estacional | 1423 | 1.399 (0.113; 1.198–1.664) | 0.812 (0.047; 0.750–0.913) | 0.136 (0.012; 0.115–0.159) | 0.014 (0.014; -0.009–0.040) |
| suave | media móvil 13 | 1423 | 0.854 (0.090; 0.662–1.005) | 0.466 (0.035; 0.400–0.518) | 0.105 (0.012; 0.089–0.129) | 0.002 (0.016; -0.023–0.031) |
| suave | SES (provisional) | 1423 | 0.710 (0.117; 0.488–0.916) | 0.375 (0.046; 0.285–0.435) | 0.083 (0.010; 0.069–0.107) | -0.003 (0.016; -0.036–0.024) |
| intermitente | naïve | 170 | 0.821 (0.167; 0.507–1.186) | 0.633 (0.128; 0.395–0.916) | 0.910 (0.294; 0.553–1.654) | 0.009 (0.434; -0.672–1.281) |
| intermitente | naïve estacional | 170 | 0.394 (0.113; 0.213–0.689) | 0.303 (0.087; 0.167–0.533) | 0.409 (0.128; 0.176–0.654) | -0.009 (0.152; -0.261–0.276) |
| intermitente | media móvil 13 | 170 | 0.350 (0.085; 0.196–0.473) | 0.270 (0.066; 0.153–0.367) | 0.390 (0.111; 0.194–0.587) | 0.010 (0.135; -0.256–0.250) |
| intermitente | SES (provisional) | 170 | 0.330 (0.078; 0.198–0.456) | 0.254 (0.060; 0.153–0.351) | 0.357 (0.093; 0.152–0.555) | -0.000 (0.119; -0.236–0.253) |

### 5.6 L + R (horizonte de protección) — todas las semanas — absolutas, sesgo, cobertura y MAPE informativa

| Segmento | Modelo | n | MAE | RMSE | sesgo | MAPE (inf.) |
|---|---|---|---|---|---|---|
| todos | naïve | 1593 | 58.616 (10.408; 42.723–83.066) | 146.808 (45.253; 79.902–235.565) | 0.621 (13.758; -15.847–37.191) | 0.250 (0.081; 0.165–0.473) |
| todos | naïve estacional | 1593 | 61.329 (5.607; 48.565–70.427) | 125.609 (10.600; 101.771–148.725) | 5.833 (6.193; -4.845–17.320) | 0.189 (0.047; 0.152–0.363) |
| todos | media móvil 13 | 1593 | 47.792 (5.204; 38.693–57.880) | 108.178 (14.130; 89.488–143.832) | 0.837 (7.059; -8.686–14.615) | 0.150 (0.043; 0.114–0.297) |
| todos | SES (provisional) | 1593 | 38.063 (4.379; 32.309–48.736) | 83.964 (15.953; 63.888–121.050) | -1.344 (7.273; -16.832–10.832) | 0.131 (0.041; 0.100–0.273) |
| suave | naïve | 1423 | 59.062 (11.283; 42.400–83.163) | 152.826 (47.835; 82.642–248.048) | 0.703 (16.165; -23.624–40.128) | 0.122 (0.018; 0.092–0.155) |
| suave | naïve estacional | 1423 | 65.729 (6.244; 52.164–75.486) | 132.365 (11.329; 107.346–157.397) | 6.634 (6.835; -4.425–19.284) | 0.136 (0.009; 0.121–0.156) |
| suave | media móvil 13 | 1423 | 50.695 (5.887; 41.936–61.717) | 113.871 (15.097; 94.001–151.798) | 0.954 (7.743; -11.146–14.878) | 0.096 (0.010; 0.084–0.123) |
| suave | SES (provisional) | 1423 | 40.029 (4.883; 33.318–50.722) | 88.202 (17.021; 66.532–127.715) | -1.426 (7.922; -18.188–11.277) | 0.079 (0.010; 0.066–0.106) |
| intermitente | naïve | 170 | 54.682 (17.379; 34.214–105.386) | 73.289 (31.830; 42.502–170.723) | -0.124 (25.072; -42.271–70.300) | 1.317 (0.714; 0.618–3.352) |
| intermitente | naïve estacional | 170 | 24.544 (7.456; 11.229–39.800) | 32.797 (11.000; 15.811–51.898) | -0.925 (8.943; -16.157–13.400) | 0.638 (0.422; 0.278–2.181) |
| intermitente | media móvil 13 | 170 | 23.558 (6.833; 11.775–34.153) | 31.791 (9.601; 14.763–48.335) | -0.098 (8.228; -19.377–12.378) | 0.601 (0.374; 0.271–1.778) |
| intermitente | SES (provisional) | 170 | 21.616 (6.006; 9.239–31.851) | 28.498 (8.423; 10.504–43.337) | -0.640 (7.269; -17.925–12.288) | 0.572 (0.343; 0.268–1.698) |

### 5.7 L + R (horizonte de protección) — solo objetivos sin desabasto — escaladas y relativas

| Segmento | Modelo | n | MASE | RMSSE | WAPE | sesgo relativo |
|---|---|---|---|---|---|---|
| todos | naïve | 915 | 0.761 (0.197; 0.511–1.246) | 0.440 (0.071; 0.341–0.631) | 0.086 (0.030; 0.043–0.153) | -0.017 (0.028; -0.085–0.033) |
| todos | naïve estacional | 915 | 1.473 (0.147; 1.140–1.723) | 0.880 (0.066; 0.694–0.986) | 0.145 (0.016; 0.117–0.174) | 0.020 (0.018; -0.002–0.060) |
| todos | media móvil 13 | 915 | 0.728 (0.157; 0.445–1.003) | 0.412 (0.074; 0.252–0.519) | 0.091 (0.018; 0.054–0.118) | 0.007 (0.016; -0.020–0.033) |
| todos | SES (provisional) | 915 | 0.600 (0.144; 0.387–0.882) | 0.327 (0.065; 0.214–0.426) | 0.069 (0.012; 0.041–0.088) | -0.009 (0.015; -0.034–0.020) |
| suave | naïve | 784 | 0.752 (0.228; 0.455–1.312) | 0.408 (0.079; 0.294–0.628) | 0.068 (0.028; 0.039–0.135) | -0.015 (0.033; -0.103–0.027) |
| suave | naïve estacional | 784 | 1.655 (0.179; 1.332–2.004) | 0.977 (0.079; 0.803–1.108) | 0.139 (0.015; 0.111–0.167) | 0.020 (0.019; -0.008–0.058) |
| suave | media móvil 13 | 784 | 0.790 (0.182; 0.467–1.117) | 0.434 (0.083; 0.252–0.557) | 0.084 (0.017; 0.047–0.114) | 0.006 (0.017; -0.023–0.032) |
| suave | SES (provisional) | 784 | 0.644 (0.165; 0.411–0.996) | 0.337 (0.070; 0.221–0.456) | 0.062 (0.011; 0.036–0.084) | -0.009 (0.015; -0.034–0.020) |
| intermitente | naïve | 131 | 0.798 (0.183; 0.305–1.017) | 0.617 (0.140; 0.239–0.802) | 0.900 (0.287; 0.475–1.545) | -0.031 (0.481; -0.698–1.358) |
| intermitente | naïve estacional | 131 | 0.384 (0.128; 0.137–0.672) | 0.298 (0.098; 0.109–0.520) | 0.397 (0.146; 0.191–0.682) | 0.073 (0.212; -0.287–0.486) |
| intermitente | media móvil 13 | 131 | 0.362 (0.100; 0.186–0.581) | 0.281 (0.078; 0.146–0.454) | 0.412 (0.157; 0.158–0.749) | 0.071 (0.204; -0.289–0.466) |
| intermitente | SES (provisional) | 131 | 0.338 (0.091; 0.214–0.503) | 0.262 (0.070; 0.167–0.390) | 0.369 (0.136; 0.173–0.636) | 0.041 (0.172; -0.246–0.373) |

### 5.8 L + R (horizonte de protección) — solo objetivos sin desabasto — absolutas, sesgo, cobertura y MAPE informativa

| Segmento | Modelo | n | MAE | RMSE | sesgo | MAPE (inf.) |
|---|---|---|---|---|---|---|
| todos | naïve | 915 | 31.913 (13.354; 17.559–74.197) | 76.771 (52.365; 33.265–224.113) | -6.857 (11.650; -40.899–10.448) | 0.235 (0.114; 0.094–0.604) |
| todos | naïve estacional | 915 | 53.224 (6.449; 37.166–62.349) | 113.471 (12.359; 82.989–135.088) | 6.879 (6.002; -0.803–18.717) | 0.202 (0.074; 0.122–0.460) |
| todos | media móvil 13 | 915 | 34.179 (9.406; 16.220–57.055) | 83.143 (22.420; 34.775–118.193) | 2.182 (5.903; -9.516–11.741) | 0.155 (0.071; 0.091–0.369) |
| todos | SES (provisional) | 915 | 25.767 (6.262; 12.393–42.453) | 57.503 (15.992; 27.337–96.134) | -3.541 (5.537; -14.692–6.681) | 0.133 (0.066; 0.064–0.339) |
| suave | naïve | 784 | 28.731 (14.195; 16.895–72.528) | 77.285 (56.657; 33.326–232.412) | -6.798 (15.711; -55.356–10.085) | 0.061 (0.013; 0.044–0.083) |
| suave | naïve estacional | 784 | 58.327 (6.850; 41.463–68.737) | 121.918 (12.957; 91.004–145.943) | 7.599 (7.152; -3.563–20.279) | 0.122 (0.011; 0.104–0.143) |
| suave | media móvil 13 | 784 | 36.000 (10.410; 16.214–61.185) | 88.789 (23.968; 37.035–124.725) | 2.281 (7.222; -12.488–12.352) | 0.073 (0.014; 0.041–0.095) |
| suave | SES (provisional) | 784 | 26.569 (6.905; 12.436–45.055) | 60.935 (17.329; 29.149–101.463) | -4.143 (6.701; -18.148–7.380) | 0.054 (0.010; 0.035–0.077) |
| intermitente | naïve | 131 | 49.752 (14.977; 23.449–87.833) | 64.011 (24.591; 28.630–138.865) | -3.738 (28.019; -44.937–77.167) | 1.226 (0.634; 0.598–3.352) |
| intermitente | naïve estacional | 131 | 21.982 (8.307; 10.607–39.905) | 28.822 (11.795; 12.090–53.150) | 2.893 (10.659; -16.464–19.968) | 0.649 (0.435; 0.211–2.181) |
| intermitente | media móvil 13 | 131 | 23.065 (9.194; 8.087–41.574) | 29.656 (12.196; 9.380–52.650) | 2.659 (11.396; -21.440–25.871) | 0.627 (0.390; 0.278–1.778) |
| intermitente | SES (provisional) | 131 | 20.727 (8.286; 8.792–35.300) | 25.692 (10.388; 10.385–45.173) | 1.156 (9.596; -18.254–18.614) | 0.587 (0.361; 0.254–1.698) |

La cobertura no se informa en `L + R`: los intervalos son semanales y no existe una regla documentada para agregarlos al horizonte de protección.

## 6. Comparación de reglas de población (efecto del sesgo de supervivencia)

Misma ejecución con las dos reglas: **vigencia al corte (`DT-087`)** (la de este informe) y **literal de U3**. Diferencias descriptivas, `SYNTHETIC`; sin conclusiones de promoción ni elección de métrica.

Población por corte — vigencia: 100 (2024-03-27 a 2025-03-26); 95 (2025-04-23 a 2025-06-18); U3 literal: 95 (2024-03-27 a 2025-06-18).

| Horizonte | Vista | Segmento | n vigencia | n U3 literal |
|---|---|---|---|---|
| h = 1 (semana 1) | todas las semanas | todos | 1685 | 1615 |
| h = 1 (semana 1) | todas las semanas | suave | 1430 | 1360 |
| h = 1 (semana 1) | todas las semanas | intermitente | 238 | 238 |
| h = 1 (semana 1) | todas las semanas | irregular | 17 | 17 |
| h = 1 (semana 1) | solo objetivos sin desabasto | todos | 1395 | 1335 |
| h = 1 (semana 1) | solo objetivos sin desabasto | suave | 1239 | 1179 |
| h = 1 (semana 1) | solo objetivos sin desabasto | intermitente | 156 | 156 |
| L + R (horizonte de protección) | todas las semanas | todos | 1593 | 1530 |
| L + R (horizonte de protección) | todas las semanas | suave | 1423 | 1360 |
| L + R (horizonte de protección) | todas las semanas | intermitente | 170 | 170 |
| L + R (horizonte de protección) | solo objetivos sin desabasto | todos | 915 | 873 |
| L + R (horizonte de protección) | solo objetivos sin desabasto | suave | 784 | 742 |
| L + R (horizonte de protección) | solo objetivos sin desabasto | intermitente | 131 | 131 |

Media entre cortes, todos los segmentos (celda: vigencia / U3 literal):

| Horizonte | Vista | Modelo | MASE | RMSSE | WAPE | MAE | sesgo relativo |
|---|---|---|---|---|---|---|---|
| h = 1 (semana 1) | todas las semanas | naïve | 0.981 / 0.985 | 0.563 / 0.564 | 0.132 / 0.133 | 11.132 / 11.418 | -0.011 / -0.011 |
| h = 1 (semana 1) | todas las semanas | naïve estacional | 1.688 / 1.673 | 0.987 / 0.973 | 0.199 / 0.198 | 16.905 / 17.052 | 0.001 / -0.004 |
| h = 1 (semana 1) | todas las semanas | media móvil 13 | 0.983 / 0.979 | 0.555 / 0.552 | 0.135 / 0.136 | 11.417 / 11.710 | -0.010 / -0.010 |
| h = 1 (semana 1) | todas las semanas | SES (provisional) | 0.886 / 0.888 | 0.492 / 0.492 | 0.119 / 0.121 | 10.113 / 10.370 | -0.014 / -0.015 |
| h = 1 (semana 1) | solo objetivos sin desabasto | naïve | 0.783 / 0.785 | 0.472 / 0.474 | 0.092 / 0.093 | 8.448 / 8.702 | -0.040 / -0.041 |
| h = 1 (semana 1) | solo objetivos sin desabasto | naïve estacional | 1.623 / 1.610 | 0.983 / 0.973 | 0.172 / 0.171 | 15.831 / 16.012 | -0.033 / -0.038 |
| h = 1 (semana 1) | solo objetivos sin desabasto | media móvil 13 | 0.822 / 0.812 | 0.491 / 0.487 | 0.107 / 0.108 | 9.800 / 10.082 | -0.043 / -0.043 |
| h = 1 (semana 1) | solo objetivos sin desabasto | SES (provisional) | 0.705 / 0.702 | 0.416 / 0.415 | 0.090 / 0.091 | 8.320 / 8.553 | -0.052 / -0.052 |
| L + R (horizonte de protección) | todas las semanas | naïve | 0.951 / 0.958 | 0.540 / 0.543 | 0.134 / 0.136 | 58.616 / 60.113 | 0.002 / 0.002 |
| L + R (horizonte de protección) | todas las semanas | naïve estacional | 1.292 / 1.278 | 0.758 / 0.742 | 0.140 / 0.137 | 61.329 / 60.923 | 0.013 / 0.009 |
| L + R (horizonte de protección) | todas las semanas | media móvil 13 | 0.800 / 0.799 | 0.446 / 0.444 | 0.109 / 0.110 | 47.792 / 48.844 | 0.002 / 0.002 |
| L + R (horizonte de protección) | todas las semanas | SES (provisional) | 0.669 / 0.672 | 0.363 / 0.363 | 0.087 / 0.088 | 38.063 / 39.027 | -0.003 / -0.003 |
| L + R (horizonte de protección) | solo objetivos sin desabasto | naïve | 0.761 / 0.768 | 0.440 / 0.444 | 0.086 / 0.088 | 31.913 / 33.120 | -0.017 / -0.018 |
| L + R (horizonte de protección) | solo objetivos sin desabasto | naïve estacional | 1.473 / 1.479 | 0.880 / 0.879 | 0.145 / 0.143 | 53.224 / 53.331 | 0.020 / 0.015 |
| L + R (horizonte de protección) | solo objetivos sin desabasto | media móvil 13 | 0.728 / 0.723 | 0.412 / 0.410 | 0.091 / 0.092 | 34.179 / 35.144 | 0.007 / 0.006 |
| L + R (horizonte de protección) | solo objetivos sin desabasto | SES (provisional) | 0.600 / 0.600 | 0.327 / 0.327 | 0.069 / 0.070 | 25.767 / 26.592 | -0.009 / -0.009 |

## 7. Salidas para `DT-078` (sin Nivel 2) y datos detallados

`f5a-observations.csv` contiene, por modelo × corte × serie × horizonte, el error y su versión escalada (MASE/RMSSE de la serie-corte) y la marca de conjunto común; con ello se calculan después el acuerdo serie-corte y el Spearman entre modelos cuando F5b aporte el indicador de Nivel 2. Junto a este informe se versiona un JSON resumido (mismo nombre, extensión `.json`): metadatos, configuración, huella y agregados entre cortes por modelo × segmento × horizonte × vista, sin tablas por corte (`DT-073`). Los datos detallados (`f5a-observations.csv`, `f5a-series-cuts.csv` y `f5a-summary.json`, con las métricas por corte) no se versionan: se regeneran de forma determinista con el comando de §1 en el directorio de salida (`ml/out/`, ignorado por Git). Huellas de los CSV:

- `f5a-observations.csv`: `f52abd6a91c9d73b62ad293b95ef078c74c9bbb7019cf5e0d00cf956d1f875b3`
- `f5a-series-cuts.csv`: `b7d18a0fee5d45bc840ef21db260bff4c0f45682aca051fab7b71db0da61a849`
