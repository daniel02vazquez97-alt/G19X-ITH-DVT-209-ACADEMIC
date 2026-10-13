# U13 (DT-101): guarded deployment of Azure OpenAI for the explanations of the API, run by the project owner from the
# repository root with an Azure CLI session that is already signed in (as deploy-u12.ps1):
#
#     powershell -ExecutionPolicy Bypass -File infra\azure\deploy-u13.ps1 -PreflightOnly
#     powershell -ExecutionPolicy Bypass -File infra\azure\deploy-u13.ps1 -Stage <stage> [-Yes]
#
# Stages (infra/azure/u13/README.md):
#   -PreflightOnly (same as -Stage Preflight, the default): STRICTLY read-only (every az call is checked against an
#              allow list). Session and subscription, group, runtime identity of U12, provider, the model in the
#              catalog of the region (version, Global Standard, retirement date) and the quota. PREFLIGHT OK or
#              PREFLIGHT BLOQUEADO.
#   Deploy     validate -> what-if checked automatically (one OpenAI account without keys, one deployment of the
#              chosen model, one "Cognitive Services OpenAI User" assignment to the runtime identity ON THE ACCOUNT;
#              nothing else, no Delete) -> OPENAI -> create.
#   Verify     checks of the deployed account, deployment and role, and tmp/u12-evidence/u13-evidence.json
#              (identifiers only). Then: genaiEnabled = true in infra/azure/u12/dev.bicepparam, Deploy dev and
#              deploy-u12.ps1 -Stage Apps.
#   Remove     tear-down (BORRAR): role assignment, deployment, account, and purge of the soft-deleted account.
#   -SelfTest  offline checks of the what-if guard (no Azure call).
# It never reads, asks for, stores or prints a key or a token: the account has disableLocalAuth. ASCII only.

[CmdletBinding()]
param(
    [ValidateSet('Preflight', 'Deploy', 'Verify', 'Remove')]
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
$Template = 'infra/azure/u13/main.bicep'
$Parameters = 'infra/azure/u13/dev.bicepparam'
$DeploymentName = 'u13-dev'
$EvidenceDir = 'tmp/u12-evidence'
$RuntimeIdentityName = 'id-mpa-dev-runtime'
# Must match infra/azure/u13/dev.bicepparam (a test checks it).
$ModelName = 'gpt-4.1-mini'
$ModelVersion = '2025-04-14'
$DeploymentSku = 'GlobalStandard'
$ModelDeployment = 'gpt-41-mini'
$Capacity = 10
$MaxCapacity = 50
$QuotaName = 'OpenAI.GlobalStandard.gpt4.1-mini'
# Cognitive Services OpenAI User (Microsoft Learn, "Azure built-in roles"): inference only.
$OpenAIUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
$AllowedTypes = @('Microsoft.CognitiveServices/accounts', 'Microsoft.CognitiveServices/accounts/deployments',
    'Microsoft.Authorization/roleAssignments')

function Step([string]$Text) { Write-Host ''; Write-Host "== $Text" -ForegroundColor Cyan }
function Stop-U13([string]$Text) {
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
    foreach ($ok in @('account show', 'group show', 'provider show', 'identity show', 'cognitiveservices model list',
            'cognitiveservices usage list', 'cognitiveservices account list', 'version')) {
        if ($joined.StartsWith($ok)) { return $true }
    }
    return $false
}

function Invoke-Az {
    param([string[]]$Arguments, [switch]$Raw, [string]$What = 'az', [switch]$AllowFailure)
    if ($Arguments -contains 'keys') { Stop-U13 'U13 nunca lee claves de la cuenta' }
    if ($script:ReadOnly -and -not (Test-ReadOnlyAz $Arguments)) { Stop-U13 ("comando no permitido en modo solo lectura: az " + (($Arguments | Select-Object -First 3) -join ' ')) }
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $output = & az @Arguments 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = $previous
    if ($code -ne 0) {
        if ($AllowFailure) { return $null }
        Write-Host (($output | ForEach-Object { "$_" }) -join "`n")
        Stop-U13 "$What fallo (codigo $code)"
    }
    $json = ($output | Where-Object { $_ -isnot [System.Management.Automation.ErrorRecord] } | ForEach-Object { "$_" }) -join "`n"
    if ($Raw) { return $json }
    if ([string]::IsNullOrWhiteSpace($json)) { return $null }
    return (ConvertFrom-Json -InputObject $json)
}

function Confirm-Or-Stop([string]$Word, [string]$Prompt) {
    if ($Yes) { return }
    $answer = Read-Host "Escribe $Word para $Prompt"
    if ($answer -cne $Word) { Stop-U13 'cancelado por el responsable' }
}

function Get-ChangePayload($Change) {
    $after = Get-Prop $Change 'after'
    if ($null -ne $after) { return $after }
    return (Get-Prop $Change 'before')
}

# What-if guard (pure; -SelfTest). Returns the list of problems; empty = conforming.
function Test-U13WhatIf($WhatIf, [string]$RgId, [string]$RuntimePrincipalId) {
    $problems = New-Object System.Collections.Generic.List[string]
    $count = @{}
    $accountId = ''
    $assignments = New-Object System.Collections.Generic.List[object]
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
            'Microsoft.CognitiveServices/accounts' {
                $accountId = $id
                if ("$(Get-Prop $a 'kind')" -cne 'OpenAI') { $problems.Add("la cuenta no es de tipo OpenAI: $(Get-Prop $a 'kind')") }
                if ("$(Get-Prop (Get-Prop $a 'sku') 'name')" -ne 'S0') { $problems.Add('la cuenta no es S0') }
                if ((Get-Prop $p 'disableLocalAuth') -ne $true) { $problems.Add('la cuenta admitiria claves (disableLocalAuth no es true)') }
                if (-not "$(Get-Prop $p 'customSubDomainName')") { $problems.Add('la cuenta sin subdominio propio (Entra ID lo exige)') }
            }
            'Microsoft.CognitiveServices/accounts/deployments' {
                $m = Get-Prop $p 'model'
                if ("$(Get-Prop $m 'name')" -ne $ModelName -or "$(Get-Prop $m 'version')" -ne $ModelVersion) { $problems.Add("modelo inesperado: $(Get-Prop $m 'name') $(Get-Prop $m 'version')") }
                $sku = Get-Prop $a 'sku'
                if ("$(Get-Prop $sku 'name')" -notin @('GlobalStandard', 'DataZoneStandard')) { $problems.Add("tipo de despliegue no permitido: $(Get-Prop $sku 'name')") }
                $cap = 0; [void][int]::TryParse("$(Get-Prop $sku 'capacity')", [ref]$cap)
                if ($cap -lt 1 -or $cap -gt $MaxCapacity) { $problems.Add("capacidad fuera de 1-${MaxCapacity}: $cap") }
                if (($id -split '/')[-1] -ne $ModelDeployment) { $problems.Add("nombre de despliegue inesperado: $id") }
            }
            'Microsoft.Authorization/roleAssignments' { $assignments.Add($c) }
        }
    }
    foreach ($c in $assignments) {
        $id = "$(Get-Prop $c 'resourceId')"
        $p = Get-Prop (Get-ChangePayload $c) 'properties'
        if (-not "$(Get-Prop $p 'roleDefinitionId')".EndsWith("/$OpenAIUserRoleId", [System.StringComparison]::OrdinalIgnoreCase)) { $problems.Add("rol no autorizado: $(Get-Prop $p 'roleDefinitionId')") }
        if (-not $accountId -or -not $id.StartsWith("$accountId/providers/Microsoft.Authorization/roleAssignments/", [System.StringComparison]::OrdinalIgnoreCase)) { $problems.Add("asignacion fuera de la cuenta de Azure OpenAI: $id") }
        $principal = "$(Get-Prop $p 'principalId')"
        if ($principal -and $RuntimePrincipalId -and $principal -ne $RuntimePrincipalId -and $principal -notlike '*reference(*') { $problems.Add("asignacion a otra identidad: $principal") }
        if ("$(Get-Prop $p 'principalType')" -notin @('', 'ServicePrincipal')) { $problems.Add('la asignacion no es a una identidad de servicio') }
    }
    foreach ($t in $AllowedTypes) { if ([int]$count[$t] -ne 1) { $problems.Add("se esperaba 1 recurso $t y hay $([int]$count[$t])") } }
    return ,$problems.ToArray()
}

function New-SelfTestCase([string]$Rg, [string]$Acc, $AccountProps, $DeploymentSku, [string]$Role, [string]$AssignScope, [string]$Extra) {
    $changes = @(
        @{ changeType = 'Create'; resourceId = $Acc; after = @{ type = 'Microsoft.CognitiveServices/accounts'; location = 'centralus'; kind = 'OpenAI'; sku = @{ name = 'S0' }; properties = $AccountProps } },
        @{ changeType = 'Create'; resourceId = "$Acc/deployments/gpt-41-mini"; after = @{ type = 'Microsoft.CognitiveServices/accounts/deployments'; sku = $DeploymentSku; properties = @{ model = @{ format = 'OpenAI'; name = 'gpt-4.1-mini'; version = '2025-04-14' } } } },
        @{ changeType = 'Create'; resourceId = "$AssignScope/providers/Microsoft.Authorization/roleAssignments/g"; after = @{ type = 'Microsoft.Authorization/roleAssignments'; properties = @{ roleDefinitionId = "/subscriptions/s/providers/Microsoft.Authorization/roleDefinitions/$Role"; principalId = 'p1'; principalType = 'ServicePrincipal' } } }
    )
    if ($Extra) { $changes += @{ changeType = $Extra; resourceId = "$Rg/providers/Microsoft.Storage/storageAccounts/x"; after = @{ type = 'Microsoft.Storage/storageAccounts' } } }
    return (ConvertTo-Json -InputObject @{ changes = $changes } -Depth 20 | ConvertFrom-Json)
}

function Invoke-SelfTest {
    $rg = '/subscriptions/s/resourceGroups/rg'
    $acc = "$rg/providers/Microsoft.CognitiveServices/accounts/oai-mpa-dev-x"
    $good = @{ customSubDomainName = 'oai-mpa-dev-x'; disableLocalAuth = $true; publicNetworkAccess = 'Enabled' }
    $sku = @{ name = 'GlobalStandard'; capacity = 10 }
    $cases = @(
        @('conforme', (New-SelfTestCase $rg $acc $good $sku $OpenAIUserRoleId $acc ''), 0),
        @('claves habilitadas', (New-SelfTestCase $rg $acc @{ customSubDomainName = 'x'; disableLocalAuth = $false } $sku $OpenAIUserRoleId $acc ''), 1),
        @('sin subdominio', (New-SelfTestCase $rg $acc @{ disableLocalAuth = $true } $sku $OpenAIUserRoleId $acc ''), 1),
        @('rol Contributor', (New-SelfTestCase $rg $acc $good $sku 'b24988ac-6180-42a0-ab88-20f7382dd24c' $acc ''), 1),
        @('asignacion en el grupo', (New-SelfTestCase $rg $acc $good $sku $OpenAIUserRoleId $rg ''), 1),
        @('capacidad 500', (New-SelfTestCase $rg $acc $good @{ name = 'GlobalStandard'; capacity = 500 } $OpenAIUserRoleId $acc ''), 1),
        @('aprovisionado', (New-SelfTestCase $rg $acc $good @{ name = 'ProvisionedManaged'; capacity = 10 } $OpenAIUserRoleId $acc ''), 1),
        @('recurso ajeno', (New-SelfTestCase $rg $acc $good $sku $OpenAIUserRoleId $acc 'Create'), 1),
        @('borrado', (New-SelfTestCase $rg $acc $good $sku $OpenAIUserRoleId $acc 'Delete'), 1)
    )
    $failed = 0
    foreach ($case in $cases) {
        $problems = Test-U13WhatIf $case[1] $rg 'p1'
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
    if ("$($account.tenantId)" -ne $ExpectedTenant) { Stop-U13 'la sesion no es del tenant de U10' }
    $rg = Invoke-Az @('group', 'show', '--name', $ResourceGroup, '--output', 'json') -What 'az group show'
    if ("$($rg.location)" -ne $Location) { Stop-U13 "el grupo no esta en $Location" }
    $identity = Invoke-Az @('identity', 'show', '--name', $RuntimeIdentityName, '--resource-group', $ResourceGroup, '--output', 'json') -What 'identidad de ejecucion de U12'
    return @{ rgId = "$($rg.id)"; principalId = "$($identity.principalId)"; clientId = "$($identity.clientId)" }
}

function Check([bool]$Ok, [string]$Text) {
    if ($Ok) { Write-Host "  OK     $Text" } else { $script:Failed++; Write-Host "  FALLO  $Text" -ForegroundColor Red }
}

function Get-U13Outputs {
    $out = Invoke-Az @('deployment', 'group', 'show', '--resource-group', $ResourceGroup, '--name', $DeploymentName, '--query', 'properties.outputs', '--output', 'json') -What 'salidas de u13-dev'
    $name = "$(Get-Prop (Get-Prop $out 'accountName') 'value')"
    if ($name -notlike 'oai-mpa-dev-*') { Stop-U13 "cuenta inesperada: $name" }
    return @{ name = $name; endpoint = "$(Get-Prop (Get-Prop $out 'endpoint') 'value')" }
}

$script:Failed = 0
switch ($Stage) {
    'Preflight' {
        Step '1. Sesion, grupo e identidad de ejecucion'
        $ctx = Get-Context
        Write-Host "  OK     grupo $ResourceGroup en $Location; identidad $RuntimeIdentityName"
        Step '2. Proveedor y catalogo'
        $state = "$(Invoke-Az @('provider', 'show', '--namespace', 'Microsoft.CognitiveServices', '--query', 'registrationState', '--output', 'tsv') -Raw)".Trim()
        if ($state -ne 'Registered') { Stop-U13 "Microsoft.CognitiveServices esta $state" }
        Write-Host '  OK     Microsoft.CognitiveServices Registered'
        $models = To-List (Invoke-Az @('cognitiveservices', 'model', 'list', '--location', $Location, '--output', 'json') -What 'catalogo de modelos')
        $match = @($models | Where-Object { "$($_.model.name)" -eq $ModelName -and "$($_.model.version)" -eq $ModelVersion -and @((To-List $_.model.skus) | Where-Object { "$($_.name)" -eq $DeploymentSku }).Count -gt 0 })
        if (-not $match.Count) { Stop-U13 "$ModelName $ModelVersion no esta en $DeploymentSku en $Location" }
        $retire = "$($match[0].model.deprecation.inference)"
        $retireDate = [datetime]::MinValue
        if (-not [datetime]::TryParse($retire, [ref]$retireDate) -or $retireDate -lt (Get-Date).AddDays(30)) { Stop-U13 "el modelo se retira el $retire (menos de 30 dias o fecha desconocida)" }
        Write-Host "  OK     $ModelName $ModelVersion en $DeploymentSku; retirada de inferencia $retire"
        Step '3. Cuota'
        $usage = To-List (Invoke-Az @('cognitiveservices', 'usage', 'list', '--location', $Location, '--output', 'json') -What 'cuota')
        $q = @($usage | Where-Object { "$($_.name.value)" -eq $QuotaName })
        if (-not $q.Count) { Stop-U13 "no hay cuota $QuotaName" }
        $free = [double]$q[0].limit - [double]$q[0].currentValue
        if ($free -lt $Capacity) { Stop-U13 "cuota libre de $QuotaName = $free (< $Capacity)" }
        Write-Host "  OK     $QuotaName libre $free (se usan $Capacity)"
        $accounts = To-List (Invoke-Az @('cognitiveservices', 'account', 'list', '--resource-group', $ResourceGroup, '--output', 'json') -What 'cuentas existentes')
        Write-Host "  INFO   cuentas de Cognitive Services en el grupo: $($accounts.Count)"
        Write-Host ''
        Write-Host 'PREFLIGHT OK' -ForegroundColor Green
    }
    'Deploy' {
        $ctx = Get-Context
        Step 'validate'
        Invoke-Az @('deployment', 'group', 'validate', '--resource-group', $ResourceGroup, '--name', $DeploymentName, '--template-file', $Template, '--parameters', $Parameters, '--output', 'none') -Raw -What 'validate' | Out-Null
        Step 'what-if'
        $whatIf = Invoke-Az @('deployment', 'group', 'what-if', '--resource-group', $ResourceGroup, '--name', $DeploymentName, '--template-file', $Template, '--parameters', $Parameters, '--no-pretty-print', '--output', 'json') -What 'what-if'
        foreach ($c in (To-List (Get-Prop $whatIf 'changes'))) { Write-Host "  $($c.changeType)  $($c.resourceId)" }
        $problems = Test-U13WhatIf $whatIf $ctx.rgId $ctx.principalId
        if ($problems.Count) { foreach ($p in $problems) { Write-Host "  PROBLEMA $p" -ForegroundColor Red }; Stop-U13 'el what-if no es el esperado' }
        Write-Host '  what-if conforme: una cuenta OpenAI sin claves, un despliegue y el rol de la identidad de ejecucion sobre la cuenta'
        Confirm-Or-Stop 'OPENAI' 'crear la cuenta de Azure OpenAI y el despliegue'
        Invoke-Az @('deployment', 'group', 'create', '--resource-group', $ResourceGroup, '--name', $DeploymentName, '--template-file', $Template, '--parameters', $Parameters, '--output', 'none') -Raw -What 'create' | Out-Null
        Write-Host 'Desplegado. Siguiente: -Stage Verify.' -ForegroundColor Green
    }
    'Verify' {
        $ctx = Get-Context
        $o = Get-U13Outputs
        $acc = Invoke-Az @('cognitiveservices', 'account', 'show', '--name', $o.name, '--resource-group', $ResourceGroup, '--output', 'json') -What 'cuenta'
        Check ("$($acc.kind)" -eq 'OpenAI' -and "$($acc.sku.name)" -eq 'S0') 'cuenta OpenAI S0'
        Check ($acc.properties.disableLocalAuth -eq $true) 'sin claves (disableLocalAuth)'
        Check ("$($acc.location)" -eq $Location) "region $Location"
        Check ("$($acc.properties.provisioningState)" -eq 'Succeeded') 'cuenta Succeeded'
        $deps = To-List (Invoke-Az @('cognitiveservices', 'account', 'deployment', 'list', '--name', $o.name, '--resource-group', $ResourceGroup, '--output', 'json') -What 'despliegues')
        Check ($deps.Count -eq 1) 'un unico despliegue'
        $d = $deps | Select-Object -First 1
        Check ("$($d.name)" -eq $ModelDeployment -and "$($d.properties.model.name)" -eq $ModelName -and "$($d.properties.model.version)" -eq $ModelVersion) "despliegue $ModelDeployment = $ModelName $ModelVersion"
        Check ("$($d.sku.name)" -eq $DeploymentSku -and [int]$d.sku.capacity -le $MaxCapacity) "$DeploymentSku, capacidad $($d.sku.capacity)"
        Check ("$($d.properties.provisioningState)" -eq 'Succeeded') 'despliegue Succeeded'
        $roles = To-List (Invoke-Az @('role', 'assignment', 'list', '--scope', "$($acc.id)", '--output', 'json') -What 'roles de la cuenta')
        $own = @($roles | Where-Object { "$($_.scope)" -eq "$($acc.id)" })
        Check ($own.Count -eq 1 -and "$($own[0].principalId)" -eq $ctx.principalId -and "$($own[0].roleDefinitionId)".EndsWith("/$OpenAIUserRoleId")) 'solo id-mpa-dev-runtime con Cognitive Services OpenAI User sobre la cuenta'
        $evidence = [ordered]@{ date = (Get-Date).ToUniversalTime().ToString('o'); accountName = $o.name; accountId = "$($acc.id)"; endpoint = $o.endpoint; deployment = "$($d.name)"; model = "$ModelName $ModelVersion"; sku = "$($d.sku.name)"; capacity = $d.sku.capacity; disableLocalAuth = $acc.properties.disableLocalAuth; runtimeClientId = $ctx.clientId; checksFailed = $script:Failed }
        New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null
        Set-Content -Path (Join-Path $EvidenceDir 'u13-evidence.json') -Value (ConvertTo-Json $evidence -Depth 5) -Encoding ASCII
        if ($script:Failed) { Stop-U13 "$($script:Failed) comprobaciones fallidas" }
        Write-Host ''
        Write-Host 'U13: Azure OpenAI verificado.' -ForegroundColor Green
        Write-Host 'Siguiente: genaiEnabled = true en infra/azure/u12/dev.bicepparam (commit), Deploy dev y deploy-u12.ps1 -Stage Apps -ImageTag <sha>.'
    }
    'Remove' {
        $ctx = Get-Context
        $o = Get-U13Outputs
        Write-Host "Se borraran: la asignacion de rol, el despliegue $ModelDeployment y la cuenta $($o.name) (y se purgara)."
        Write-Host 'Antes, pon genaiEnabled = false en infra/azure/u12/dev.bicepparam y redespliega Apps: la api vuelve a la plantilla.'
        Confirm-Or-Stop 'BORRAR' "borrar la cuenta $($o.name)"
        $acc = Invoke-Az @('cognitiveservices', 'account', 'show', '--name', $o.name, '--resource-group', $ResourceGroup, '--output', 'json') -What 'cuenta'
        Invoke-Az @('role', 'assignment', 'delete', '--assignee', $ctx.principalId, '--role', $OpenAIUserRoleId, '--scope', "$($acc.id)") -Raw -What 'borrar el rol' | Out-Null
        Invoke-Az @('cognitiveservices', 'account', 'deployment', 'delete', '--name', $o.name, '--resource-group', $ResourceGroup, '--deployment-name', $ModelDeployment) -Raw -What 'borrar el despliegue' | Out-Null
        Invoke-Az @('cognitiveservices', 'account', 'delete', '--name', $o.name, '--resource-group', $ResourceGroup) -Raw -What 'borrar la cuenta' | Out-Null
        Invoke-Az @('cognitiveservices', 'account', 'purge', '--name', $o.name, '--resource-group', $ResourceGroup, '--location', $Location) -Raw -What 'purgar la cuenta' | Out-Null
        Write-Host 'U13 desmontada.' -ForegroundColor Green
    }
}
