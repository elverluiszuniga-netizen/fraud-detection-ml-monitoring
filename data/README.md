# Datos
El CSV raw no se versiona debido a su tamaño. Se conserva una única copia original en la raíz: `PS_20174392719_1491204439457_log.csv`; el script también acepta una ruta mediante `--input`. No modificar el original. `raw/` y `processed/` están reservados para fases posteriores.

Referencia/desarrollo: `step <= 400`. Producción simulada: `step >= 401`. Nunca mezclar estos periodos mediante un split aleatorio global.
