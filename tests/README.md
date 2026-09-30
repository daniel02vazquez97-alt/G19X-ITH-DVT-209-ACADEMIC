# Pruebas

Estrategia completa en [`../docs/13-testing.md`](../docs/13-testing.md).

## Estado

Vacía en la Etapa 0: no existe código de aplicación que probar. Es lo correcto en esta etapa.

## Organización prevista

Las pruebas unitarias vivirán junto a su código (`backend/tests/`, `frontend/src/**/*.test.tsx`,
`ml/tests/`). Esta carpeta se reserva para lo **transversal**, que no pertenece a un solo módulo:

```
tests/
├── e2e/            # Flujos completos a través de toda la pila
├── performance/    # Escenarios de carga y sus criterios
├── security/       # Autorización, inyección, inyección de prompt, fuga
└── fixtures/       # Datos y escenarios compartidos
```

## Prioridad

Se prueba con más intensidad donde un error cuesta más:

```
supply_engine  >  API + datos  >  pipeline de ML  >  ingesta  >  frontend
```

El motor de abastecimiento es puro y determinístico, lo que permite probarlo de forma exhaustiva con
casos calculados a mano. Es la parte más fácil de probar y la que más lo merece.

## Reglas innegociables

1. **No se reporta trabajo terminado con pruebas en rojo.**
2. Sin red en pruebas unitarias: los servicios de Azure se sustituyen por dobles.
3. Sin dependencia del reloj real ni de aleatoriedad no sembrada.
4. Toda corrección de defecto añade la prueba que lo habría detectado.
5. Cobertura como señal, no como objetivo.
