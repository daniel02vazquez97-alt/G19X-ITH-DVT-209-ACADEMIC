# U14 (DT-102): guarded deployment of a minimal Azure Machine Learning workspace that reproduces the F5a backtest of the
# official baseline and logs it with MLflow. Run by the project owner from the repository root with an Azure CLI
# session already signed in and the `ml` extension installed (az extension add --name ml):
#
#     powershell -ExecutionPolicy Bypass -File infra\azure\deploy-u14.ps1 -PreflightOnly
#     powershell -ExecutionPolicy Bypass -File infra\azure\deploy-u14.ps1 -Stage <stage> [-Yes]
#
# Stages (infra/azure/u14/README.md):
#   -PreflightOnly (= -Stage Preflight, the default): STRICTLY read-only (allow list). Session, group, providers, the
#              `ml` extension, existing workspaces and the versioned F5a summary. PREFLIGHT OK or PREFLIGHT BLOQUEADO.
#   Deploy     validate -> what-if checked automatically (one workspace without container registry or Application
#              Insights, one Standard_LRS storage account without public blobs, one Key Vault; nothing else, no Delete)
#              -> AZUREML -> create.
#   Submit     builds the minimal code snapshot in tmp/u14-job, sends infra/azure/u14/job/job.yml (serverless,
#              Standard_DS2_v2), waits, downloads the model output to tmp/u14-evidence and, only if results_sha256
#              equals the versioned report, registers the model baseline-ma13.
#   Verify     workspace, last job Completed, results_sha256 equal to the versioned one, model registered, no compute
#              left and no endpoints; tmp/u14-evidence/u14-evidence.json (identifiers only).
#   Remove     tear-down (BORRAR): workspace with all its dependent resources, permanently, and purge of the Key Vault.
#   -SelfTest  offline checks of the what-if guard (no Azure call).
# It never reads, asks for, stores or prints a key, a token or a connection string. ASCII only.

[CmdletBinding()]
param(
    [ValidateSet('Preflight', 'Deploy', 'Submit', 'Verify', 'Remove')]
    [string]$Stage = 'Preflight',
    [switch]$Yes,
    [switch]$SelfTest,
    [switch]$PreflightOnly
)

$ErrorActionPreference = 'Stop'
if ($PreflightOnly) {
    if ($PSBoundParameters.ContainsKey('Stage') -and $Stage -ne 'Preflight') { Write-Host "-PreflightOnly no se combina con -Stage $Stage" -ForegroundColor Red; exit 2 }
    $Stage = 'Preflight'
}
$script:ReadOnly = ($Stage -eq 'Preflight' -and -not $SelfTest)

$ResourceGroup = 'rg-motor-predictivo-dev'
$Location = 'centralus'
$ExpectedTenant = '6ce4b1ba-ae4f-4887-bd6b-acb3c72039ad'
$Template = 'infra/azure/u14/main.bicep'
$Parameters = 'infra/azure/u14/dev.bicepparam'
$DeploymentName = 'u14-dev'
$WorkspaceName = 'mlw-mpa-dev'
$ModelName = 'baseline-ma13'
$JobFile = 'infra/azure/u14/job/job.yml'
$SnapshotDir = 'tmp/u14-job'
$EvidenceDir = 'tmp/u14-evidence'
$VersionedReport = 'docs/reports/fase5-f5a-backtest-sintetico.json'
$AllowedTypes = @('Microsoft.MachineLearningServices/workspaces', 'Microsoft.Storage/storageAccounts', 'Microsoft.KeyVault/vaults')
$TerminalStates = @('Completed', 'Failed', 'Canceled', 'NotResponding')

function Step([string]$Text) { Write-Host ''; Write-Host "== $Text" -ForegroundColor Cyan }
function Stop-U14([string]$Text) {
    Write-Host ''; Write-Host "DETENIDO: $Text" -ForegroundColor Red
    if ($script:ReadOnly) { Write-Host 'PREFLIGHT BLOQUEADO' -ForegroundColor Red }
    exit 1
}
function Get-Prop($Object, [string]$Name) {
    if ($null -eq $Object) { return $null }
    if ($Object -is [System.Collections.IDictionary]) { return $Object[$Name] }
    $p = $Object.PSObject.Properties[$Name]
    if ($null -eq $p) { return $null }
    return $p.Value
}
function To-List($Value) {
    $items = New-Object System.Collections.Generic.List[object]
    if ($null -eq $Value) { return ,$items.ToArray() }
    if ($Value -is [System.Array]) { foreach ($v in $Value) { if ($null -ne $v) { $items.Add($v) } } } else { $items.Add($Value) }
    return ,$items.ToArray()
}

# Read-only allow list for the preflight: show/list/version only.
function Test-ReadOnlyAz([string[]]$Arguments) {
    $joined = ($Arguments | Where-Object { $_ -notlike '-*' } | Select-Object -First 4) -join ' '
    foreach ($ok in @('account show', 'group show', 'provider show', 'extension show', 'resource list', 'version')) {
        if ($joined.StartsWith($ok)) { return $true }
    }
    return $false
}

function Invoke-Az {
    param([string[]]$Arguments, [switch]$Raw, [string]$What = 'az', [switch]$AllowFailure)
    if ($Arguments -contains 'keys' -or $Arguments -contains 'list-keys' -or $Arguments -contains 'show-connection-string') { Stop-U14 'U14 nunca lee claves ni cadenas de conexion' }
    if ($script:ReadOnly -and -not (Test-ReadOnlyAz $Arguments)) { Stop-U14 ("comando no permitido en modo solo lectura: az " + (($Arguments | Select-Object -First 3) -join ' ')) }
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $output = & az @Arguments 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = $previous
    if ($code -ne 0) {
        if ($AllowFailure) { return $null }
        Write-Host (($output | ForEach-Object { "$_" }) -join "`n")
        Stop-U14 "$What fallo (codigo $code)"
    }
    $json = ($output | Where-Object { $_ -isnot [System.Management.Automation.ErrorRecord] } | ForEach-Object { "$_" }) -join "`n"
    if ($Raw) { return $json }
    if ([string]::IsNullOrWhiteSpace($json)) { return $null }
    return (ConvertFrom-Json -InputObject $json)
}

function Confirm-Or-Stop([string]$Word, [string]$Prompt) {
    if ($Yes) { return }
    $answer = Read-Host "Escribe $Word para $Prompt"
    if ($answer -cne $Word) { Stop-U14 'cancelado por el responsable' }
}

function Get-ChangePayload($Change) {
    $after = Get-Prop $Change 'after'
    if ($null -ne $after) { return $after }
    return (Get-Prop $Change 'before')
}

# What-if guard (pure; -SelfTest). Returns the list of problems; empty = conforming.
function Test-U14WhatIf($WhatIf, [string]$RgId) {
    $problems = New-Object System.Collections.Generic.List[string]
    $count = @{}
    foreach ($c in (To-List (Get-Prop $WhatIf 'changes'))) {
        $kind = "$(Get-Prop $c 'changeType')"
        if ($kind -eq 'Ignore') { continue }
        $id = "$(Get-Prop $c 'resourceId')"
        $a = Get-ChangePayload $c
        $type = "$(Get-Prop $a 'type')"
        if (-not $type) { $problems.Add("cambio sin tipo: $id"); continue }
        if ($kind -notin @('Create', 'Modify', 'NoChange')) { $problems.Add("cambio no permitido: $kind en $id"); continue }
        if ($type -notin $AllowedTypes) { $problems.Add("recurso inesperado: $type ($id)"); continue }
        if (-not $id.StartsWith($RgId + '/', [System.StringComparison]::OrdinalIgnoreCase)) { $problems.Add("fuera del grupo: $id") }
        $count[$type] = 1 + [int]$count[$type]
        $p = Get-Prop $a 'properties'
        $loc = "$(Get-Prop $a 'location')"
        if ($loc -and ($loc -replace ' ', '').ToLower() -ne $Location) { $problems.Add("region distinta de ${Location}: $loc") }
        switch ($type) {
            'Microsoft.Storage/storageAccounts' {
                if ("$(Get-Prop (Get-Prop $a 'sku') 'name')" -ne 'Standard_LRS') { $problems.Add("almacenamiento distinto de Standard_LRS: $(Get-Prop (Get-Prop $a 'sku') 'name')") }
                if ((Get-Prop $p 'allowBlobPublicAccess') -ne $false) { $problems.Add('almacenamiento con acceso publico a blobs') }
                if ("$(Get-Prop $p 'minimumTlsVersion')" -ne 'TLS1_2') { $problems.Add('almacenamiento sin TLS 1.2 minimo') }
            }
            'Microsoft.KeyVault/vaults' {
                if ("$(Get-Prop (Get-Prop $p 'sku') 'name')" -notin @('standard', 'Standard')) { $problems.Add('Key Vault distinto de Standard') }
                if ((Get-Prop $p 'enablePurgeProtection') -eq $true) { $problems.Add('Key Vault con proteccion de purga (impediria el desmontaje)') }
            }
            'Microsoft.MachineLearningServices/workspaces' {
                if ("$(Get-Prop $a 'kind')" -notin @('', 'Default')) { $problems.Add("workspace de tipo $(Get-Prop $a 'kind'), no Default") }
                if ("$(Get-Prop $p 'containerRegistry')") { $problems.Add('workspace con registro de contenedores (DT-102: sin ACR)') }
                if ("$(Get-Prop $p 'applicationInsights')") { $problems.Add('workspace con Application Insights (DT-102: sin Application Insights)') }
            }
        }
    }
    foreach ($t in $AllowedTypes) { if ([int]$count[$t] -ne 1) { $problems.Add("se esperaba 1 recurso $t y hay $([int]$count[$t])") } }
    return ,$problems.ToArray()
}

function New-SelfTestCase([string]$Rg, $WorkspaceProps, $StorageProps, [string]$Extra) {
    $p = "$Rg/providers"
    $changes = @(
        @{ changeType = 'Create'; resourceId = "$p/Microsoft.Storage/storageAccounts/stmpamlx"; after = @{ type = 'Microsoft.Storage/storageAccounts'; location = 'centralus'; sku = @{ name = 'Standard_LRS' }; properties = $StorageProps } },
        @{ changeType = 'Create'; resourceId = "$p/Microsoft.KeyVault/vaults/kv-mpaml-x"; after = @{ type = 'Microsoft.KeyVault/vaults'; location = 'centralus'; properties = @{ sku = @{ family = 'A'; name = 'standard' } } } },
        @{ changeType = 'Create'; resourceId = "$p/Microsoft.MachineLearningServices/workspaces/mlw-mpa-dev"; after = @{ type = 'Microsoft.MachineLearningServices/workspaces'; location = 'centralus'; kind = 'Default'; properties = $WorkspaceProps } }
    )
    if ($Extra) { $changes += @{ changeType = $Extra; resourceId = "$p/Microsoft.ContainerRegistry/registries/crx"; after = @{ type = 'Microsoft.ContainerRegistry/registries' } } }
    return (ConvertTo-Json -InputObject @{ changes = $changes } -Depth 20 | ConvertFrom-Json)
}

function Invoke-SelfTest {
    $rg = '/subscriptions/s/resourceGroups/rg'
    $ws = @{ storageAccount = 'st'; keyVault = 'kv'; publicNetworkAccess = 'Enabled' }
    $st = @{ allowBlobPublicAccess = $false; minimumTlsVersion = 'TLS1_2'; supportsHttpsTrafficOnly = $true }
    $cases = @(
        @('conforme', (New-SelfTestCase $rg $ws $st ''), 0),
        @('workspace con ACR', (New-SelfTestCase $rg @{ storageAccount = 'st'; keyVault = 'kv'; containerRegistry = 'cr' } $st ''), 1),
        @('workspace con Application Insights', (New-SelfTestCase $rg @{ storageAccount = 'st'; keyVault = 'kv'; applicationInsights = 'ai' } $st ''), 1),
        @('blobs publicos', (New-SelfTestCase $rg $ws @{ allowBlobPublicAccess = $true; minimumTlsVersion = 'TLS1_2' } ''), 1),
        @('TLS 1.0', (New-SelfTestCase $rg $ws @{ allowBlobPublicAccess = $false; minimumTlsVersion = 'TLS1_0' } ''), 1),
        @('recurso ajeno (ACR)', (New-SelfTestCase $rg $ws $st 'Create'), 1),
        @('borrado', (New-SelfTestCase $rg $ws $st 'Delete'), 1)
    )
    $failed = 0
    foreach ($case in $cases) {
        $problems = Test-U14WhatIf $case[1] $rg
        $ok = if ($case[2] -eq 0) { $problems.Count -eq 0 } else { $problems.Count -gt 0 }
        if ($ok) { Write-Host "  OK    $($case[0])" } else { $failed++; Write-Host "  FALLO $($case[0]): $($problems -join '; ')" -ForegroundColor Red }
    }
    if ($failed) { Write-Host "SELFTEST: $failed fallos" -ForegroundColor Red; exit 1 }
    Write-Host "SELFTEST OK ($($cases.Count) casos)" -ForegroundColor Green
    exit 0
}

if ($SelfTest) { Invoke-SelfTest }

function Get-Context {
    $account = Invoke-Az @('account', 'show', '--output', 'json') -What 'az account show'
    if ("$($account.tenantId)" -ne $ExpectedTenant) { Stop-U14 'la sesion no es del tenant de U10' }
    $rg = Invoke-Az @('group', 'show', '--name', $ResourceGroup, '--output', 'json') -What 'az group show'
    if ("$($rg.location)" -ne $Location) { Stop-U14 "el grupo no esta en $Location" }
    return @{ rgId = "$($rg.id)" }
}

function Get-VersionedSha {
    if (-not (Test-Path $VersionedReport)) { Stop-U14 "falta $VersionedReport" }
    $sha = "$((Get-Content -Raw -Path $VersionedReport | ConvertFrom-Json).results_sha256)"
    if ($sha -notmatch '^[0-9a-f]{64}$') { Stop-U14 'results_sha256 del informe versionado no valido' }
    return $sha
}

function Get-WsArgs { return @('--resource-group', $ResourceGroup, '--workspace-name', $WorkspaceName) }

# Minimal code snapshot of the job: what python -m ml backtest and the wrapper need, nothing else (no secrets, no .git,
# no dataset output, no frontend).
function New-Snapshot {
    if (Test-Path $SnapshotDir) { Remove-Item -Recurse -Force $SnapshotDir }
    New-Item -ItemType Directory -Force -Path $SnapshotDir | Out-Null
    $root = (Resolve-Path '.').Path
    $dirs = @('backend/app', 'ml', 'data/synthetic/generator', 'data/synthetic/config', 'infra/azure/u14/job')
    # Never copied: caches, local outputs (ml/out is ~100 MB of F5b/F5c caches) and tests.
    $skip = '[\\/](__pycache__|out|tests)([\\/]|$)'
    $files = New-Object System.Collections.Generic.List[string]
    foreach ($dir in $dirs) {
        foreach ($f in (Get-ChildItem -Path $dir -Recurse -File)) {
            $rel = $f.FullName.Substring($root.Length + 1)
            if ($rel -notmatch $skip -and $f.Extension -ne '.pyc') { $files.Add($rel) }
        }
    }
    foreach ($f in @('data/__init__.py', 'data/synthetic/__init__.py', $VersionedReport)) { $files.Add($f) }
    foreach ($rel in $files) {
        $target = Join-Path $SnapshotDir $rel
        New-Item -ItemType Directory -Force -Path (Split-Path $target -Parent) | Out-Null
        Copy-Item -Path $rel -Destination $target
    }
    return (Resolve-Path $SnapshotDir).Path
}

function Check([bool]$Ok, [string]$Text) {
    if ($Ok) { Write-Host "  OK     $Text" } else { $script:Failed++; Write-Host "  FALLO  $Text" -ForegroundColor Red }
}

$script:Failed = 0
switch ($Stage) {
    'Preflight' {
        Step '1. Sesion y grupo'
        $ctx = Get-Context
        Write-Host "  OK     grupo $ResourceGroup en $Location"
        Step '2. Proveedores y extension ml'
        foreach ($ns in @('Microsoft.MachineLearningServices', 'Microsoft.Compute', 'Microsoft.Storage', 'Microsoft.KeyVault')) {
            $state = "$(Invoke-Az @('provider', 'show', '--namespace', $ns, '--query', 'registrationState', '--output', 'tsv') -Raw)".Trim()
            if ($state -ne 'Registered') { Stop-U14 "$ns esta $state (az provider register --namespace $ns --wait)" }
            Write-Host "  OK     $ns Registered"
        }
        $ext = Invoke-Az @('extension', 'show', '--name', 'ml', '--output', 'json') -What 'extension ml' -AllowFailure
        if ($null -eq $ext) { Stop-U14 'falta la extension ml de Azure CLI: az extension add --name ml' }
        Write-Host "  OK     extension ml $($ext.version)"
        Step '3. Estado actual'
        $ws = To-List (Invoke-Az @('resource', 'list', '--resource-group', $ResourceGroup, '--resource-type', 'Microsoft.MachineLearningServices/workspaces', '--output', 'json') -What 'workspaces')
        Write-Host "  INFO   workspaces de Azure ML en el grupo: $($ws.Count)"
        Write-Host "  OK     results_sha256 versionado: $(Get-VersionedSha)"
        Write-Host ''
        Write-Host 'PREFLIGHT OK' -ForegroundColor Green
    }
    'Deploy' {
        $ctx = Get-Context
        Step 'validate'
        Invoke-Az @('deployment', 'group', 'validate', '--resource-group', $ResourceGroup, '--name', $DeploymentName, '--template-file', $Template, '--parameters', $Parameters, '--output', 'none') -Raw -What 'validate' | Out-Null
        Step 'what-if'
        $whatIf = Invoke-Az @('deployment', 'group', 'what-if', '--resource-group', $ResourceGroup, '--name', $DeploymentName, '--template-file', $Template, '--parameters', $Parameters, '--no-pretty-print', '--output', 'json') -What 'what-if'
        foreach ($c in (To-List (Get-Prop $whatIf 'changes'))) { if ("$($c.changeType)" -ne 'Ignore') { Write-Host "  $($c.changeType)  $($c.resourceId)" } }
        $problems = Test-U14WhatIf $whatIf $ctx.rgId
        if ($problems.Count) { foreach ($p in $problems) { Write-Host "  PROBLEMA $p" -ForegroundColor Red }; Stop-U14 'el what-if no es el esperado' }
        Write-Host '  what-if conforme: workspace sin ACR ni Application Insights, almacenamiento Standard_LRS privado y Key Vault'
        Confirm-Or-Stop 'AZUREML' 'crear el workspace de Azure ML y sus dos recursos'
        Invoke-Az @('deployment', 'group', 'create', '--resource-group', $ResourceGroup, '--name', $DeploymentName, '--template-file', $Template, '--parameters', $Parameters, '--output', 'none') -Raw -What 'create' | Out-Null
        Write-Host 'Desplegado. Siguiente: -Stage Submit.' -ForegroundColor Green
    }
    'Submit' {
        $ctx = Get-Context
        $versioned = Get-VersionedSha
        Step 'Instantanea minima del codigo'
        $snapshot = New-Snapshot
        Write-Host "  $snapshot"
        Step 'Envio del job (serverless, Standard_DS2_v2)'
        $job = "$(Invoke-Az (@('ml', 'job', 'create', '--file', $JobFile, '--set', "code=$snapshot", '--query', 'name', '--output', 'tsv') + (Get-WsArgs)) -Raw -What 'az ml job create')".Trim()
        if (-not $job) { Stop-U14 'el job no devolvio nombre' }
        Write-Host "  job: $job"
        $deadline = (Get-Date).AddMinutes(60)
        do {
            Start-Sleep -Seconds 30
            $status = "$(Invoke-Az (@('ml', 'job', 'show', '--name', $job, '--query', 'status', '--output', 'tsv') + (Get-WsArgs)) -Raw -What 'estado del job')".Trim()
            Write-Host "  $(Get-Date -Format HH:mm:ss) $status"
        } while ($status -notin $TerminalStates -and (Get-Date) -lt $deadline)
        New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null
        $evidence = [ordered]@{ date = (Get-Date).ToUniversalTime().ToString('o'); job = $job; status = $status; versionedResultsSha256 = $versioned }
        if ($status -ne 'Completed') {
            Set-Content -Path (Join-Path $EvidenceDir 'u14-submit.json') -Value (ConvertTo-Json $evidence) -Encoding ASCII
            Stop-U14 "el job termino en $status (portal: el workspace > Jobs > $job > Outputs + logs)"
        }
        $download = Join-Path $EvidenceDir $job
        Invoke-Az (@('ml', 'job', 'download', '--name', $job, '--output-name', 'model', '--download-path', $download) + (Get-WsArgs)) -Raw -What 'descarga de la salida model' | Out-Null
        $cmpFile = Get-ChildItem -Path $download -Recurse -Filter 'comparison.json' | Select-Object -First 1
        if ($null -eq $cmpFile) { Stop-U14 'la salida model no contiene comparison.json' }
        $cmp = Get-Content -Raw -Path $cmpFile.FullName | ConvertFrom-Json
        $evidence.resultsSha256 = "$($cmp.results_sha256)"
        $evidence.reproduces = ("$($cmp.results_sha256)" -eq $versioned)
        if (-not $evidence.reproduces) {
            Set-Content -Path (Join-Path $EvidenceDir 'u14-submit.json') -Value (ConvertTo-Json $evidence) -Encoding ASCII
            Stop-U14 "results_sha256 $($cmp.results_sha256) distinto del versionado ${versioned}: hallazgo, no se registra el modelo"
        }
        Step "Registro del modelo $ModelName"
        $model = Invoke-Az (@('ml', 'model', 'create', '--name', $ModelName, '--type', 'custom_model', '--path', "azureml://jobs/$job/outputs/model", '--tags', "results_sha256=$versioned", "job=$job", 'decision=DT-102', 'data_origin=SYNTHETIC', '--output', 'json') + (Get-WsArgs)) -What 'az ml model create'
        $evidence.modelVersion = "$($model.version)"
        Set-Content -Path (Join-Path $EvidenceDir 'u14-submit.json') -Value (ConvertTo-Json $evidence) -Encoding ASCII
        Write-Host "  $ModelName version $($model.version)"
        Write-Host 'Job completado, resultado reproducido y modelo registrado. Siguiente: -Stage Verify.' -ForegroundColor Green
    }
    'Verify' {
        $ctx = Get-Context
        $versioned = Get-VersionedSha
        $submitFile = Join-Path $EvidenceDir 'u14-submit.json'
        if (-not (Test-Path $submitFile)) { Stop-U14 'falta tmp/u14-evidence/u14-submit.json (ejecuta -Stage Submit)' }
        $submit = Get-Content -Raw -Path $submitFile | ConvertFrom-Json
        $ws = Invoke-Az @('ml', 'workspace', 'show', '--name', $WorkspaceName, '--resource-group', $ResourceGroup, '--output', 'json') -What 'workspace'
        Check ("$($ws.location)" -eq $Location) "workspace $WorkspaceName en $Location"
        Check (-not "$($ws.container_registry)") 'workspace sin registro de contenedores'
        $job = Invoke-Az (@('ml', 'job', 'show', '--name', "$($submit.job)", '--output', 'json') + (Get-WsArgs)) -What 'job'
        Check ("$($job.status)" -eq 'Completed') "job $($submit.job) Completed"
        Check ("$($submit.resultsSha256)" -eq $versioned) "results_sha256 igual al informe versionado ($versioned)"
        $model = Invoke-Az (@('ml', 'model', 'show', '--name', $ModelName, '--label', 'latest', '--output', 'json') + (Get-WsArgs)) -What 'modelo' -AllowFailure
        Check ($null -ne $model -and "$($model.tags.results_sha256)" -eq $versioned) "modelo $ModelName registrado con results_sha256"
        $computes = To-List (Invoke-Az (@('ml', 'compute', 'list', '--output', 'json') + (Get-WsArgs)) -What 'computo')
        Check ($computes.Count -eq 0) 'sin instancias ni clusteres de computo (solo serverless)'
        $endpoints = To-List (Invoke-Az (@('ml', 'online-endpoint', 'list', '--output', 'json') + (Get-WsArgs)) -What 'endpoints')
        Check ($endpoints.Count -eq 0) 'sin endpoints de inferencia'
        $evidence = [ordered]@{ date = (Get-Date).ToUniversalTime().ToString('o'); workspace = "$($ws.id)"; job = "$($submit.job)"; jobStatus = "$($job.status)"; resultsSha256 = "$($submit.resultsSha256)"; versionedResultsSha256 = $versioned; model = $ModelName; modelVersion = "$($model.version)"; checksFailed = $script:Failed }
        Set-Content -Path (Join-Path $EvidenceDir 'u14-evidence.json') -Value (ConvertTo-Json $evidence) -Encoding ASCII
        if ($script:Failed) { Stop-U14 "$($script:Failed) comprobaciones fallidas" }
        Write-Host ''
        Write-Host 'U14: Azure ML verificado (backtesting reproducido y baseline registrado).' -ForegroundColor Green
    }
    'Remove' {
        $ctx = Get-Context
        $out = Invoke-Az @('deployment', 'group', 'show', '--resource-group', $ResourceGroup, '--name', $DeploymentName, '--query', 'properties.outputs', '--output', 'json') -What 'salidas de u14-dev'
        $kv = "$(Get-Prop (Get-Prop $out 'keyVaultName') 'value')"
        Write-Host "Se borraran de forma permanente el workspace $WorkspaceName y sus recursos dependientes, y se purgara el Key Vault $kv."
        Confirm-Or-Stop 'BORRAR' "borrar el workspace $WorkspaceName"
        Invoke-Az @('ml', 'workspace', 'delete', '--name', $WorkspaceName, '--resource-group', $ResourceGroup, '--all-resources', '--permanently-delete', '--yes') -Raw -What 'borrar el workspace' | Out-Null
        if ($kv) { Invoke-Az @('keyvault', 'purge', '--name', $kv, '--location', $Location) -Raw -What 'purgar el Key Vault' -AllowFailure | Out-Null }
        Write-Host 'U14 desmontada.' -ForegroundColor Green
    }
}
