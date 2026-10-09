# U10 (DT-098): guarded deployment of the Azure base of `dev`, run by the project owner from the repository
# root with an Azure CLI session that is already signed in:
#
#     powershell -ExecutionPolicy Bypass -File infra\azure\deploy-dev.ps1
#
# It never asks for or stores credentials and never prints tokens. Steps, each one a hard stop on failure:
#  1. active subscription is "Azure for Students" and enabled;
#  2. existing resource group: only if it is EMPTY and has NO locks, and only if it is in another region,
#     it is deleted (the region of a group cannot change);
#  3. local Bicep build, lint and parameter build;
#  4. resource providers registered (Microsoft.KeyVault, Microsoft.ManagedIdentity);
#  5. `az deployment sub validate`;
#  6. `az deployment sub what-if`, checked automatically: only Create, exactly the five U10 resources, all in
#     the expected region, Key Vault private with RBAC, OIDC subject limited to `dev`, only the Reader role.
#     Anything else prints "WHAT-IF NO AUTORIZADO" and stops before deploying;
#  7. confirmation (type DESPLEGAR; -Yes skips it), then `az deployment sub create`;
#  8. verification and an evidence file with identifiers only (tmp/u10-evidence/, ignored by Git).
#
# Options:
#   -SelfTest       checks, without calling Azure, that JSON lists from az are counted correctly by this
#                   PowerShell ("[]" -> 0); run it once on the machine that will deploy.
#   -PreflightOnly  runs steps 1-4 read-only (no deletion, no provider registration, no deployment) and stops.
#   -Yes            skips the DESPLEGAR confirmation.
#
# JSON lists (resources, locks, federated credentials, role assignments) are always read with
# ConvertFrom-AzJsonArray: Windows PowerShell 5.1 returns a JSON array from ConvertFrom-Json as ONE object,
# so wrapping it in @(...) counted "[]" as one element (the false positive of 2026-10-07).
# ASCII only on purpose: Windows PowerShell 5.1 reads scripts without BOM as ANSI.

[CmdletBinding()]
param(
    [switch]$Yes,
    [switch]$SelfTest,
    [switch]$PreflightOnly
)

$ErrorActionPreference = 'Stop'

$ResourceGroup = 'rg-motor-predictivo-dev'
$Location = 'centralus'  # must match param location in parameters/dev.bicepparam (DT-098)
$DeploymentName = 'u10-base-dev'
$Template = 'infra/azure/main.bicep'
$Parameters = 'infra/azure/parameters/dev.bicepparam'
$ExpectedSubject = 'repo:daniel02vazquez97-alt@290574726/G19X-ITH-DVT-209-ACADEMIC@1408075880:environment:dev'
$ReaderRoleId = 'acdd72a7-3385-48ef-bd42-f606fba81ae7'
$EvidenceDir = 'tmp/u10-evidence'

function Step([string]$Text) { Write-Host ''; Write-Host "== $Text" -ForegroundColor Cyan }
function Stop-U10([string]$Text) { Write-Host ''; Write-Host "DETENIDO: $Text" -ForegroundColor Red; exit 1 }

# Turns the text of a JSON array into a flat PowerShell array whatever the PowerShell version:
#   ""/"null"/"[]" -> 0 elements, "[{...}]" -> 1, "[{...},{...}]" -> 2.
# PowerShell 5.1 returns the array as a single object and PowerShell 7 enumerates it; both are normalised here,
# including the nested shape @( @() ) that @(...) produced around a 5.1 result. Nulls are never counted.
function ConvertFrom-AzJsonArray {
    param([AllowNull()][AllowEmptyString()][string]$Json)
    $items = New-Object System.Collections.Generic.List[object]
    if ([string]::IsNullOrWhiteSpace($Json)) { return ,$items.ToArray() }
    $parsed = ConvertFrom-Json -InputObject $Json
    if ($null -eq $parsed) { return ,$items.ToArray() }
    if ($parsed -isnot [System.Array]) {
        if ($parsed -is [string]) { throw "se esperaba una lista JSON y llego texto" }
        $items.Add($parsed)
        return ,$items.ToArray()
    }
    foreach ($element in $parsed) {
        if ($null -eq $element) { continue }
        if ($element -is [System.Array]) {
            foreach ($inner in $element) { if ($null -ne $inner) { $items.Add($inner) } }
        } else {
            $items.Add($element)
        }
    }
    return ,$items.ToArray()
}

# Runs az with the given arguments; returns parsed JSON (an array with -Array, raw text with -Raw). Stops on a
# non-zero exit.
function Invoke-Az {
    param([string[]]$Arguments, [switch]$Raw, [switch]$Array, [string]$What = 'az')
    # Windows PowerShell 5.1 turns native stderr into terminating errors under 'Stop'; az writes warnings there.
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $output = & az @Arguments 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = $previous
    $text = ($output | ForEach-Object { "$_" }) -join "`n"
    if ($code -ne 0) { Write-Host $text; Stop-U10 "$What fallo (codigo $code)" }
    if ($Raw) { return $text }
    $json = ($output | Where-Object { $_ -isnot [System.Management.Automation.ErrorRecord] } | ForEach-Object { "$_" }) -join "`n"
    if ($Array) { return ,(ConvertFrom-AzJsonArray $json) }
    if ([string]::IsNullOrWhiteSpace($json)) { return $null }
    return (ConvertFrom-Json -InputObject $json)
}

function Save-Evidence([string]$Name, $Object) {
    $Object | ConvertTo-Json -Depth 20 | Set-Content -Path (Join-Path $EvidenceDir $Name) -Encoding UTF8
}

if ($SelfTest) {
    $cases = [ordered]@{
        '[]' = 0; '' = 0; 'null' = 0; '[ ]' = 0
        '[{"name":"a","type":"t"}]' = 1
        '[{"name":"a","type":"t"},{"name":"b","type":"t"}]' = 2
    }
    $failed = 0
    foreach ($json in $cases.Keys) {
        $count = (ConvertFrom-AzJsonArray $json).Count
        $ok = ($count -eq $cases[$json])
        if (-not $ok) { $failed++ }
        Write-Host ("{0}  {1,-48} -> {2} (esperado {3})" -f ($(if ($ok) { 'OK  ' } else { 'FAIL' })), "'$json'", $count, $cases[$json])
    }
    $one = ConvertFrom-AzJsonArray '[{"name":"a","type":"t"}]'
    if ($one[0].name -ne 'a') { $failed++; Write-Host 'FAIL  el elemento no conserva sus propiedades' } else { Write-Host 'OK    el elemento conserva sus propiedades' }
    Write-Host ("PowerShell {0}: {1}" -f $PSVersionTable.PSVersion, $(if ($failed -eq 0) { 'SELFTEST OK' } else { "SELFTEST FALLO ($failed)" }))
    if ($failed -eq 0) { exit 0 } else { exit 1 }
}

if (-not (Test-Path $Template) -or -not (Test-Path $Parameters)) {
    Stop-U10 'ejecuta el script desde la raiz del repositorio'
}
New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null

# 1 --------------------------------------------------------------------------------------------------
Step '1. Suscripcion activa'
$account = Invoke-Az @('account', 'show', '--output', 'json') -What 'az account show'
Write-Host ("Suscripcion: {0} | estado: {1}" -f $account.name, $account.state)
if ($account.name -notmatch 'Azure for Students') { Stop-U10 "la suscripcion activa no es Azure for Students ($($account.name))" }
if ($account.state -ne 'Enabled') { Stop-U10 "la suscripcion no esta habilitada ($($account.state))" }

# 2 --------------------------------------------------------------------------------------------------
Step "2. Grupo de recursos existente: $ResourceGroup"
$exists = (Invoke-Az @('group', 'exists', '--name', $ResourceGroup) -Raw -What 'az group exists').Trim()
$keepGroup = $false
$previousGroup = $null
if ($exists -eq 'true') {
    $previousGroup = Invoke-Az @('group', 'show', '--name', $ResourceGroup, '--output', 'json') -What 'az group show'
    Write-Host ("Existe en {0}" -f $previousGroup.location)
    $resources = Invoke-Az @('resource', 'list', '--resource-group', $ResourceGroup, '--output', 'json') -Array -What 'az resource list'
    $locks = Invoke-Az @('lock', 'list', '--resource-group', $ResourceGroup, '--output', 'json') -Array -What 'az lock list'
    Write-Host ("Recursos: {0} | bloqueos: {1}" -f $resources.Count, $locks.Count)
    if ($resources.Count -gt 0) { $resources | ForEach-Object { Write-Host (" - {0} ({1})" -f $_.name, $_.type) }; Stop-U10 'el grupo contiene recursos; no se borra nada' }
    if ($locks.Count -gt 0) { $locks | ForEach-Object { Write-Host (" - bloqueo {0} ({1})" -f $_.name, $_.level) }; Stop-U10 'el grupo tiene bloqueos; no se borra nada' }
    Write-Host 'Grupo vacio y sin bloqueos: se puede eliminar.'
    if ($previousGroup.location -eq $Location) {
        $keepGroup = $true
        Write-Host "Ya esta en $Location`: se conserva."
    } elseif ($PreflightOnly) {
        Write-Host "PreflightOnly: no se borra (esta en $($previousGroup.location); el despliegue lo borraria)."
    } else {
        Write-Host "Vacio, sin bloqueos y en otra region: se borra."
        Invoke-Az @('group', 'delete', '--name', $ResourceGroup, '--yes') -Raw -What 'az group delete' | Out-Null
        $deadline = (Get-Date).AddMinutes(10)
        do {
            $exists = (Invoke-Az @('group', 'exists', '--name', $ResourceGroup) -Raw -What 'az group exists').Trim()
            if ($exists -eq 'false') { break }
            Start-Sleep -Seconds 10
        } while ((Get-Date) -lt $deadline)
        if ($exists -ne 'false') { Stop-U10 'el grupo sigue existiendo tras borrarlo' }
        Write-Host 'Borrado: az group exists = false'
    }
} else {
    Write-Host 'No existe: la plantilla lo creara.'
}

# 3 --------------------------------------------------------------------------------------------------
Step '3. Validacion local de Bicep'
Invoke-Az @('bicep', 'build', '--file', $Template, '--stdout') -Raw -What 'az bicep build' | Out-Null
Invoke-Az @('bicep', 'lint', '--file', $Template) -Raw -What 'az bicep lint' | Out-Null
Invoke-Az @('bicep', 'build-params', '--file', $Parameters, '--stdout') -Raw -What 'az bicep build-params' | Out-Null
Write-Host 'build, lint y build-params correctos'

# 4 --------------------------------------------------------------------------------------------------
Step '4. Proveedores de recursos'
foreach ($ns in @('Microsoft.KeyVault', 'Microsoft.ManagedIdentity')) {
    $state = (Invoke-Az @('provider', 'show', '--namespace', $ns, '--query', 'registrationState', '--output', 'tsv') -Raw -What "az provider show $ns").Trim()
    if ($state -ne 'Registered' -and $PreflightOnly) {
        Write-Host "$ns`: $state (PreflightOnly: no se registra)"
    } elseif ($state -ne 'Registered') {
        Write-Host "$ns`: $state -> registrando"
        Invoke-Az @('provider', 'register', '--namespace', $ns, '--wait') -Raw -What "az provider register $ns" | Out-Null
    } else { Write-Host "$ns`: Registered" }
}

if ($PreflightOnly) {
    Write-Host ''
    Write-Host 'PREFLIGHT OK: pasos 1-4 correctos; no se borro, registro ni desplego nada.' -ForegroundColor Green
    exit 0
}

$deployArgs = @('--name', $DeploymentName, '--location', $Location, '--template-file', $Template, '--parameters', $Parameters)

# 5 --------------------------------------------------------------------------------------------------
Step '5. az deployment sub validate'
$validation = Invoke-Az (@('deployment', 'sub', 'validate') + $deployArgs + @('--output', 'json')) -What 'validate'
if ($validation.error) { Stop-U10 ("validate devolvio error: {0}" -f ($validation.error | ConvertTo-Json -Depth 10)) }
Write-Host ("validate: {0}" -f $validation.properties.provisioningState)

# 6 --------------------------------------------------------------------------------------------------
Step '6. az deployment sub what-if (comprobacion automatica)'
$whatIf = Invoke-Az (@('deployment', 'sub', 'what-if') + $deployArgs + @('--result-format', 'FullResourcePayloads', '--no-pretty-print', '--output', 'json')) -What 'what-if'
Save-Evidence 'what-if.json' $whatIf
$problems = New-Object System.Collections.Generic.List[string]
$changes = @($whatIf.changes | Where-Object { $_.changeType -ne 'Ignore' })
$rgId = "/subscriptions/$($account.id)/resourceGroups/$ResourceGroup"
$seen = @{}
foreach ($c in $changes) {
    $after = $c.after
    $type = if ($after) { $after.type } else { '(sin payload)' }
    Write-Host (" {0,-9} {1}" -f $c.changeType, $c.resourceId)
    if ($c.changeType -eq 'NoChange' -and $keepGroup -and $type -eq 'Microsoft.Resources/resourceGroups') { $seen[$type] = $true; continue }
    if ($c.changeType -ne 'Create') { $problems.Add("cambio no permitido: $($c.changeType) en $($c.resourceId)"); continue }
    if ($seen.ContainsKey($type)) { $problems.Add("recurso repetido: $type") }
    $seen[$type] = $true
    switch ($type) {
        'Microsoft.Resources/resourceGroups' {
            if ($after.name -ne $ResourceGroup) { $problems.Add("grupo con otro nombre: $($after.name)") }
            if ($after.location -ne $Location) { $problems.Add("grupo en otra region: $($after.location)") }
        }
        'Microsoft.KeyVault/vaults' {
            if ($after.location -ne $Location) { $problems.Add("Key Vault en otra region: $($after.location)") }
            if ($after.properties.enableRbacAuthorization -ne $true) { $problems.Add('Key Vault sin RBAC') }
            if ($after.properties.publicNetworkAccess -ne 'Disabled') { $problems.Add('Key Vault con acceso publico') }
            if (-not $c.resourceId.StartsWith($rgId, [System.StringComparison]::OrdinalIgnoreCase)) { $problems.Add('Key Vault fuera del grupo') }
        }
        'Microsoft.ManagedIdentity/userAssignedIdentities' {
            if ($after.location -ne $Location) { $problems.Add("identidad en otra region: $($after.location)") }
            if (-not $c.resourceId.StartsWith($rgId, [System.StringComparison]::OrdinalIgnoreCase)) { $problems.Add('identidad fuera del grupo') }
        }
        'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials' {
            if ($after.properties.subject -cne $ExpectedSubject) { $problems.Add("sujeto OIDC inesperado: $($after.properties.subject)") }
            if ($after.properties.issuer -ne 'https://token.actions.githubusercontent.com') { $problems.Add('emisor OIDC inesperado') }
        }
        'Microsoft.Authorization/roleAssignments' {
            if (-not "$($after.properties.roleDefinitionId)".EndsWith($ReaderRoleId)) { $problems.Add("rol distinto de Reader: $($after.properties.roleDefinitionId)") }
            if (-not $c.resourceId.StartsWith($rgId, [System.StringComparison]::OrdinalIgnoreCase)) { $problems.Add('asignacion de rol fuera del grupo') }
        }
        default { $problems.Add("recurso inesperado: $type ($($c.resourceId))") }
    }
}
$expectedTypes = @('Microsoft.Resources/resourceGroups', 'Microsoft.KeyVault/vaults', 'Microsoft.ManagedIdentity/userAssignedIdentities',
    'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials', 'Microsoft.Authorization/roleAssignments')
foreach ($t in $expectedTypes) { if (-not $seen.ContainsKey($t)) { $problems.Add("falta el recurso esperado: $t") } }
if ($whatIf.status -and $whatIf.status -ne 'Succeeded') { $problems.Add("what-if con estado $($whatIf.status)") }
if ($problems.Count -gt 0) {
    Write-Host ''
    Write-Host 'WHAT-IF NO AUTORIZADO' -ForegroundColor Red
    $problems | ForEach-Object { Write-Host " - $_" }
    exit 2
}
Write-Host ("what-if conforme: {0} cambios, solo los cinco recursos de U10 en {1}" -f $changes.Count, $Location) -ForegroundColor Green

# 7 --------------------------------------------------------------------------------------------------
Step '7. Despliegue real'
if (-not $Yes) {
    $answer = Read-Host 'Escribe DESPLEGAR para crear los recursos (cualquier otra cosa cancela)'
    if ($answer -cne 'DESPLEGAR') { Stop-U10 'cancelado por el responsable; no se creo nada' }
}
$deployment = Invoke-Az (@('deployment', 'sub', 'create') + $deployArgs + @('--output', 'json')) -What 'create'
$state = $deployment.properties.provisioningState
Write-Host "create: $state"
if ($state -ne 'Succeeded') { Stop-U10 "el despliegue termino en $state" }
$outputs = $deployment.properties.outputs

# 8 --------------------------------------------------------------------------------------------------
Step '8. Verificacion'
$group = Invoke-Az @('group', 'show', '--name', $ResourceGroup, '--output', 'json') -What 'az group show'
$resources = Invoke-Az @('resource', 'list', '--resource-group', $ResourceGroup, '--output', 'json') -Array -What 'az resource list'
$kv = Invoke-Az @('keyvault', 'show', '--name', $outputs.keyVaultName.value, '--output', 'json') -What 'az keyvault show'
$identity = Invoke-Az @('identity', 'show', '--name', $outputs.githubIdentityName.value, '--resource-group', $ResourceGroup, '--output', 'json') -What 'az identity show'
$federations = Invoke-Az @('identity', 'federated-credential', 'list', '--identity-name', $identity.name, '--resource-group', $ResourceGroup, '--output', 'json') -Array -What 'az identity federated-credential list'
$roles = Invoke-Az @('role', 'assignment', 'list', '--all', '--assignee', $identity.principalId, '--output', 'json') -Array -What 'az role assignment list'
$outputResources = @($deployment.properties.outputResources | ForEach-Object { $_.id })

$checks = [ordered]@{
    'grupo en la region esperada'          = ($group.location -eq $Location)
    'solo recursos de U10 en el grupo'       = (@($resources | Where-Object { $_.type -notin @('Microsoft.KeyVault/vaults', 'Microsoft.ManagedIdentity/userAssignedIdentities', 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials') }).Count -eq 0 -and @($resources | Where-Object { $_.type -eq 'Microsoft.KeyVault/vaults' }).Count -eq 1 -and @($resources | Where-Object { $_.type -eq 'Microsoft.ManagedIdentity/userAssignedIdentities' }).Count -eq 1)
    'Key Vault con RBAC'                    = ($kv.properties.enableRbacAuthorization -eq $true)
    'Key Vault sin acceso publico'          = ($kv.properties.publicNetworkAccess -eq 'Disabled')
    'una sola credencial federada'          = ($federations.Count -eq 1)
    'sujeto OIDC limitado a dev'            = ($federations.Count -eq 1 -and $federations[0].subject -ceq $ExpectedSubject)
    'una sola asignacion de rol: Reader'    = ($roles.Count -eq 1 -and $roles[0].roleDefinitionName -eq 'Reader')
    'rol limitado al grupo'                 = ($roles.Count -eq 1 -and $roles[0].scope -eq $group.id)
    'nada creado fuera del grupo'           = (@($outputResources | Where-Object { -not $_.StartsWith($group.id, [System.StringComparison]::OrdinalIgnoreCase) }).Count -eq 0)
}
$failed = 0
foreach ($k in $checks.Keys) {
    $ok = [bool]$checks[$k]
    if (-not $ok) { $failed++ }
    Write-Host ("{0}  {1}" -f ($(if ($ok) { 'OK  ' } else { 'FAIL' })), $k)
}

$evidence = [ordered]@{
    date                       = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    subscription               = $account.name
    subscriptionId             = $account.id
    tenantId                   = $account.tenantId
    previousResourceGroup      = $(if ($previousGroup) { [ordered]@{ location = $previousGroup.location; deleted = (-not $keepGroup) } } else { $null })
    whatIfChanges              = @($changes | ForEach-Object { [ordered]@{ changeType = $_.changeType; resourceId = $_.resourceId } })
    deployment                 = [ordered]@{ name = $DeploymentName; provisioningState = $state; timestamp = $deployment.properties.timestamp; outputResources = $outputResources }
    resourceGroup              = [ordered]@{ name = $group.name; id = $group.id; location = $group.location; tags = $group.tags }
    keyVault                   = [ordered]@{ name = $kv.name; id = $kv.id; location = $kv.location; sku = $kv.properties.sku.name;
                                     enableRbacAuthorization = $kv.properties.enableRbacAuthorization; publicNetworkAccess = $kv.properties.publicNetworkAccess;
                                     softDeleteRetentionInDays = $kv.properties.softDeleteRetentionInDays; enablePurgeProtection = $kv.properties.enablePurgeProtection; tags = $kv.tags }
    managedIdentity            = [ordered]@{ name = $identity.name; id = $identity.id; location = $identity.location; principalId = $identity.principalId; clientId = $identity.clientId; tags = $identity.tags }
    federatedCredentials       = @($federations | ForEach-Object { [ordered]@{ name = $_.name; issuer = $_.issuer; subject = $_.subject; audiences = $_.audiences } })
    roleAssignments            = @($roles | ForEach-Object { [ordered]@{ role = $_.roleDefinitionName; scope = $_.scope; id = $_.id } })
    resourcesInGroup           = @($resources | ForEach-Object { [ordered]@{ name = $_.name; type = $_.type; location = $_.location } })
    checksFailed               = $failed
}
Save-Evidence 'u10-evidence.json' $evidence
Write-Host ''
Write-Host "Evidencia (solo identificadores, sin secretos): $EvidenceDir/u10-evidence.json"
if ($failed -gt 0) { Stop-U10 "$failed comprobaciones posteriores fallaron" }
Write-Host 'U10 desplegada y verificada.' -ForegroundColor Green
