# Script para ejecutar archivos SQL en un contenedor Docker
# Guarda este script como Execute-SqlFiles.ps1

# Configura las variables
$containerName = "backend-laplace-db-1"  # Cambia al contenedor de la base de datos
$postgresUser = "postgres"
$postgresDb = "laplace"
$sqlDirectory = "C:\Users\Usuario\repo\backend-laplace\api\migrations"

# Obtener todos los archivos SQL del directorio y ordenarlos
$sqlFiles = Get-ChildItem -Path $sqlDirectory -Filter "*.sql" | Sort-Object Name

Write-Host "Se encontraron $($sqlFiles.Count) archivos SQL para ejecutar:" -ForegroundColor Cyan
$sqlFiles.Name | ForEach-Object { Write-Host "  - $_" }
Write-Host ""

# Ejecutar cada archivo SQL en el contenedor
foreach ($sqlFile in $sqlFiles) {
    $localPath = $sqlFile.FullName
    $containerPath = "/tmp/$($sqlFile.Name)"
    
    Write-Host "Procesando $($sqlFile.Name)..." -ForegroundColor Yellow
    
    # Paso 1: Copiar el archivo SQL al contenedor
    Write-Host "  Copiando archivo al contenedor..."
    docker cp "$localPath" "${containerName}:$containerPath"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ERROR: No se pudo copiar el archivo al contenedor." -ForegroundColor Red
        continue
    }
    
    # Paso 2: Ejecutar el archivo SQL
    Write-Host "  Ejecutando SQL..."
    docker exec $containerName psql -U $postgresUser -d $postgresDb -f $containerPath
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ Archivo ejecutado correctamente." -ForegroundColor Green
    }
    else {
        Write-Host "  ❌ Error al ejecutar el archivo." -ForegroundColor Red
    }
    
    # Opcional: Limpiar el archivo temporal
    docker exec $containerName rm $containerPath
    
    Write-Host ""
}

Write-Host "¡Proceso completado!" -ForegroundColor Green