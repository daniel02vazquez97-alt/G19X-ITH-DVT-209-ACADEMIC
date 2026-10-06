# Fase 5 — F5c: modelos candidatos, estudio de `DT-011` e intervalos (US-055)

> **SYNTHETIC.** Todo se calcula con el dataset sintético. Los 17 cortes de `DT-075` y el simulador de F5b; el
> *holdout* no se lee. **No recomienda ni promueve ningún modelo** (`DT-084`): la tabla de criterios es
> automática e informativa. Las conclusiones que usan la demanda latente solo valen para datos `SYNTHETIC`.
> Generado por `python -m ml candidates`; no editar a mano.

## 1. Ejecución

| Campo | Valor |
|---|---|
| Fecha | 2026-10-06 |
| Comando | `PYTHONPATH=backend python -m ml candidates --data data/synthetic/output --out ml/out --report docs/reports/fase5-f5c-candidatos-sintetico.md --generated-on 2026-10-06 --workers 2 --reuse-cache ml/out/f5c-cache/17e2ff08bfbc635f` |
| Dataset | `ds-6c8ad65b4999` (SYNTHETIC) |
| Código | `ml` 0.2.0; candidatos 0.1.0-provisional |
| Motor U1 | 0.1.0; versiones vistas en las decisiones: 0.1.0 |
| Commit | `cd3630da845aa6ce2ffaace297a67cd92bd1f57b` (cambios sin commit en archivos versionados: False) |
| Python | 3.11.16 |
| Aleatoriedad | none (no randomness) |
| `results_sha256` | `1ce5ea29580f8c6fdb2b1f029cef0292f73b55385c25d19d988bb696c03fb54d` |

## 2. Criterios y valores provisionales

Criterios del responsable (`DT-091`, `DT-093`, `ACEPTADA`, provisionales):

- bias: absolute relative bias at L+R ≤ 0.1; segments ≥ 10 products not worse than 0.05
- coverage: nominal 0.8; calibrated if within [0.75, 0.85] per horizon on the late cuts (label of the band only)
- cuts: aggregate and ≥ ⌈2/3⌉ of the comparable cuts, minimum 5; fewer → not conclusive
- level2: units short ≤ +2%, fill rate ≥ −0.002, average inventory ≤ +5%
- primary: MASE at LR; h = 1 secondary (DT-093 point 1)
- segments: no segment with ≥ 10 products worse than 5%
- status: ACEPTADA (DT-091, DT-093), provisional, SYNTHETIC

Valores provisionales de esta unidad (`PROPUESTA`, configurables):

- Candidatos: rejillas y arranques en la configuración del JSON (`candidates`); mínimo de 25 semanas (104 para Holt-Winters); intervalo nearest-rank 10/90 de los errores dentro de muestra, como el SES de F5a.
- Comparación por pares con el baseline oficial (media móvil 13): un corte es comparable si ambos tienen observación con dato real completo; agregado = media de las métricas por corte; un segmento bloquea si tiene en promedio ≥ 10 series por corte comparable; el sesgo se compara en valor absoluto.
- Nivel 2: los criterios se aplican al periodo completo; el periodo sin calentamiento se informa al lado.
- SES y los baselines conservan la cadencia de F5b (pronóstico recalculado en cada decisión), para que sus resultados no cambien; los candidatos reoptimizan cada 4 decisiones (`DT-093` punto 9).
- US-055: cortes tardíos 2024-11-06, 2024-12-04, 2025-01-01, 2025-01-29, 2025-02-26, 2025-03-26, 2025-04-23, 2025-05-21, 2025-06-18; calibración por factor de ensanche con los cortes cuya ventana de evaluación termina antes del corte medido.
- `DT-011`: modelos estudiados media móvil 13, SES (provisional), Holt-Winters, TSB (los dos mejores candidatos por Nivel 1: menor MASE en `L + R` relativo al baseline oficial).

## 3. Elegibilidad y sustituciones

| Candidato | Pronósticos propios | No elegible | Sustituido por el baseline oficial (valor inválido) |
|---|---|---|---|
| Holt | 1607 | 0 | 78 |
| Holt-Winters | 614 | 1000 | 71 |
| Croston | 1685 | 0 | 0 |
| SBA | 1685 | 0 | 0 |
| TSB | 1685 | 0 | 0 |

Holt-Winters solo es elegible con 104 semanas de entrenamiento: cortes de las semanas 104 a 128. Una sustitución ocurre cuando un valor no cruza la frontera de `DT-074` (sobre todo, pronósticos negativos de Holt y Holt-Winters en series con tendencia descendente); la serie usa entonces el baseline oficial y cuenta como observación del candidato.

## 4. Nivel 1 frente al baseline oficial (SYNTHETIC)

Media de las métricas por corte en el conjunto común de cada par (modelo, media móvil 13). MASE en `L + R` es la métrica primaria (`DT-090`, `DT-093`); `h = 1` es secundaria.

| Modelo | Horizonte | Vista | Cortes | Series por corte | MASE | MASE media móvil | Relativo | RMSSE | WAPE | Sesgo relativo | Cobertura (semana 1) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| naïve | L + R | todas | 17 | 93.7 | 0.951 | 0.800 | +18.8% | 0.540 | 0.134 | 0.002 | — |
| naïve | L + R | sin desabasto | 17 | 53.8 | 0.761 | 0.728 | +4.5% | 0.440 | 0.086 | -0.017 | — |
| naïve | h = 1 | todas | 17 | 99.1 | 0.981 | 0.983 | -0.3% | 0.563 | 0.132 | -0.011 | 0.841 |
| naïve | h = 1 | sin desabasto | 17 | 82.1 | 0.783 | 0.822 | -4.8% | 0.472 | 0.092 | -0.040 | 0.883 |
| naïve estacional | L + R | todas | 17 | 93.7 | 1.292 | 0.800 | +61.5% | 0.758 | 0.140 | 0.013 | — |
| naïve estacional | L + R | sin desabasto | 17 | 53.8 | 1.473 | 0.728 | +102.3% | 0.880 | 0.145 | 0.020 | — |
| naïve estacional | h = 1 | todas | 17 | 99.1 | 1.688 | 0.983 | +71.6% | 0.987 | 0.199 | 0.001 | 0.836 |
| naïve estacional | h = 1 | sin desabasto | 17 | 82.1 | 1.623 | 0.822 | +97.5% | 0.983 | 0.172 | -0.033 | 0.864 |
| media móvil 13 | L + R | todas | 17 | 93.7 | 0.800 | 0.800 | +0.0% | 0.446 | 0.109 | 0.002 | — |
| media móvil 13 | L + R | sin desabasto | 17 | 53.8 | 0.728 | 0.728 | +0.0% | 0.412 | 0.091 | 0.007 | — |
| media móvil 13 | h = 1 | todas | 17 | 99.1 | 0.983 | 0.983 | +0.0% | 0.555 | 0.135 | -0.010 | 0.831 |
| media móvil 13 | h = 1 | sin desabasto | 17 | 82.1 | 0.822 | 0.822 | +0.0% | 0.491 | 0.107 | -0.043 | 0.853 |
| SES (provisional) | L + R | todas | 17 | 93.7 | 0.669 | 0.800 | -16.4% | 0.363 | 0.087 | -0.003 | — |
| SES (provisional) | L + R | sin desabasto | 17 | 53.8 | 0.600 | 0.728 | -17.6% | 0.327 | 0.069 | -0.009 | — |
| SES (provisional) | h = 1 | todas | 17 | 99.1 | 0.886 | 0.983 | -9.9% | 0.492 | 0.119 | -0.014 | 0.814 |
| SES (provisional) | h = 1 | sin desabasto | 17 | 82.1 | 0.705 | 0.822 | -14.2% | 0.416 | 0.090 | -0.052 | 0.840 |
| Holt | L + R | todas | 17 | 93.7 | 0.753 | 0.800 | -5.9% | 0.423 | 0.096 | 0.012 | — |
| Holt | L + R | sin desabasto | 17 | 53.8 | 0.651 | 0.728 | -10.6% | 0.366 | 0.069 | -0.019 | — |
| Holt | h = 1 | todas | 17 | 99.1 | 0.911 | 0.983 | -7.4% | 0.511 | 0.116 | -0.003 | 0.814 |
| Holt | h = 1 | sin desabasto | 17 | 82.1 | 0.710 | 0.822 | -13.6% | 0.423 | 0.082 | -0.046 | 0.843 |
| Holt-Winters | L + R | todas | 7 | 91.9 | 0.643 | 0.787 | -18.3% | 0.338 | 0.074 | -0.001 | — |
| Holt-Winters | L + R | sin desabasto | 7 | 51.7 | 0.582 | 0.622 | -6.3% | 0.297 | 0.048 | -0.016 | — |
| Holt-Winters | h = 1 | todas | 7 | 97.9 | 1.088 | 0.895 | +21.5% | 0.601 | 0.141 | 0.001 | 0.669 |
| Holt-Winters | h = 1 | sin desabasto | 7 | 80.9 | 0.947 | 0.752 | +26.0% | 0.529 | 0.099 | -0.049 | 0.687 |
| Croston | L + R | todas | 17 | 93.7 | 0.688 | 0.800 | -14.0% | 0.374 | 0.090 | -0.002 | — |
| Croston | L + R | sin desabasto | 17 | 53.8 | 0.622 | 0.728 | -14.6% | 0.340 | 0.073 | -0.006 | — |
| Croston | h = 1 | todas | 17 | 99.1 | 4.989 | 0.983 | +407.3% | 1.027 | 0.270 | 0.135 | 0.815 |
| Croston | h = 1 | sin desabasto | 17 | 82.1 | 0.729 | 0.822 | -11.2% | 0.431 | 0.093 | -0.050 | 0.839 |
| SBA | L + R | todas | 17 | 93.7 | 0.903 | 0.800 | +12.8% | 0.473 | 0.105 | -0.052 | — |
| SBA | L + R | sin desabasto | 17 | 53.8 | 0.948 | 0.728 | +30.2% | 0.470 | 0.087 | -0.051 | — |
| SBA | h = 1 | todas | 17 | 99.1 | 4.617 | 0.983 | +369.5% | 1.057 | 0.271 | 0.063 | 0.811 |
| SBA | h = 1 | sin desabasto | 17 | 82.1 | 1.053 | 0.822 | +28.1% | 0.576 | 0.121 | -0.096 | 0.832 |
| TSB | L + R | todas | 17 | 93.7 | 0.687 | 0.800 | -14.2% | 0.373 | 0.090 | -0.003 | — |
| TSB | L + R | sin desabasto | 17 | 53.8 | 0.619 | 0.728 | -15.0% | 0.339 | 0.073 | -0.007 | — |
| TSB | h = 1 | todas | 17 | 99.1 | 0.902 | 0.983 | -8.3% | 0.503 | 0.121 | -0.014 | 0.815 |
| TSB | h = 1 | sin desabasto | 17 | 82.1 | 0.728 | 0.822 | -11.5% | 0.430 | 0.093 | -0.051 | 0.839 |

Por segmento (MASE en `L + R`, todas las semanas; relativo a la media móvil en el mismo conjunto):

| Modelo | Segmento | Cortes | Series por corte | MASE | MASE media móvil | Relativo | Sesgo relativo |
|---|---|---|---|---|---|---|---|
| naïve | intermitente | 17 | 10.0 | 0.821 | 0.350 | +134.4% | 0.009 |
| naïve | suave | 17 | 83.7 | 0.966 | 0.854 | +13.1% | 0.002 |
| naïve estacional | intermitente | 17 | 10.0 | 0.394 | 0.350 | +12.4% | -0.009 |
| naïve estacional | suave | 17 | 83.7 | 1.399 | 0.854 | +63.9% | 0.014 |
| SES (provisional) | intermitente | 17 | 10.0 | 0.330 | 0.350 | -5.9% | -0.000 |
| SES (provisional) | suave | 17 | 83.7 | 0.710 | 0.854 | -16.9% | -0.003 |
| Holt | intermitente | 17 | 10.0 | 0.511 | 0.350 | +45.7% | 0.211 |
| Holt | suave | 17 | 83.7 | 0.782 | 0.854 | -8.4% | 0.009 |
| Holt-Winters | intermitente | 7 | 10.0 | 0.377 | 0.338 | +11.4% | 0.069 |
| Holt-Winters | suave | 7 | 81.9 | 0.675 | 0.842 | -19.7% | -0.002 |
| Croston | intermitente | 17 | 10.0 | 0.323 | 0.350 | -7.9% | 0.011 |
| Croston | suave | 17 | 83.7 | 0.732 | 0.854 | -14.3% | -0.002 |
| SBA | intermitente | 17 | 10.0 | 0.328 | 0.350 | -6.4% | -0.025 |
| SBA | suave | 17 | 83.7 | 0.972 | 0.854 | +13.8% | -0.052 |
| TSB | intermitente | 17 | 10.0 | 0.325 | 0.350 | -7.2% | 0.003 |
| TSB | suave | 17 | 83.7 | 0.730 | 0.854 | -14.5% | -0.003 |

## 5. Nivel 2 por rama, segmento y periodo (SYNTHETIC)

Series simuladas: 95. Misma `engine_version` en todas las ramas. Las ramas «(b)» y «(c)» son las estrategias de `DT-011` (§8).

### Periodo completo (2024-03-28 a 2025-09-24)

| Segmento | Rama | Series | Unidades faltantes | Días con desabasto | *Fill rate* | Servicio por ciclos | Inventario medio | Relativo a media móvil | Órdenes |
|---|---|---|---|---|---|---|---|---|---|
| todos | naïve | 95 | 5,137 | 336 | 0.9925 | 0.9811 | 19,236.7 | 1.065 | 4372 |
| todos | naïve estacional | 95 | 11,953 | 755 | 0.9826 | 0.9437 | 17,056.4 | 0.944 | 4689 |
| todos | media móvil 13 | 95 | 3,882 | 255 | 0.9943 | 0.9841 | 18,062.9 | 1.000 | 4714 |
| todos | SES (provisional) | 95 | 3,860 | 255 | 0.9944 | 0.9842 | 17,892.9 | 0.991 | 4715 |
| todos | Holt | 95 | 5,490 | 344 | 0.9920 | 0.9798 | 18,659.0 | 1.033 | 4529 |
| todos | Holt-Winters | 95 | 4,218 | 259 | 0.9939 | 0.9837 | 18,276.1 | 1.012 | 4698 |
| todos | Croston | 95 | 4,271 | 265 | 0.9938 | 0.9835 | 17,776.0 | 0.984 | 4723 |
| todos | SBA | 95 | 4,928 | 333 | 0.9928 | 0.9765 | 15,319.6 | 0.848 | 4733 |
| todos | TSB | 95 | 4,170 | 257 | 0.9939 | 0.9842 | 17,771.3 | 0.984 | 4713 |
| todos | media móvil 13 (b) | 95 | 3,314 | 228 | 0.9952 | 0.9858 | 18,432.2 | 1.020 | 4712 |
| todos | media móvil 13 (c) | 95 | 3,306 | 231 | 0.9952 | 0.9857 | 18,440.6 | 1.021 | 4717 |
| todos | SES (provisional) (b) | 95 | 3,187 | 220 | 0.9954 | 0.9864 | 18,370.1 | 1.017 | 4718 |
| todos | SES (provisional) (c) | 95 | 3,153 | 216 | 0.9954 | 0.9866 | 18,377.0 | 1.017 | 4716 |
| todos | Holt-Winters (b) | 95 | 3,493 | 236 | 0.9949 | 0.9849 | 18,425.5 | 1.020 | 4702 |
| todos | Holt-Winters (c) | 95 | 3,511 | 239 | 0.9949 | 0.9849 | 18,431.9 | 1.020 | 4708 |
| todos | TSB (b) | 95 | 3,168 | 216 | 0.9954 | 0.9866 | 18,404.2 | 1.019 | 4722 |
| todos | TSB (c) | 95 | 3,173 | 215 | 0.9954 | 0.9870 | 18,393.9 | 1.018 | 4722 |
| intermitente | naïve | 10 | 68 | 10 | 0.9935 | 0.9897 | 1,498.5 | 2.037 | 126 |
| intermitente | naïve estacional | 10 | 789 | 69 | 0.9240 | 0.9410 | 692.9 | 0.942 | 256 |
| intermitente | media móvil 13 | 10 | 605 | 56 | 0.9418 | 0.9487 | 735.8 | 1.000 | 263 |
| intermitente | SES (provisional) | 10 | 496 | 52 | 0.9522 | 0.9487 | 719.6 | 0.978 | 269 |
| intermitente | Holt | 10 | 298 | 29 | 0.9713 | 0.9731 | 1,046.0 | 1.422 | 167 |
| intermitente | Holt-Winters | 10 | 521 | 49 | 0.9498 | 0.9551 | 762.9 | 1.037 | 258 |
| intermitente | Croston | 10 | 573 | 55 | 0.9448 | 0.9449 | 693.2 | 0.942 | 280 |
| intermitente | SBA | 10 | 644 | 64 | 0.9380 | 0.9372 | 674.7 | 0.917 | 280 |
| intermitente | TSB | 10 | 547 | 52 | 0.9473 | 0.9500 | 713.5 | 0.970 | 269 |
| suave | naïve | 85 | 5,069 | 326 | 0.9925 | 0.9801 | 17,738.2 | 1.024 | 4246 |
| suave | naïve estacional | 85 | 11,164 | 686 | 0.9835 | 0.9440 | 16,363.5 | 0.944 | 4433 |
| suave | media móvil 13 | 85 | 3,277 | 199 | 0.9952 | 0.9882 | 17,327.1 | 1.000 | 4451 |
| suave | SES (provisional) | 85 | 3,364 | 203 | 0.9950 | 0.9884 | 17,173.3 | 0.991 | 4446 |
| suave | Holt | 85 | 5,192 | 315 | 0.9923 | 0.9805 | 17,613.0 | 1.017 | 4362 |
| suave | Holt-Winters | 85 | 3,697 | 210 | 0.9945 | 0.9870 | 17,513.2 | 1.011 | 4440 |
| suave | Croston | 85 | 3,698 | 210 | 0.9945 | 0.9881 | 17,082.9 | 0.986 | 4443 |
| suave | SBA | 85 | 4,284 | 269 | 0.9937 | 0.9811 | 14,644.9 | 0.845 | 4453 |
| suave | TSB | 85 | 3,623 | 205 | 0.9946 | 0.9882 | 17,057.8 | 0.984 | 4444 |

### Sin las semanas de calentamiento (2024-05-23 a 2025-09-24)

| Segmento | Rama | Series | Unidades faltantes | Días con desabasto | *Fill rate* | Servicio por ciclos | Inventario medio | Relativo a media móvil | Órdenes |
|---|---|---|---|---|---|---|---|---|---|
| todos | naïve | 95 | 2,540 | 168 | 0.9959 | 0.9877 | 19,492.7 | 1.066 | 3928 |
| todos | naïve estacional | 95 | 8,375 | 554 | 0.9864 | 0.9481 | 17,080.1 | 0.934 | 4226 |
| todos | media móvil 13 | 95 | 1,166 | 87 | 0.9981 | 0.9910 | 18,280.5 | 1.000 | 4244 |
| todos | SES (provisional) | 95 | 1,180 | 89 | 0.9981 | 0.9910 | 18,098.0 | 0.990 | 4254 |
| todos | Holt | 95 | 2,931 | 181 | 0.9952 | 0.9859 | 18,895.0 | 1.034 | 4071 |
| todos | Holt-Winters | 95 | 1,502 | 91 | 0.9976 | 0.9905 | 18,518.1 | 1.013 | 4228 |
| todos | Croston | 95 | 1,496 | 96 | 0.9976 | 0.9904 | 17,972.4 | 0.983 | 4262 |
| todos | SBA | 95 | 1,980 | 153 | 0.9968 | 0.9833 | 15,334.8 | 0.839 | 4269 |
| todos | TSB | 95 | 1,395 | 88 | 0.9977 | 0.9911 | 17,973.3 | 0.983 | 4248 |
| todos | media móvil 13 (b) | 95 | 835 | 71 | 0.9986 | 0.9922 | 18,574.6 | 1.016 | 4241 |
| todos | media móvil 13 (c) | 95 | 824 | 74 | 0.9987 | 0.9920 | 18,583.7 | 1.017 | 4243 |
| todos | SES (provisional) (b) | 95 | 720 | 65 | 0.9988 | 0.9926 | 18,519.2 | 1.013 | 4243 |
| todos | SES (provisional) (c) | 95 | 698 | 61 | 0.9989 | 0.9929 | 18,531.9 | 1.014 | 4243 |
| todos | Holt-Winters (b) | 95 | 1,014 | 79 | 0.9984 | 0.9911 | 18,567.2 | 1.016 | 4231 |
| todos | Holt-Winters (c) | 95 | 1,029 | 82 | 0.9983 | 0.9911 | 18,573.9 | 1.016 | 4234 |
| todos | TSB (b) | 95 | 701 | 61 | 0.9989 | 0.9929 | 18,546.7 | 1.015 | 4250 |
| todos | TSB (c) | 95 | 706 | 60 | 0.9989 | 0.9934 | 18,537.6 | 1.014 | 4251 |
| intermitente | naïve | 10 | 42 | 6 | 0.9955 | 0.9929 | 1,570.8 | 2.150 | 106 |
| intermitente | naïve estacional | 10 | 737 | 64 | 0.9211 | 0.9400 | 683.3 | 0.935 | 240 |
| intermitente | media móvil 13 | 10 | 559 | 50 | 0.9402 | 0.9486 | 730.4 | 1.000 | 242 |
| intermitente | SES (provisional) | 10 | 468 | 47 | 0.9499 | 0.9486 | 715.1 | 0.979 | 248 |
| intermitente | Holt | 10 | 272 | 25 | 0.9709 | 0.9743 | 1,072.0 | 1.468 | 144 |
| intermitente | Holt-Winters | 10 | 475 | 43 | 0.9492 | 0.9557 | 760.7 | 1.041 | 237 |
| intermitente | Croston | 10 | 545 | 50 | 0.9417 | 0.9443 | 685.8 | 0.939 | 259 |
| intermitente | SBA | 10 | 616 | 59 | 0.9341 | 0.9357 | 665.6 | 0.911 | 260 |
| intermitente | TSB | 10 | 519 | 47 | 0.9444 | 0.9500 | 708.3 | 0.970 | 246 |
| suave | naïve | 85 | 2,498 | 162 | 0.9959 | 0.9871 | 17,921.9 | 1.021 | 3822 |
| suave | naïve estacional | 85 | 7,638 | 490 | 0.9874 | 0.9491 | 16,396.8 | 0.934 | 3986 |
| suave | media móvil 13 | 85 | 607 | 37 | 0.9990 | 0.9960 | 17,550.1 | 1.000 | 4002 |
| suave | SES (provisional) | 85 | 712 | 42 | 0.9988 | 0.9960 | 17,382.9 | 0.990 | 4006 |
| suave | Holt | 85 | 2,659 | 156 | 0.9956 | 0.9872 | 17,823.0 | 1.016 | 3927 |
| suave | Holt-Winters | 85 | 1,027 | 48 | 0.9983 | 0.9946 | 17,757.4 | 1.012 | 3991 |
| suave | Croston | 85 | 951 | 46 | 0.9984 | 0.9958 | 17,286.6 | 0.985 | 4003 |
| suave | SBA | 85 | 1,364 | 94 | 0.9977 | 0.9889 | 14,669.2 | 0.836 | 4009 |
| suave | TSB | 85 | 876 | 41 | 0.9986 | 0.9960 | 17,265.0 | 0.984 | 4002 |

Sustituciones por el baseline oficial en las decisiones del simulador (`DT-093` punto 11):

| Rama | No elegible | Valor inválido |
|---|---|---|
| Holt | 0 | 215 |
| Holt-Winters | 3800 | 93 |
| Holt-Winters (b) | 3864 | 101 |
| Holt-Winters (c) | 3800 | 99 |

## 6. Cruce informativo con el Nivel 1 (`DT-078`)

Acuerdo por serie y corte entre la métrica de Nivel 1 y las unidades faltantes de la ventana, sobre los nueve modelos; «con inventario»: la rama preferida no supera el inventario medio de la otra más allá de la tolerancia.

| Tolerancia | Horizonte | Métrica | Pares | Empates | Acuerdo | Acuerdo con restricción de inventario |
|---|---|---|---|---|---|---|
| 0% | h = 1 | MASE | 6591 | 43409 | 0.573 | 0.136 |
| 0% | h = 1 | RMSSE | 6591 | 43409 | 0.573 | 0.136 |
| 0% | h = 1 | WAPE | 5860 | 41432 | 0.595 | 0.140 |
| 0% | L + R | MASE | 6621 | 43127 | 0.614 | 0.162 |
| 0% | L + R | RMSSE | 6621 | 43127 | 0.614 | 0.162 |
| 0% | L + R | WAPE | 6621 | 43127 | 0.614 | 0.162 |
| 5% | h = 1 | MASE | 6591 | 43409 | 0.573 | 0.170 |
| 5% | h = 1 | RMSSE | 6591 | 43409 | 0.573 | 0.170 |
| 5% | h = 1 | WAPE | 5860 | 41432 | 0.595 | 0.174 |
| 5% | L + R | MASE | 6621 | 43127 | 0.614 | 0.201 |
| 5% | L + R | RMSSE | 6621 | 43127 | 0.614 | 0.201 |
| 5% | L + R | WAPE | 6621 | 43127 | 0.614 | 0.201 |

Spearman entre modelos por corte (métrica agregada frente a unidades faltantes):

| Conjunto | Horizonte | Métrica | ρ medio | mín | máx | Cortes |
|---|---|---|---|---|---|---|
| los nueve | h = 1 | MASE | 0.696 | 0.458 | 0.867 | 7 |
| los nueve | h = 1 | RMSSE | 0.749 | 0.633 | 0.817 | 7 |
| los nueve | h = 1 | WAPE | 0.391 | 0.067 | 0.833 | 7 |
| los nueve | L + R | MASE | 0.745 | 0.617 | 0.867 | 7 |
| los nueve | L + R | RMSSE | 0.702 | 0.533 | 0.817 | 7 |
| los nueve | L + R | WAPE | 0.625 | 0.458 | 0.833 | 7 |
| sin Holt-Winters | h = 1 | MASE | 0.622 | 0.286 | 0.881 | 17 |
| sin Holt-Winters | h = 1 | RMSSE | 0.637 | 0.286 | 0.881 | 17 |
| sin Holt-Winters | h = 1 | WAPE | 0.422 | 0.098 | 0.881 | 17 |
| sin Holt-Winters | L + R | MASE | 0.650 | 0.190 | 0.994 | 17 |
| sin Holt-Winters | L + R | RMSSE | 0.645 | 0.095 | 0.994 | 17 |
| sin Holt-Winters | L + R | WAPE | 0.588 | -0.095 | 0.929 | 17 |

## 7. Criterios por modelo (cumple / no cumple, sin recomendación)

Automático, frente a la media móvil de 13 semanas con la estrategia (a). Incluye SES, el candidato más fuerte de `DT-089`. «Informativo»: periodo sin calentamiento, no decide.

**Cumplen todos los criterios que deciden:** SES (provisional). Es un hecho del cálculo, no una recomendación: sin G2 ni G3 no se promueve nada (`DT-084`).

### SES (provisional)

| Criterio | Valor | Umbral | Resultado |
|---|---|---|---|
| N1: mejora agregada de MASE en L + R | candidate: 0.669; comparable_cuts: 17; official_baseline: 0.800 | candidato < baseline oficial | CUMPLE |
| N1: mejora en ⌈2/3⌉ de los cortes comparables (mínimo 5) | comparable_cuts: 17; improved: 17; needed: 12 | ≥ 12 de 17 | CUMPLE |
| N1: ningún segmento de ≥ 10 productos empeora más de un 5 % en MASE | intermitente: -0.059; suave: -0.169 | cambio relativo ≤ 5% en segmentos que bloquean | CUMPLE |
| Sesgo relativo medio en L + R dentro de ±0,10 | candidate: -0.003; official_baseline: 0.002 | valor absoluto ≤ 0.1 | CUMPLE |
| Sesgo por segmento de ≥ 10 productos no peor en más de 0,05 | intermitente: -0.010; suave: 0.001 | aumento del valor absoluto del sesgo ≤ 0.05 | CUMPLE |
| N2 (FULL): unidades faltantes no peores en más de un 2 % | candidate: 3,860.000; official_baseline: 3,882.000; relative: -0.006 | ≤ 3,959.6 | CUMPLE |
| N2 (FULL): fill rate no peor en más de 0,2 puntos | candidate: 0.994; official_baseline: 0.994 | ≥ 0.9923 | CUMPLE |
| N2 (FULL): inventario medio como máximo +5 % | candidate: 17,892.927; official_baseline: 18,062.866; relative: 0.991 | ≤ 1.05 × baseline | CUMPLE |
| N2 (NO_WARMUP): unidades faltantes no peores en más de un 2 % (informativo) | candidate: 1,180.000; official_baseline: 1,166.000; relative: 0.012 | ≤ 1,189.3 | CUMPLE |
| N2 (NO_WARMUP): fill rate no peor en más de 0,2 puntos (informativo) | candidate: 0.998; official_baseline: 0.998 | ≥ 0.9961 | CUMPLE |
| N2 (NO_WARMUP): inventario medio como máximo +5 % (informativo) | candidate: 18,097.982; official_baseline: 18,280.539; relative: 0.990 | ≤ 1.05 × baseline | CUMPLE |

Veredicto: cumple todos los criterios que deciden (sin recomendación ni promoción).

### Holt

| Criterio | Valor | Umbral | Resultado |
|---|---|---|---|
| N1: mejora agregada de MASE en L + R | candidate: 0.753; comparable_cuts: 17; official_baseline: 0.800 | candidato < baseline oficial | CUMPLE |
| N1: mejora en ⌈2/3⌉ de los cortes comparables (mínimo 5) | comparable_cuts: 17; improved: 15; needed: 12 | ≥ 12 de 17 | CUMPLE |
| N1: ningún segmento de ≥ 10 productos empeora más de un 5 % en MASE | intermitente: 0.457; suave: -0.084 | cambio relativo ≤ 5% en segmentos que bloquean | NO CUMPLE |
| Sesgo relativo medio en L + R dentro de ±0,10 | candidate: 0.012; official_baseline: 0.002 | valor absoluto ≤ 0.1 | CUMPLE |
| Sesgo por segmento de ≥ 10 productos no peor en más de 0,05 | intermitente: 0.201; suave: 0.007 | aumento del valor absoluto del sesgo ≤ 0.05 | NO CUMPLE |
| N2 (FULL): unidades faltantes no peores en más de un 2 % | candidate: 5,490.000; official_baseline: 3,882.000; relative: 0.414 | ≤ 3,959.6 | NO CUMPLE |
| N2 (FULL): fill rate no peor en más de 0,2 puntos | candidate: 0.992; official_baseline: 0.994 | ≥ 0.9923 | NO CUMPLE |
| N2 (FULL): inventario medio como máximo +5 % | candidate: 18,658.976; official_baseline: 18,062.866; relative: 1.033 | ≤ 1.05 × baseline | CUMPLE |
| N2 (NO_WARMUP): unidades faltantes no peores en más de un 2 % (informativo) | candidate: 2,931.000; official_baseline: 1,166.000; relative: 1.514 | ≤ 1,189.3 | NO CUMPLE |
| N2 (NO_WARMUP): fill rate no peor en más de 0,2 puntos (informativo) | candidate: 0.995; official_baseline: 0.998 | ≥ 0.9961 | NO CUMPLE |
| N2 (NO_WARMUP): inventario medio como máximo +5 % (informativo) | candidate: 18,895.010; official_baseline: 18,280.539; relative: 1.034 | ≤ 1.05 × baseline | CUMPLE |

Veredicto: no cumple: N1: ningún segmento de ≥ 10 productos empeora más de un 5 % en MASE; Sesgo por segmento de ≥ 10 productos no peor en más de 0,05; N2 (FULL): unidades faltantes no peores en más de un 2 %; N2 (FULL): fill rate no peor en más de 0,2 puntos.

### Holt-Winters

| Criterio | Valor | Umbral | Resultado |
|---|---|---|---|
| N1: mejora agregada de MASE en L + R | candidate: 0.643; comparable_cuts: 7; official_baseline: 0.787 | candidato < baseline oficial | CUMPLE |
| N1: mejora en ⌈2/3⌉ de los cortes comparables (mínimo 5) | comparable_cuts: 7; improved: 7; needed: 5 | ≥ 5 de 7 | CUMPLE |
| N1: ningún segmento de ≥ 10 productos empeora más de un 5 % en MASE | intermitente: 0.114; suave: -0.197 | cambio relativo ≤ 5% en segmentos que bloquean | NO CUMPLE |
| Sesgo relativo medio en L + R dentro de ±0,10 | candidate: -0.001; official_baseline: -0.001 | valor absoluto ≤ 0.1 | CUMPLE |
| Sesgo por segmento de ≥ 10 productos no peor en más de 0,05 | intermitente: 0.048; suave: 0.002 | aumento del valor absoluto del sesgo ≤ 0.05 | CUMPLE |
| N2 (FULL): unidades faltantes no peores en más de un 2 % | candidate: 4,218.000; official_baseline: 3,882.000; relative: 0.087 | ≤ 3,959.6 | NO CUMPLE |
| N2 (FULL): fill rate no peor en más de 0,2 puntos | candidate: 0.994; official_baseline: 0.994 | ≥ 0.9923 | CUMPLE |
| N2 (FULL): inventario medio como máximo +5 % | candidate: 18,276.062; official_baseline: 18,062.866; relative: 1.012 | ≤ 1.05 × baseline | CUMPLE |
| N2 (NO_WARMUP): unidades faltantes no peores en más de un 2 % (informativo) | candidate: 1,502.000; official_baseline: 1,166.000; relative: 0.288 | ≤ 1,189.3 | NO CUMPLE |
| N2 (NO_WARMUP): fill rate no peor en más de 0,2 puntos (informativo) | candidate: 0.998; official_baseline: 0.998 | ≥ 0.9961 | CUMPLE |
| N2 (NO_WARMUP): inventario medio como máximo +5 % (informativo) | candidate: 18,518.100; official_baseline: 18,280.539; relative: 1.013 | ≤ 1.05 × baseline | CUMPLE |

Veredicto: no cumple: N1: ningún segmento de ≥ 10 productos empeora más de un 5 % en MASE; N2 (FULL): unidades faltantes no peores en más de un 2 %.

### Croston

| Criterio | Valor | Umbral | Resultado |
|---|---|---|---|
| N1: mejora agregada de MASE en L + R | candidate: 0.688; comparable_cuts: 17; official_baseline: 0.800 | candidato < baseline oficial | CUMPLE |
| N1: mejora en ⌈2/3⌉ de los cortes comparables (mínimo 5) | comparable_cuts: 17; improved: 17; needed: 12 | ≥ 12 de 17 | CUMPLE |
| N1: ningún segmento de ≥ 10 productos empeora más de un 5 % en MASE | intermitente: -0.079; suave: -0.143 | cambio relativo ≤ 5% en segmentos que bloquean | CUMPLE |
| Sesgo relativo medio en L + R dentro de ±0,10 | candidate: -0.002; official_baseline: 0.002 | valor absoluto ≤ 0.1 | CUMPLE |
| Sesgo por segmento de ≥ 10 productos no peor en más de 0,05 | intermitente: 0.001; suave: -0.001 | aumento del valor absoluto del sesgo ≤ 0.05 | CUMPLE |
| N2 (FULL): unidades faltantes no peores en más de un 2 % | candidate: 4,271.000; official_baseline: 3,882.000; relative: 0.100 | ≤ 3,959.6 | NO CUMPLE |
| N2 (FULL): fill rate no peor en más de 0,2 puntos | candidate: 0.994; official_baseline: 0.994 | ≥ 0.9923 | CUMPLE |
| N2 (FULL): inventario medio como máximo +5 % | candidate: 17,776.044; official_baseline: 18,062.866; relative: 0.984 | ≤ 1.05 × baseline | CUMPLE |
| N2 (NO_WARMUP): unidades faltantes no peores en más de un 2 % (informativo) | candidate: 1,496.000; official_baseline: 1,166.000; relative: 0.283 | ≤ 1,189.3 | NO CUMPLE |
| N2 (NO_WARMUP): fill rate no peor en más de 0,2 puntos (informativo) | candidate: 0.998; official_baseline: 0.998 | ≥ 0.9961 | CUMPLE |
| N2 (NO_WARMUP): inventario medio como máximo +5 % (informativo) | candidate: 17,972.396; official_baseline: 18,280.539; relative: 0.983 | ≤ 1.05 × baseline | CUMPLE |

Veredicto: no cumple: N2 (FULL): unidades faltantes no peores en más de un 2 %.

### SBA

| Criterio | Valor | Umbral | Resultado |
|---|---|---|---|
| N1: mejora agregada de MASE en L + R | candidate: 0.903; comparable_cuts: 17; official_baseline: 0.800 | candidato < baseline oficial | NO CUMPLE |
| N1: mejora en ⌈2/3⌉ de los cortes comparables (mínimo 5) | comparable_cuts: 17; improved: 2; needed: 12 | ≥ 12 de 17 | NO CUMPLE |
| N1: ningún segmento de ≥ 10 productos empeora más de un 5 % en MASE | intermitente: -0.064; suave: 0.138 | cambio relativo ≤ 5% en segmentos que bloquean | NO CUMPLE |
| Sesgo relativo medio en L + R dentro de ±0,10 | candidate: -0.052; official_baseline: 0.002 | valor absoluto ≤ 0.1 | CUMPLE |
| Sesgo por segmento de ≥ 10 productos no peor en más de 0,05 | intermitente: 0.016; suave: 0.050 | aumento del valor absoluto del sesgo ≤ 0.05 | CUMPLE |
| N2 (FULL): unidades faltantes no peores en más de un 2 % | candidate: 4,928.000; official_baseline: 3,882.000; relative: 0.269 | ≤ 3,959.6 | NO CUMPLE |
| N2 (FULL): fill rate no peor en más de 0,2 puntos | candidate: 0.993; official_baseline: 0.994 | ≥ 0.9923 | CUMPLE |
| N2 (FULL): inventario medio como máximo +5 % | candidate: 15,319.603; official_baseline: 18,062.866; relative: 0.848 | ≤ 1.05 × baseline | CUMPLE |
| N2 (NO_WARMUP): unidades faltantes no peores en más de un 2 % (informativo) | candidate: 1,980.000; official_baseline: 1,166.000; relative: 0.698 | ≤ 1,189.3 | NO CUMPLE |
| N2 (NO_WARMUP): fill rate no peor en más de 0,2 puntos (informativo) | candidate: 0.997; official_baseline: 0.998 | ≥ 0.9961 | CUMPLE |
| N2 (NO_WARMUP): inventario medio como máximo +5 % (informativo) | candidate: 15,334.820; official_baseline: 18,280.539; relative: 0.839 | ≤ 1.05 × baseline | CUMPLE |

Veredicto: no cumple: N1: mejora agregada de MASE en L + R; N1: mejora en ⌈2/3⌉ de los cortes comparables (mínimo 5); N1: ningún segmento de ≥ 10 productos empeora más de un 5 % en MASE; N2 (FULL): unidades faltantes no peores en más de un 2 %.

### TSB

| Criterio | Valor | Umbral | Resultado |
|---|---|---|---|
| N1: mejora agregada de MASE en L + R | candidate: 0.687; comparable_cuts: 17; official_baseline: 0.800 | candidato < baseline oficial | CUMPLE |
| N1: mejora en ⌈2/3⌉ de los cortes comparables (mínimo 5) | comparable_cuts: 17; improved: 17; needed: 12 | ≥ 12 de 17 | CUMPLE |
| N1: ningún segmento de ≥ 10 productos empeora más de un 5 % en MASE | intermitente: -0.072; suave: -0.145 | cambio relativo ≤ 5% en segmentos que bloquean | CUMPLE |
| Sesgo relativo medio en L + R dentro de ±0,10 | candidate: -0.003; official_baseline: 0.002 | valor absoluto ≤ 0.1 | CUMPLE |
| Sesgo por segmento de ≥ 10 productos no peor en más de 0,05 | intermitente: -0.007; suave: 0.001 | aumento del valor absoluto del sesgo ≤ 0.05 | CUMPLE |
| N2 (FULL): unidades faltantes no peores en más de un 2 % | candidate: 4,170.000; official_baseline: 3,882.000; relative: 0.074 | ≤ 3,959.6 | NO CUMPLE |
| N2 (FULL): fill rate no peor en más de 0,2 puntos | candidate: 0.994; official_baseline: 0.994 | ≥ 0.9923 | CUMPLE |
| N2 (FULL): inventario medio como máximo +5 % | candidate: 17,771.337; official_baseline: 18,062.866; relative: 0.984 | ≤ 1.05 × baseline | CUMPLE |
| N2 (NO_WARMUP): unidades faltantes no peores en más de un 2 % (informativo) | candidate: 1,395.000; official_baseline: 1,166.000; relative: 0.196 | ≤ 1,189.3 | NO CUMPLE |
| N2 (NO_WARMUP): fill rate no peor en más de 0,2 puntos (informativo) | candidate: 0.998; official_baseline: 0.998 | ≥ 0.9961 | CUMPLE |
| N2 (NO_WARMUP): inventario medio como máximo +5 % (informativo) | candidate: 17,973.273; official_baseline: 18,280.539; relative: 0.983 | ≤ 1.05 × baseline | CUMPLE |

Veredicto: no cumple: N2 (FULL): unidades faltantes no peores en más de un 2 %.

## 8. Criterios por estrategia de `DT-011`

Los mismos criterios para cada modelo estudiado bajo cada estrategia, con la media móvil de 13 semanas **bajo la misma estrategia** como referencia. Nivel 1 del estudio de `DT-011` (consumo observado, sin las series de desabasto extremo); Nivel 2 de las ramas «(b)» y «(c)» de §5. C = cumple, **N** = no cumple, NC = no concluyente, NE = no evaluado. Sin recomendación.

> **Posible sesgo de selección:** Holt-Winters entró al estudio por su Nivel 1 medido en solo 7 cortes comparables (semanas 104 a 128), frente a 17 de los demás.

| Estrategia | Modelo | MASE `L + R` (modelo / media móvil) | Unidades faltantes (modelo / media móvil) | N1 agregado | N1 cortes | N1 segmentos | Sesgo | Sesgo por segmento | N2 faltantes | N2 *fill rate* | N2 inventario | Cumple todo |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| (a) | SES (provisional) | 0.669 / 0.800 | 3,860 / 3,882 | C | C | C | C | C | C | C | C | sí |
| (a) | Holt-Winters | 0.643 / 0.787 | 4,218 / 3,882 | C | C | **N** | C | C | **N** | C | C | no |
| (a) | TSB | 0.687 / 0.800 | 4,170 / 3,882 | C | C | C | C | C | **N** | C | C | no |
| (b) | SES (provisional) | 0.604 / 0.771 | 3,187 / 3,314 | C | C | C | C | C | C | C | C | sí |
| (b) | Holt-Winters | 0.587 / 0.758 | 3,493 / 3,314 | C | C | **N** | C | C | **N** | C | C | no |
| (b) | TSB | 0.642 / 0.771 | 3,168 / 3,314 | C | C | C | C | C | C | C | C | sí |
| (c) | SES (provisional) | 0.604 / 0.774 | 3,153 / 3,306 | C | C | C | C | C | C | C | C | sí |
| (c) | Holt-Winters | 0.555 / 0.754 | 3,511 / 3,306 | C | C | **N** | C | **N** | **N** | C | C | no |
| (c) | TSB | 0.645 / 0.774 | 3,173 / 3,306 | C | C | C | C | C | C | C | C | sí |

Cumplen todos los criterios que deciden, por estrategia: (a) SES (provisional); (b) SES (provisional), TSB; (c) SES (provisional), TSB.

## 9. Estudio de `DT-011` (desabasto)

Estrategias de entrenamiento: (a) consumo tal cual; (b) excluir días con desabasto; (c) imputar días con desabasto. La verdad nunca es un valor imputado. Conjunto común de las tres estrategias de cada modelo; series con más del 50 % de días con desabasto aparte: 5 series (85 serie-cortes). **La comparación contra la demanda latente solo es posible con datos `SYNTHETIC`.**

| Verdad | Modelo | Horizonte | Vista | Estrategia | Cortes | MASE | WAPE | Sesgo relativo |
|---|---|---|---|---|---|---|---|---|
| consumo observado | media móvil 13 | L + R | todas | (a) | 17 | 0.800 | 0.109 | 0.002 |
| consumo observado | media móvil 13 | L + R | todas | (b) | 17 | 0.771 | 0.116 | 0.065 |
| consumo observado | media móvil 13 | L + R | todas | (c) | 17 | 0.774 | 0.116 | 0.064 |
| consumo observado | media móvil 13 | L + R | sin desabasto | (a) | 17 | 0.728 | 0.091 | 0.007 |
| consumo observado | media móvil 13 | L + R | sin desabasto | (b) | 17 | 0.620 | 0.083 | 0.040 |
| consumo observado | media móvil 13 | L + R | sin desabasto | (c) | 17 | 0.621 | 0.082 | 0.040 |
| consumo observado | media móvil 13 | h = 1 | todas | (a) | 17 | 1.036 | 0.135 | -0.010 |
| consumo observado | media móvil 13 | h = 1 | todas | (b) | 17 | 0.930 | 0.122 | 0.051 |
| consumo observado | media móvil 13 | h = 1 | todas | (c) | 17 | 0.934 | 0.122 | 0.051 |
| consumo observado | media móvil 13 | h = 1 | sin desabasto | (a) | 17 | 0.822 | 0.107 | -0.043 |
| consumo observado | media móvil 13 | h = 1 | sin desabasto | (b) | 17 | 0.664 | 0.082 | 0.009 |
| consumo observado | media móvil 13 | h = 1 | sin desabasto | (c) | 17 | 0.668 | 0.083 | 0.009 |
| consumo observado | SES (provisional) | L + R | todas | (a) | 17 | 0.669 | 0.087 | -0.003 |
| consumo observado | SES (provisional) | L + R | todas | (b) | 17 | 0.604 | 0.086 | 0.063 |
| consumo observado | SES (provisional) | L + R | todas | (c) | 17 | 0.604 | 0.085 | 0.061 |
| consumo observado | SES (provisional) | L + R | sin desabasto | (a) | 17 | 0.600 | 0.069 | -0.009 |
| consumo observado | SES (provisional) | L + R | sin desabasto | (b) | 17 | 0.419 | 0.045 | 0.018 |
| consumo observado | SES (provisional) | L + R | sin desabasto | (c) | 17 | 0.422 | 0.045 | 0.018 |
| consumo observado | SES (provisional) | h = 1 | todas | (a) | 17 | 0.933 | 0.119 | -0.014 |
| consumo observado | SES (provisional) | h = 1 | todas | (b) | 17 | 0.793 | 0.095 | 0.050 |
| consumo observado | SES (provisional) | h = 1 | todas | (c) | 17 | 0.792 | 0.094 | 0.048 |
| consumo observado | SES (provisional) | h = 1 | sin desabasto | (a) | 17 | 0.705 | 0.090 | -0.052 |
| consumo observado | SES (provisional) | h = 1 | sin desabasto | (b) | 17 | 0.480 | 0.050 | 0.000 |
| consumo observado | SES (provisional) | h = 1 | sin desabasto | (c) | 17 | 0.482 | 0.051 | -0.000 |
| consumo observado | Holt-Winters | L + R | todas | (a) | 7 | 0.658 | 0.067 | 0.002 |
| consumo observado | Holt-Winters | L + R | todas | (b) | 7 | 0.587 | 0.072 | 0.051 |
| consumo observado | Holt-Winters | L + R | todas | (c) | 7 | 0.565 | 0.070 | 0.051 |
| consumo observado | Holt-Winters | L + R | sin desabasto | (a) | 7 | 0.582 | 0.046 | -0.012 |
| consumo observado | Holt-Winters | L + R | sin desabasto | (b) | 7 | 0.352 | 0.032 | 0.002 |
| consumo observado | Holt-Winters | L + R | sin desabasto | (c) | 7 | 0.332 | 0.030 | 0.005 |
| consumo observado | Holt-Winters | h = 1 | todas | (a) | 7 | 1.170 | 0.137 | 0.006 |
| consumo observado | Holt-Winters | h = 1 | todas | (b) | 7 | 0.862 | 0.109 | 0.053 |
| consumo observado | Holt-Winters | h = 1 | todas | (c) | 7 | 0.843 | 0.107 | 0.053 |
| consumo observado | Holt-Winters | h = 1 | sin desabasto | (a) | 7 | 0.967 | 0.093 | -0.045 |
| consumo observado | Holt-Winters | h = 1 | sin desabasto | (b) | 7 | 0.576 | 0.057 | -0.005 |
| consumo observado | Holt-Winters | h = 1 | sin desabasto | (c) | 7 | 0.559 | 0.055 | -0.005 |
| consumo observado | TSB | L + R | todas | (a) | 17 | 0.687 | 0.090 | -0.003 |
| consumo observado | TSB | L + R | todas | (b) | 17 | 0.642 | 0.094 | 0.063 |
| consumo observado | TSB | L + R | todas | (c) | 17 | 0.645 | 0.095 | 0.062 |
| consumo observado | TSB | L + R | sin desabasto | (a) | 17 | 0.619 | 0.073 | -0.007 |
| consumo observado | TSB | L + R | sin desabasto | (b) | 17 | 0.474 | 0.058 | 0.026 |
| consumo observado | TSB | L + R | sin desabasto | (c) | 17 | 0.475 | 0.058 | 0.026 |
| consumo observado | TSB | h = 1 | todas | (a) | 17 | 0.950 | 0.121 | -0.014 |
| consumo observado | TSB | h = 1 | todas | (b) | 17 | 0.824 | 0.102 | 0.050 |
| consumo observado | TSB | h = 1 | todas | (c) | 17 | 0.826 | 0.103 | 0.049 |
| consumo observado | TSB | h = 1 | sin desabasto | (a) | 17 | 0.728 | 0.093 | -0.051 |
| consumo observado | TSB | h = 1 | sin desabasto | (b) | 17 | 0.529 | 0.060 | 0.004 |
| consumo observado | TSB | h = 1 | sin desabasto | (c) | 17 | 0.533 | 0.061 | 0.003 |
| demanda latente | media móvil 13 | L + R | todas | (a) | 17 | 0.809 | 0.117 | -0.059 |
| demanda latente | media móvil 13 | L + R | todas | (b) | 17 | 0.622 | 0.084 | -0.001 |
| demanda latente | media móvil 13 | L + R | todas | (c) | 17 | 0.626 | 0.085 | -0.001 |
| demanda latente | media móvil 13 | L + R | sin desabasto | (a) | 17 | 0.728 | 0.091 | 0.007 |
| demanda latente | media móvil 13 | L + R | sin desabasto | (b) | 17 | 0.620 | 0.083 | 0.040 |
| demanda latente | media móvil 13 | L + R | sin desabasto | (c) | 17 | 0.621 | 0.082 | 0.040 |
| demanda latente | media móvil 13 | h = 1 | todas | (a) | 17 | 0.842 | 0.117 | -0.059 |
| demanda latente | media móvil 13 | h = 1 | todas | (b) | 17 | 0.663 | 0.085 | -0.001 |
| demanda latente | media móvil 13 | h = 1 | todas | (c) | 17 | 0.669 | 0.087 | -0.001 |
| demanda latente | media móvil 13 | h = 1 | sin desabasto | (a) | 17 | 0.822 | 0.107 | -0.043 |
| demanda latente | media móvil 13 | h = 1 | sin desabasto | (b) | 17 | 0.664 | 0.082 | 0.009 |
| demanda latente | media móvil 13 | h = 1 | sin desabasto | (c) | 17 | 0.668 | 0.083 | 0.009 |
| demanda latente | SES (provisional) | L + R | todas | (a) | 17 | 0.680 | 0.099 | -0.064 |
| demanda latente | SES (provisional) | L + R | todas | (b) | 17 | 0.405 | 0.047 | -0.002 |
| demanda latente | SES (provisional) | L + R | todas | (c) | 17 | 0.413 | 0.048 | -0.004 |
| demanda latente | SES (provisional) | L + R | sin desabasto | (a) | 17 | 0.600 | 0.069 | -0.009 |
| demanda latente | SES (provisional) | L + R | sin desabasto | (b) | 17 | 0.419 | 0.045 | 0.018 |
| demanda latente | SES (provisional) | L + R | sin desabasto | (c) | 17 | 0.422 | 0.045 | 0.018 |
| demanda latente | SES (provisional) | h = 1 | todas | (a) | 17 | 0.720 | 0.099 | -0.063 |
| demanda latente | SES (provisional) | h = 1 | todas | (b) | 17 | 0.470 | 0.051 | -0.002 |
| demanda latente | SES (provisional) | h = 1 | todas | (c) | 17 | 0.475 | 0.052 | -0.004 |
| demanda latente | SES (provisional) | h = 1 | sin desabasto | (a) | 17 | 0.705 | 0.090 | -0.052 |
| demanda latente | SES (provisional) | h = 1 | sin desabasto | (b) | 17 | 0.480 | 0.050 | 0.000 |
| demanda latente | SES (provisional) | h = 1 | sin desabasto | (c) | 17 | 0.482 | 0.051 | -0.000 |
| demanda latente | Holt-Winters | L + R | todas | (a) | 7 | 0.640 | 0.069 | -0.051 |
| demanda latente | Holt-Winters | L + R | todas | (b) | 7 | 0.332 | 0.031 | -0.004 |
| demanda latente | Holt-Winters | L + R | todas | (c) | 7 | 0.313 | 0.029 | -0.004 |
| demanda latente | Holt-Winters | L + R | sin desabasto | (a) | 7 | 0.582 | 0.046 | -0.012 |
| demanda latente | Holt-Winters | L + R | sin desabasto | (b) | 7 | 0.352 | 0.032 | 0.002 |
| demanda latente | Holt-Winters | L + R | sin desabasto | (c) | 7 | 0.332 | 0.030 | 0.005 |
| demanda latente | Holt-Winters | h = 1 | todas | (a) | 7 | 0.973 | 0.099 | -0.051 |
| demanda latente | Holt-Winters | h = 1 | todas | (b) | 7 | 0.570 | 0.057 | -0.006 |
| demanda latente | Holt-Winters | h = 1 | todas | (c) | 7 | 0.553 | 0.056 | -0.006 |
| demanda latente | Holt-Winters | h = 1 | sin desabasto | (a) | 7 | 0.967 | 0.093 | -0.045 |
| demanda latente | Holt-Winters | h = 1 | sin desabasto | (b) | 7 | 0.576 | 0.057 | -0.005 |
| demanda latente | Holt-Winters | h = 1 | sin desabasto | (c) | 7 | 0.559 | 0.055 | -0.005 |
| demanda latente | TSB | L + R | todas | (a) | 17 | 0.702 | 0.102 | -0.064 |
| demanda latente | TSB | L + R | todas | (b) | 17 | 0.468 | 0.059 | -0.002 |
| demanda latente | TSB | L + R | todas | (c) | 17 | 0.474 | 0.061 | -0.003 |
| demanda latente | TSB | L + R | sin desabasto | (a) | 17 | 0.619 | 0.073 | -0.007 |
| demanda latente | TSB | L + R | sin desabasto | (b) | 17 | 0.474 | 0.058 | 0.026 |
| demanda latente | TSB | L + R | sin desabasto | (c) | 17 | 0.475 | 0.058 | 0.026 |
| demanda latente | TSB | h = 1 | todas | (a) | 17 | 0.742 | 0.102 | -0.063 |
| demanda latente | TSB | h = 1 | todas | (b) | 17 | 0.522 | 0.061 | -0.002 |
| demanda latente | TSB | h = 1 | todas | (c) | 17 | 0.529 | 0.063 | -0.002 |
| demanda latente | TSB | h = 1 | sin desabasto | (a) | 17 | 0.728 | 0.093 | -0.051 |
| demanda latente | TSB | h = 1 | sin desabasto | (b) | 17 | 0.529 | 0.060 | 0.004 |
| demanda latente | TSB | h = 1 | sin desabasto | (c) | 17 | 0.533 | 0.061 | 0.003 |

Sustituciones en el estudio: Holt-Winters: 71, Holt-Winters (b): 26, Holt-Winters (c): 48.

Nivel 2 de las estrategias: filas «(b)» y «(c)» de §5 (población completa).

**Conclusión provisional del estudio** (revisión del responsable, 2026-10-06; solo con datos `SYNTHETIC`): las estrategias (b) y (c) reducen las unidades faltantes entre un 15 % y un 24 % en los modelos estudiados, con un inventario medio entre un 1,7 % y un 2,1 % mayor que el de la media móvil 13 con (a). Adoptar una en producción exige una unidad propia que cambie U3 y una DT nueva.

**PROPUESTA del desarrollador** (pendiente de decisión del responsable): preferir (b). La diferencia con (c) está dentro del ruido, (b) no necesita un estimador con parámetros propios y la API ya expone `days_observed` y `stockout_days` por periodo.

## 10. Sensibilidades

### Cadencia de reoptimización

Los candidatos reoptimizan cada 4 decisiones (`DT-093` punto 9). Aquí, Holt, Croston y TSB reoptimizan en cada decisión semanal, con la media móvil 13 en la misma simulación. Se calcula en el mismo comando de §1 (etapa «cadence»); huella del detalle: `28ce7c4f122519303398f7c5d36c4e3dd0a07c7ac7e4b2230106f40522fda9a6`. Media móvil idéntica a la de §5: sí.

| Rama | Unidades faltantes | Relativo a media móvil | *Fill rate* | Inventario relativo | N2 faltantes | N2 *fill rate* | N2 inventario |
|---|---|---|---|---|---|---|---|
| media móvil 13 | 3,882 | +0.0% | 0.9943 | 1.000 | — | — | — |
| Croston | 4,025 | +3.7% | 0.9941 | 0.985 | NO CUMPLE | CUMPLE | CUMPLE |
| Holt | 5,658 | +45.7% | 0.9918 | 1.033 | NO CUMPLE | NO CUMPLE | CUMPLE |
| TSB | 3,973 | +2.3% | 0.9942 | 0.985 | NO CUMPLE | CUMPLE | CUMPLE |

Con reoptimización semanal cumplen los criterios de Nivel 2: ninguno.

### Tamaño mínimo de segmento

El segmento intermitente tiene en promedio 10 series por corte, justo en el umbral de `DT-091`. Cambios respecto al umbral de 10, sobre las tablas de §7 y §8:

| Umbral | Resultados que cambian | Veredictos que cambian |
|---|---|---|
| 11 | 7 de 165 | ninguno |
| 9 | 0 de 165 | ninguno |

Con 11: Holt-Winters (§8, (a)), «N1: ningún segmento de ≥ 10 productos empeora más de un 5 % en MASE»: NO CUMPLE → CUMPLE; Holt (§7), «N1: ningún segmento de ≥ 10 productos empeora más de un 5 % en MASE»: NO CUMPLE → CUMPLE; Holt (§7), «Sesgo por segmento de ≥ 10 productos no peor en más de 0,05»: NO CUMPLE → CUMPLE; Holt-Winters (§7), «N1: ningún segmento de ≥ 10 productos empeora más de un 5 % en MASE»: NO CUMPLE → CUMPLE; Holt-Winters (§8, (b)), «N1: ningún segmento de ≥ 10 productos empeora más de un 5 % en MASE»: NO CUMPLE → CUMPLE; Holt-Winters (§8, (c)), «N1: ningún segmento de ≥ 10 productos empeora más de un 5 % en MASE»: NO CUMPLE → CUMPLE; Holt-Winters (§8, (c)), «Sesgo por segmento de ≥ 10 productos no peor en más de 0,05»: NO CUMPLE → CUMPLE.

## 11. US-055: cobertura de los intervalos

Cobertura semanal (nominal 0,80) contra el consumo observado. Calibrado si la cobertura en los cortes tardíos está entre 0,75 y 0,85 en el horizonte (`DT-093` punto 6). Solo decide el rótulo de la banda.

| Modelo | Horizontes en banda: actual | Horizontes en banda: calibrado | Cobertura actual, todos los cortes (h = 1 / h = 14) | Actual, tardíos (h = 1 / h = 14) | Calibrado, tardíos (h = 1 / h = 14) |
|---|---|---|---|---|---|
| naïve | 12 de 14 | 14 de 14 | 0.842 / 0.832 | 0.841 / 0.847 | 0.780 / 0.828 |
| naïve estacional | 9 de 14 | 11 de 14 | 0.836 / 0.826 | 0.849 / 0.853 | 0.849 / 0.853 |
| media móvil 13 | 14 de 14 | 14 de 14 | 0.831 / 0.805 | 0.836 / 0.816 | 0.836 / 0.816 |
| SES (provisional) | 14 de 14 | 14 de 14 | 0.814 / 0.774 | 0.833 / 0.794 | 0.834 / 0.830 |
| Holt | 14 de 14 | 13 de 14 | 0.814 / 0.787 | 0.815 / 0.775 | 0.815 / 0.770 |
| Holt-Winters | 0 de 14 | 8 de 14 | 0.669 / 0.641 | 0.669 / 0.641 | 0.839 / 0.856 |
| Croston | 14 de 14 | 14 de 14 | 0.815 / 0.774 | 0.831 / 0.794 | 0.831 / 0.827 |
| SBA | 14 de 14 | 14 de 14 | 0.810 / 0.765 | 0.826 / 0.794 | 0.832 / 0.835 |
| TSB | 14 de 14 | 14 de 14 | 0.815 / 0.775 | 0.832 / 0.794 | 0.832 / 0.824 |

**Rótulo recomendado para la banda de la Fase 7** (media móvil 13, la que sirve U3; texto del responsable): **«Intervalo nominal 0,80. Cobertura observada entre 0,75 y 0,85 en pruebas con datos sintéticos; no validada con datos reales.»** El intervalo actual de U3 queda en banda en 14 de 14 horizontes con todas las semanas y en 13 de 14 sin las semanas con desabasto; la variante calibrada, en 14 de 14. No hace falta calibrarlo con estos datos. Es un ajuste posterior de F7d que se autoriza aparte: la Fase 7 no se modifica.

## 12. Paridad con F5a y F5b

Huellas de los archivos de detalle de F5a y F5b recalculados desde F5c (sus cuatro modelos):

| Archivo | F5c | Registrado | Igual |
|---|---|---|---|
| `f5a-observations.csv` | `f52abd6a91c9d73b…` | `f52abd6a91c9d73b…` | True |
| `f5a-series-cuts.csv` | `b7d18a0fee5d45bc…` | `b7d18a0fee5d45bc…` | True |
| `f5b-decisions.csv` | `a9fd7608fc7a0ba2…` | `a9fd7608fc7a0ba2…` | True |
| `f5b-orders.csv` | `823c72d74d034a0a…` | `823c72d74d034a0a…` | True |
| `f5b-windows.csv` | `895488760c0745b9…` | `895488760c0745b9…` | True |

## 13. Salidas

Junto a este informe se versiona un JSON resumido (mismo nombre, `.json`). El detalle se regenera de forma determinista con el comando de §1 en `ml/out/`, ignorado por Git. Huellas:

- `f5c-decisions.csv`: `f023e0e135ab16319e2ee2b8afa2bcdbde8be7386b1289f73219239778d0a606`
- `f5c-observations.csv`: `0aa19b6f4cbde8e292542458d58d6bf746e7f59caaf2cdb2b88f41332ccb06b1`
- `f5c-orders.csv`: `4147143598636330fed06a756945264ce54b43ce8e04aac045c97c4a0233893e`
- `f5c-study.csv`: `507fab15f550634c77b61669df33dd1ef0a5471ea265b5e7305dadcc1e79488c`
- `f5c-windows.csv`: `70105e2511edcec90fda7c39e74e6f6ad1460a1873d0145665a96034807989d0`
