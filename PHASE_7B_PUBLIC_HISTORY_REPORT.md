# Fase 7B — Preparación de historial público seguro

Fecha: 15 de octubre de 2026, America/Lima.

**Resultado: copia independiente preparada para autorización de publicación Git.** El repositorio original conserva sus cinco commits y sus ramas. No se ha creado ningún repositorio remoto, hecho push, abierto PR, mergeado ni creado release. DagsHub sigue pendiente como entrega externa.

## 1. Alcance y ubicaciones

Se revisaron `PHASE_7B_PREPUBLICATION_REPORT.md`, `PHASE_7B_PUBLICATION_PLAN.md`, todos los commits de `main` y `development`, sus árboles y todos los objetos locales, incluidos los inalcanzables si existieran. El árbol fuente estaba limpio al comenzar.

La carpeta local separada `phase7b-public-history` contiene:

- `public-repository/`: único directorio preparado para publicar; Git independiente, sin remotos, alternates, objetos prestados ni historial original.
- `private-backup/`: bundle del historial original, restauración de comprobación y los 15 originales privados. **Nunca publicar esta carpeta.** Está fuera de `public-repository/` y del repositorio original.
- `preparation-receipt.json` y `final-receipt.json`: recibos locales de trazabilidad; el segundo identifica las puntas exactas aprobables después del commit de este informe.
- Logs de tests, notebooks y dashboard, fuera del directorio publicable. Pueden mencionar la ubicación del entorno Python y se conservan solo localmente.

Este mismo informe se entrega en el repositorio original como archivo nuevo y en `development` de la copia pública. Las referencias y archivos previamente versionados del original no se modificaron.

## 2. Hallazgos del historial original

Origen: `main = 4ea3a5fba48b2ba27b7ab4162f82cfbfd9c8baeb`; `development = 806f24b4ebe414e4dc39590057d46ca351feba08`. Se examinaron **5 commits, 203 objetos y 164 blobs**, sin objetos inalcanzables. El mayor blob tiene 4,090,362 bytes.

| Commit original | Archivos con rutas privadas en su árbol |
|---|---:|
| `4ea3a5fba48b2ba27b7ab4162f82cfbfd9c8baeb` | 2 |
| `22b49c526a588fbd9037439243d1c75fa08ff588` | 14 |
| `18acda61bc935bb06c48115cebb72293eb443e6d` | 15 |
| `c22bd9f65bc10bf6d031ac956cb454ac36b8a385` | 0 |
| `806f24b4ebe414e4dc39590057d46ca351feba08` | 0 |

Los tres primeros commits hacen alcanzables 15 blobs distintos afectados; los dos últimos ya tienen árboles saneados, pero conservan los anteriores como ancestros. Inventario exacto:

| Archivo | OID del blob privado |
|---|---|
| `reports/audit_results.json` | `0a207376c812f180090de73be808cc3c5914001a` |
| `artifacts/production_monitoring_freeze.json` | `1627b29f8e4e6afe1c3d1c75233e4cee6a917dab` |
| `artifacts/monitoring_summary.json` | `2ff5416e38137a1f086f86c509ef6f99c361088d` |
| `notebooks/05_monitoring.ipynb` | `35dc2fcdf95a9f59992a206a5dd7696f1f9a048d` |
| `artifacts/phase3_run.json` | `36f71cb6f87d6f5d9ca33dd6e16c5b8304bec5c8` |
| `INITIAL_DATA_AUDIT.md` | `4ad1c8a67d4182765754471d8a09f096d715d094` |
| `PHASE_5_MONITORING_REPORT.md` | `58f0c706fe9b085c5d3a98bb9e34e4e08eeb6940` |
| `notebooks/03_hyperparameter_optimization.ipynb` | `6780603ca53ca537fc6a7c988bcf4bd328889dd3` |
| `PHASE_3_OPTIMIZATION_MLFLOW_REPORT.md` | `743d341b33d01d268fd7ebc77899878198f91d9e` |
| `artifacts/interpretability_summary.json` | `743f75fbba74a7b616b2f995ac642335f5eba54b` |
| `notebooks/04_interpretability.ipynb` | `76240f3561a4adc4a33baf6b99cd88b5bb972a19` |
| `docs/model_interpretability.md` | `8e3c4e3b27b9b3191dcef23097a22aa56bbb347b` |
| `PHASE_7_DELIVERY_AUDIT.md` | `c6aecb11a3a13f74bcc5d90aee9042990234dbac` |
| `PHASE_4_INTERPRETABILITY_REPORT.md` | `d945d15f81d5d186b62357bed8b8fd78efc2efd0` |
| `artifacts/phase2_run.json` | `e671a74dbd054d1abf7e060d15b081e4320752be` |

`docs/original_history_audit.json` contiene la relación completa commit/archivo/OID, sin reproducir las rutas privadas. Los OID son identificadores, no objetos importados al repositorio público.

## 3. Clasificación de seguridad

Las incidencias confirmadas son directorios del checkout local, procedencia de artifacts y SQLite, y logs del entorno Python. Revelan estructura local; no se identificaron credenciales en ellas.

Se buscaron tokens GitHub clásicos y fine-grained, claves AWS, claves privadas PEM/OpenSSH, claves Google API, tokens Slack, secretos literales y URLs con credenciales en blobs y mensajes de commits/tags. **Cero candidatos de secretos reales.** La URL de `tests/test_optimization.py:125` con usuario/contraseña es una fixture explícita del dominio reservado `example.invalid`; prueba que el código rechaza URLs autenticadas. No es una credencial operativa y se conservó.

Los patrones se aplicaron al texto y metadata PNG para rutas; se evitó interpretar bytes comprimidos de píxeles como rutas. Los patrones de secretos también examinaron los bytes de objetos. La comprobación adicional del prefijo exacto del checkout original cubre también contenido binario y variantes escapadas. No se alteraron imágenes. La revisión es heurística y no una garantía universal sobre todos los formatos de secretos. No apareció ningún hallazgo que requiera revocación; ante un futuro secreto confirmado, detener la publicación y revocarlo antes de continuar.

## 4. Alternativas y decisión

| Alternativa | Ventaja | Riesgo/coste en este proyecto |
|---|---|---|
| Reescribir una copia con una herramienta especializada, por ejemplo `git-filter-repo` | Conserva una secuencia equivalente de commits y permite mapear cada commit antiguo al reescrito | Exige revisar reglas, todos los refs y metadata; cambia hashes de commits y archivos afectados; puede romper las comprobaciones de evidencia congelada si se transforman artifacts sin manifiesto; requiere instalar y validar la herramienta |
| Inicializar un Git independiente y reconstruir baseline saneada más snapshot final | Control explícito de archivos y objetos; original intacto; sin instalación, force push ni residuos del historial privado | La cronología pública nueva no reproduce cada commit intermedio; la trazabilidad debe documentarse mediante OID, inventario y respaldo |

**Se eligió la segunda opción**, dado que no hay publicación remota configurada y el árbol final ya estaba validado. No se ejecutó ninguna reescritura sobre el original ni se instaló una herramienta. Tampoco se hizo un clon del original para convertirlo en público: se inicializó un object store nuevo y se exportaron exclusivamente archivos de los árboles elegidos.

## 5. Respaldo privado y recuperación comprobada

Se creó `private-backup/original-history.bundle` con `git bundle create ... --all`. SHA256:

`f0f02afbcd2f5d0e4e087de14ec98d8647f302915c18daabbedab59bf297e962`.

`git bundle verify` fue satisfactorio. Se restauró localmente en `private-backup/restore-check.git` mediante clon bare del bundle, sin red ni hardlinks. `show-ref` coincide exactamente con el original y `git fsck --full` fue satisfactorio. El bundle conserva los cinco commits, ambas ramas y todos sus objetos alcanzables; no había objetos inalcanzables que respaldar.

Se copiaron también los 15 originales de `private_publication_originals/` y se comprobaron sus SHA256 contra `publication_sanitization_manifest.json`. El respaldo no intenta duplicar raw, entorno, DB MLflow ni otros archivos ignorados: permanecen intactos en el original y no forman parte del historial Git.

Procedimiento de recuperación, solo si hiciera falta: desde `private-backup/`, elegir un destino nuevo vacío y ejecutar `git clone --bare --no-hardlinks original-history.bundle recovered-original.git`; luego `git -C recovered-original.git fsck --full`. No recuperar sobre el repositorio público ni el original existente.

## 6. Ramas públicas y trazabilidad

La copia usa esta genealogía:

```text
db6bbdf  main: baseline inicial saneada
   |
57ada5a  development: snapshot académico final y procedencia
   |
         development: informe final y mapa de commits actualizado
```

| Referencia | Commit |
|---|---|
| `main` original | `4ea3a5fba48b2ba27b7ab4162f82cfbfd9c8baeb` |
| `development` original | `806f24b4ebe414e4dc39590057d46ca351feba08` |
| `main` pública nueva | `db6bbdf77fb026a2acf83ac662b50e0a7fe3abb5` |
| Snapshot público validado | `57ada5ab1e8ccd0ed92a65195c4c3ac73fa7a85b` |
| Punta final pública con este informe | `public_development` en `../final-receipt.json`, comprobable con `git rev-parse development` |

El informe no inserta el hash del commit que lo contiene, pues eso sería autorreferencial. El recibo local se escribe después del commit final y fija ese hash exacto para aprobación.

La baseline reconstruye los 22 archivos de `main` original, saneando únicamente las rutas de la auditoría Markdown y JSON; añade `.gitattributes` del árbol final para conservar bytes desde el primer commit. Los resultados de la auditoría inicial se mantienen. `development` incorpora los 150 archivos del árbol final fuente.

`docs/public_history_provenance.json` registra los árboles originales, SHA256 y OID por archivo, cambios de baseline y correspondencia de los cinco commits originales con baseline/snapshot. Los commits intermedios se representan por su contenido acumulado en el snapshot final; **no se afirma equivalencia de sus árboles ni conservación de autorías/fechas originales en la nueva cronología**. Los hashes de modelos, métricas, notebooks y reportes finales no cambian.

`main` es ancestro de `development`: comprobado con `git merge-base --is-ancestor main development`, sin hacer merge. Hay cambios académicos reales entre ambas ramas, incluidos código, modelo, notebooks, dashboard e informes. Un futuro PR `development → main` comparte ancestro y es integrable; no necesita `--allow-unrelated-histories`. Su estado real en GitHub solo podrá comprobarse después de publicar las ramas y abrirlo con autorización.

La autoría de los commits nuevos utiliza `elverluiszuniga-netizen` y su dirección noreply en opciones de comando; no se cambió configuración global ni se reutilizó la cuenta anterior. No se solicitó autenticación ni se realizó ninguna consulta remota durante esta fase.

## 7. Integridad de entregables y diferencias

Se mantuvieron los **150 archivos fuente**, sin bajas. De ellos, **148 son idénticos byte a byte** al commit `806f24b`. Las únicas diferencias son:

1. `PHASE_7B_PUBLICATION_PLAN.md`: aviso inicial que invalida sus instrucciones históricas para la cuenta anterior y remite a este procedimiento.
2. `scripts/validate_publication.py`: comprueba siempre los hashes de copias publicables; comprueba originales privados solo cuando están presentes. La copia pública no debe contener esos originales. La ausencia se informa explícitamente; no se finge haberlos verificado allí.

Se añadieron `scripts/audit_public_history.py`, `docs/original_history_audit.json`, `docs/public_history_provenance.json` y este informe. No se alteraron productores de resultados, reglas del modelo, dependencias o lock. La comparación final identifica individualmente todos los archivos añadidos y modificados en `final-receipt.json`.

Se comprobó la presencia y la igualdad byte a byte de los cinco notebooks, módulos de código académico, app Streamlit, modelo champion y manifiesto, CSV/JSON de artifacts, figuras y cinco HTML. Se conservan README, documentación de datos/reproducción/recuperación y todos los informes académicos de fases.

Champion: SHA256 `44a20bc0e2abbd276ae94790db404248d2ab2c5d01025b00b2e4f935b6f220e4`, **14 features, 24 rondas efectivas, threshold 0.5**. Modelo de 77,796 bytes idéntico al validado. Los archivos completos de métricas son idénticos: no se recalcularon ni editaron sus valores. Se verificaron la carga y consistencia del bundle mediante la suite y el verificador de entrega. No se entrenó, optimizó ni ejecutó inferencia sobre Production.

## 8. Validación ejecutada desde la copia

Se reutilizó el entorno de bibliotecas existente, ejecutando los módulos del checkout público y sin configurar un path absoluto en el código publicable. `PYTHONPATH` se limpió y `FRAUD_DATA_PATH` se eliminó del entorno de comprobación. Temporales dentro de `tmp/`, ignorado.

| Comprobación | Resultado |
|---|---|
| `python -m pytest -q -p no:cacheprovider` | **59 passed, 4 warnings**, 11.56 segundos |
| `python scripts/verify_delivery.py --notebooks` | Modelo, artifacts y evidencia congelada OK; cinco notebooks OK |
| Celdas por notebook 01–05 | 5, 6, 6, 5 y 6 |
| `python scripts/validate_publication.py` | Cinco vistas Streamlit sin excepciones/errores; cinco HTML completos; hashes publicables OK |
| Segunda copia en otra ruta | Artifacts, modelo y cinco notebooks OK, sin raw, processed ni stores MLflow |
| `python scripts/audit_public_history.py` | Cero rutas privadas, secretos candidatos o archivos prohibidos en el historial público |
| `git fsck --full` | Satisfactorio |

Los cuatro warnings son deprecaciones de SHAP y SQLAlchemy/MLflow. AppTest dentro del sandbox no completó y se interrumpió; la ejecución final fuera del sandbox terminó correctamente. Los notebooks se validaron ejecutando sus celdas Python de presentación, sin reescribir outputs; no se afirma ejecución en un kernel Jupyter independiente. AppTest y las comprobaciones de estructura HTML no sustituyen una revisión visual nueva en navegador.

`git diff --check main..development` detecta espacios/líneas finales heredados en HTML Evidently y algunos módulos. Se conservaron deliberadamente los bytes de los archivos validados; no son cambios nuevos de métricas ni fallos de tests. No se presenta esa comprobación como satisfactoria. Los cambios documentales nuevos se revisaron por separado.

## 9. Seguridad del conjunto publicable

Se inspeccionaron todos los objetos locales de la copia pública, no solo el árbol de `development`. Resultado: ningún blob privado original, ningún commit original, ninguna ruta privada detectada, ningún objeto inalcanzable ni archivo prohibido. Los hashes antiguos escritos como trazabilidad no hacen alcanzables sus objetos.

También se comprobaron bytes de todos los objetos de contenido frente al prefijo exacto del checkout privado y sus variantes escapadas. No hay alternates, shallow clone, tags, refs de respaldo ni remotos. Las únicas ramas son `main` y `development`.

No se incorporaron CSV raw, `.env`, claves, bundles privados, DB SQLite/MLflow/Optuna, matrices procesadas ni entorno virtual. Los placeholders `.gitkeep` se conservan. Se revisó `.gitignore`, que protege raw, stores, secretos, temporales y originales privados. Mayor blob: HTML Evidently, 4,090,362 bytes; ninguno supera 10 MiB. No se borraron datos locales del original.

El scanner conserva explícitamente la fixture sintética de URL autenticada y documenta sus exclusiones. Si en una revisión posterior aparece un candidato distinto, detenerse y evaluarlo antes de publicar.

## 10. Procedimiento exacto para publicar, solo tras autorización

**No ejecutado.** Este procedimiento sustituye las instrucciones de publicación de los planes históricos. Solo corresponde al directorio `public-repository/` preparado y a la cuenta `elverluiszuniga-netizen`. No publicar desde el original ni desde `private-backup/`.

### A. Revalidación local e identidad

Abrir PowerShell en `public-repository/`, activar un entorno Python con las dependencias del lock y mantener `../final-receipt.json` junto a la copia. Ejecutar después de la autorización:

```powershell
$ErrorActionPreference = 'Stop'
function Assert-NativeSuccess {
    if ($LASTEXITCODE -ne 0) { throw 'El comando anterior falló; detenerse.' }
}
$receipt = Get-Content ../final-receipt.json -Raw | ConvertFrom-Json
$currentMain = (git rev-parse main).Trim(); Assert-NativeSuccess
$currentDev = (git rev-parse development).Trim(); Assert-NativeSuccess
if ($currentMain -cne $receipt.public_main -or $currentDev -cne $receipt.public_development) {
    throw 'Las ramas cambiaron respecto a la copia revisada.'
}
$dirty = @(git status --porcelain); Assert-NativeSuccess
if ($dirty.Count -ne 0) { throw 'Hay cambios locales pendientes.' }
$remotes = @(git remote); Assert-NativeSuccess
if ($remotes.Count -ne 0) { throw 'Ya existe un remoto; revisarlo antes de continuar.' }
git merge-base --is-ancestor main development; Assert-NativeSuccess
git fsck --full; Assert-NativeSuccess
python scripts/audit_public_history.py --output ../prepush-security-audit.json
Assert-NativeSuccess
python scripts/verify_delivery.py --notebooks; Assert-NativeSuccess
python -m pytest -q -p no:cacheprovider; Assert-NativeSuccess

$gh = (Get-Command gh -ErrorAction SilentlyContinue).Source
if (-not $gh) { $gh = Join-Path $env:ProgramFiles 'GitHub CLI/gh.exe' }
if (-not (Test-Path -LiteralPath $gh)) { throw 'GitHub CLI no localizado.' }
& $gh auth status; Assert-NativeSuccess
$login = (& $gh api user --jq .login).Trim(); Assert-NativeSuccess
if ($login -cne 'elverluiszuniga-netizen') { throw 'Cuenta incorrecta; detenerse.' }
```

Si falla cualquier comprobación, no publicar. Si cambian las ramas después de este informe, actualizar la validación y el recibo mediante una nueva revisión. No adaptar el recibo para saltarse una discrepancia.

### B. Crear un repositorio vacío y publicar exclusivamente ambas ramas

Este bloque requiere autorización explícita para **crear un repositorio público y hacer push de esas dos ramas**. Si el nombre ya existe, el comando de creación debe fallar: detenerse y revisar contenido/permisos; no sobrescribir, forzar ni asumir que un error de red significa ausencia. No inicializar README, licencia o `.gitignore` remotos.

```powershell
$repo = 'elverluiszuniga-netizen/fraud-detection-ml-monitoring'
& $gh repo create $repo --public --description 'Academic fraud detection, interpretability and offline monitoring'
Assert-NativeSuccess
git remote add origin "https://github.com/$repo.git"; Assert-NativeSuccess
git push --atomic --set-upstream origin refs/heads/main:refs/heads/main refs/heads/development:refs/heads/development
Assert-NativeSuccess
& $gh repo edit $repo --default-branch main; Assert-NativeSuccess

$remoteLines = @(git ls-remote --heads origin main development); Assert-NativeSuccess
$remoteRefs = @{}
foreach ($line in $remoteLines) {
    $fields = $line -split '\s+'
    $remoteRefs[$fields[1]] = $fields[0]
}
if ($remoteRefs['refs/heads/main'] -cne $receipt.public_main -or
    $remoteRefs['refs/heads/development'] -cne $receipt.public_development) {
    throw 'Las puntas remotas no coinciden con el recibo.'
}
& $gh repo view $repo --json nameWithOwner,url,isPrivate,defaultBranchRef
Assert-NativeSuccess
```

Revisar `isPrivate = false` y default branch `main`. No usar `--mirror`, `--all`, force push ni subir tags/bundles. Si hay un fallo parcial después de crear el remoto, inspeccionar el estado real antes de reintentar; no repetir ciegamente la creación.

### C. PR académico, solo con autorización adicional

Después de comprobar ambas ramas remotas, se podrá abrir un PR real con base `main` y head `development`. El diff contendrá los entregables académicos acumulados y este informe. Preparar el cuerpo fuera del árbol y revisar antes de enviarlo:

```powershell
@'
Incorpora la entrega académica validada de detección de fraude, interpretabilidad y monitoreo offline sobre una baseline saneada.

Se conservan notebooks, código, champion, métricas, HTML, documentación y dashboard. El historial público es independiente; la trazabilidad y el respaldo privado están documentados en PHASE_7B_PUBLIC_HISTORY_REPORT.md.

Validación: 59 tests, cinco notebooks, cinco vistas Streamlit y verificación de integridad/seguridad. DagsHub sigue pendiente como evidencia externa. No se ha reentrenado ni modificado el modelo o sus resultados.
'@ | Set-Content ../public-history-pr-body.md -Encoding utf8
& $gh pr create --repo $repo --base main --head development --title 'Prepare validated academic fraud monitoring delivery' --body-file ../public-history-pr-body.md
Assert-NativeSuccess
```

No ejecutar ese último comando con la autorización limitada a crear/publicar ramas. Registrar la URL real del PR y revisar su diff/estado de integración. Merge, tags y release son pasos posteriores que requieren autorización propia; no se incluyen comandos para ellos aquí.

## 11. Pendientes y decisión solicitada

El bloqueo por rutas privadas del historial queda resuelto **para la copia independiente revisada**. El repositorio original sigue conteniendo esas rutas históricas y debe mantenerse privado/local.

Continúan pendientes: cuenta/repositorio/endpoint DagsHub, credenciales y permisos verificados, migración de runs con mapping de IDs, comparación de artifacts descargados, acceso del evaluador y URLs reales. No se usaron tokens DagsHub ni se hicieron conexiones remotas durante esta preparación.

Se solicita autorización para la siguiente fase: crear el repositorio público en `elverluiszuniga-netizen` y publicar únicamente `main` y `development` desde la copia preparada y sus SHA del recibo final. Abrir PR, mergear y crear release quedan fuera de esa autorización salvo aprobación expresa adicional.

**DETENIDO tras la preparación, commits locales de la copia y verificación final.**
