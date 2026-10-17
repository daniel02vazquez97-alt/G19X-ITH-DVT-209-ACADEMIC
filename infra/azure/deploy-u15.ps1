# U15 (DT-094): Azure AI Search on the Free service the owner created by hand (motor-predictivo-search-dev, 2026-10-16),
# embeddings text-embedding-3-small on the U13 Azure OpenAI account and the synthetic corpus only. Run by the project
# owner from the repository root with an Azure CLI session already signed in:
#
#     powershell -ExecutionPolicy Bypass -File infra\azure\deploy-u15.ps1 -PreflightOnly
#     powershell -ExecutionPolicy Bypass -File infra\azure\deploy-u15.ps1 -Stage <stage> [-Yes]
#
# Stages (infra/azure/u15/README.md):
#   -PreflightOnly (= -Stage Preflight, the default): STRICTLY read-only (allow list). Session, group, the Search service
#              (Free, running, accepts Entra ID), the embeddings deployment, your data roles, the runtime identity and,
#              with Python, the index status (GET only). PREFLIGHT OK or PREFLIGHT BLOQUEADO.
#   WhatIf     validate + what-if of infra/azure/u15/main.bicep against the real service: shows the drift, never creates.
#   Index      creates or updates the index u15-demo-documents from infra/azure/u15/index.json (INDICE).
#   Load       vectorizes knowledge/search_corpus/ (synthetic) with text-embedding-3-small and uploads it (CARGAR).
#   Roles      Search Index Data Reader to id-mpa-dev-runtime on the service only (ROL); idempotent. Needs the
#              deploy-u12.ps1 of this same change, whose Verify accepts that role.
#   Verify     service, embeddings, runtime role (exactly one reader, nothing else on the service) and, with YOUR
#              identity, document count, fixed evaluation set and group filter; tmp/u15-evidence/u15-evidence.json.
#   -SelfTest  offline checks of the guards (no Azure call).
# It never reads, asks for, stores or prints a key or a connection string; the Entra ID tokens of your session are
# requested by search_setup.py and stay in its memory. It does not touch the API, Container Apps or the settings of the
# service (API keys stay enabled until the API is verified with Entra ID). ASCII only.

[CmdletBinding()]
param(
    [ValidateSet('Preflight', 'WhatIf', 'Index', 'Load', 'Roles', 'Verify')]
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
$script:ReadOnly = ($Stage -in @('Preflight', 'WhatIf') -and -not $SelfTest)

$ResourceGroup = 'rg-motor-predictivo-dev'
$Location = 'centralus'
$ExpectedTenant = '6ce4b1ba-ae4f-4887-bd6b-acb3c72039ad'
$SearchName = 'motor-predictivo-search-dev'
$ExpectedSku = 'free'
$OpenAIPattern = '^oai-mpa-dev-[a-z0-9]+$'
$EmbeddingDeployment = 'text-embedding-3-small'
$RuntimeIdentity = 'id-mpa-dev-runtime'
$Template = 'infra/azure/u15/main.bicep'
$Parameters = 'infra/azure/u15/dev.bicepparam'
$DeploymentName = 'u15-dev'
$Setup = 'infra/azure/u15/search_setup.py'
$EvidenceDir = 'tmp/u15-evidence'
# Built-in role ids (Microsoft Learn, "Azure built-in roles"); the three roles of the owner were confirmed by the
# assignments created on 2026-10-17.
$SearchReaderRoleId = '1407120a-92aa-4202-b7e9-c0e197c71c8f'
$OwnerRoles = @(@('Search Service Contributor', 'search'), @('Search Index Data Contributor', 'search'), @('Cognitive Services OpenAI User', 'openai'))

function Step([string]$Text) { Write-Host ''; Write-Host "== $Text" -ForegroundColor Cyan }
function Stop-U15([string]$Text) {
    Write-Host ''; Write-Host "DETENIDO: $Text" -ForegroundColor Red
    if ($Stage -eq 'Preflight' -and -not $SelfTest) { Write-Host 'PREFLIGHT BLOQUEADO' -ForegroundColor Red }
    exit 1
}
function Get-Prop($Object, [string]$Name) {
    if ($null -eq $Object) { return $null }
    if ($Object -is [System.Collections.IDictionary]) { return $Object[$Name] }
    $p = $Object.PSObject.Properties[$Name]
    if ($null -eq $p) { return $null }
    return $p.Value
}
# az search service show returns the properties flat; ARM shapes nest them under "properties". Both are accepted.
function Get-SvcProp($Service, [string]$Name) {
    $v = Get-Prop $Service $Name
    if ($null -eq $v) { $v = Get-Prop (Get-Prop $Service 'properties') $Name }
    return $v
}
function To-List($Value) {
    $items = New-Object System.Collections.Generic.List[object]
    if ($null -eq $Value) { return ,$items.ToArray() }
    if ($Value -is [System.Array]) { foreach ($v in $Value) { if ($null -ne $v) { $items.Add($v) } } } else { $items.Add($Value) }
    return ,$items.ToArray()
}

# Read-only allow list for Preflight and WhatIf: show/list, validate and what-if only.
function Test-ReadOnlyAz([string[]]$Arguments) {
    $joined = (@($Arguments | Where-Object { $_ -notlike '-*' } | Select-Object -First 5) -join ' ')
    foreach ($ok in @('account show', 'group show', 'search service show', 'resource list', 'cognitiveservices account show',
            'cognitiveservices account deployment list', 'role assignment list', 'ad signed-in-user show', 'identity show',
            'deployment group validate', 'deployment group what-if', 'version')) {
        if ($joined -eq $ok -or $joined.StartsWith($ok + ' ')) { return $true }
    }
    return $false
}

function Invoke-Az {
    param([string[]]$Arguments, [switch]$Raw, [string]$What = 'az', [switch]$AllowFailure)
    foreach ($word in @('keys', 'admin-key', 'query-key', 'list-keys', 'get-access-token', 'show-connection-string')) {
        if ($Arguments -contains $word) { Stop-U15 'U15 nunca lee claves, tokens ni cadenas de conexion desde este script' }
    }
    if ($script:ReadOnly -and -not (Test-ReadOnlyAz $Arguments)) { Stop-U15 ("comando no permitido en modo solo lectura: az " + (($Arguments | Select-Object -First 3) -join ' ')) }
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $output = & az @Arguments 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = $previous
    if ($code -ne 0) {
        if ($AllowFailure) { return $null }
        Write-Host (($output | ForEach-Object { "$_" }) -join "`n")
        Stop-U15 "$What fallo (codigo $code)"
    }
    $json = ($output | Where-Object { $_ -isnot [System.Management.Automation.ErrorRecord] } | ForEach-Object { "$_" }) -join "`n"
    if ($Raw) { return $json }
    if ([string]::IsNullOrWhiteSpace($json)) { return $null }
    return (ConvertFrom-Json -InputObject $json)
}

function Confirm-Or-Stop([string]$Word, [string]$Prompt) {
    if ($Yes) { return }
    $answer = Read-Host "Escribe $Word para $Prompt"
    if ($answer -cne $Word) { Stop-U15 'cancelado por el responsable' }
}

function Check([bool]$Ok, [string]$Text) {
    if ($Ok) { Write-Host "  OK     $Text" } else { $script:Failed++; Write-Host "  FALLO  $Text" -ForegroundColor Red }
}

# ---- Guards (pure; -SelfTest) ----------------------------------------------------------------------------------------

# Free (no continuous charge), running, in centralus, public endpoint and Entra ID accepted (aadOrApiKey or keys off).
function Test-SearchService($Service) {
    $problems = New-Object System.Collections.Generic.List[string]
    if ($null -eq $Service) { $problems.Add("no existe el servicio $SearchName"); return ,$problems.ToArray() }
    $sku = "$(Get-Prop (Get-Prop $Service 'sku') 'name')"
    if ($sku -ne $ExpectedSku) { $problems.Add("SKU $sku; se esperaba $ExpectedSku (sin cargo continuo, DT-094)") }
    if ("$(Get-SvcProp $Service 'status')" -ne 'running') { $problems.Add("estado $(Get-SvcProp $Service 'status'), no running") }
    if ("$(Get-SvcProp $Service 'provisioningState')" -ne 'Succeeded') { $problems.Add("aprovisionamiento $(Get-SvcProp $Service 'provisioningState')") }
    $loc = ("$(Get-Prop $Service 'location')" -replace ' ', '').ToLower()
    if ($loc -ne $Location) { $problems.Add("region $loc, no $Location") }
    if ("$(Get-SvcProp $Service 'publicNetworkAccess')" -notin @('Enabled', 'enabled')) { $problems.Add('acceso publico deshabilitado: Container Apps no llegaria sin endpoint privado') }
    $keysOff = ((Get-SvcProp $Service 'disableLocalAuth') -eq $true)
    if (-not $keysOff -and $null -eq (Get-Prop (Get-SvcProp $Service 'authOptions') 'aadOrApiKey')) {
        $problems.Add('el servicio no acepta Entra ID (solo claves): en el portal, Configuracion > Claves > Ambos')
    }
    return ,$problems.ToArray()
}

function Get-AuthMode($Service) {
    if ((Get-SvcProp $Service 'disableLocalAuth') -eq $true) { return 'solo Entra ID (claves desactivadas)' }
    return 'Entra ID y claves de API'
}

function Test-EmbeddingDeployment($Deployments) {
    $problems = New-Object System.Collections.Generic.List[string]
    $match = @(foreach ($d in (To-List $Deployments)) { if ("$(Get-Prop $d 'name')" -eq $EmbeddingDeployment) { $d } })
    if ($match.Count -ne 1) { $problems.Add("falta el despliegue $EmbeddingDeployment en la cuenta de U13"); return ,$problems.ToArray() }
    $p = Get-Prop $match[0] 'properties'
    if ("$(Get-Prop (Get-Prop $p 'model') 'name')" -ne 'text-embedding-3-small') { $problems.Add("$EmbeddingDeployment no usa el modelo text-embedding-3-small") }
    if ("$(Get-Prop $p 'provisioningState')" -ne 'Succeeded') { $problems.Add("$EmbeddingDeployment en estado $(Get-Prop $p 'provisioningState')") }
    return ,$problems.ToArray()
}

# True when one assignment of $Name has $TargetId as its scope or as a descendant of its scope (inherited).
function Test-HasRole($Roles, [string]$Name, [string]$TargetId) {
    foreach ($r in (To-List $Roles)) {
        $scope = "$(Get-Prop $r 'scope')".TrimEnd('/')
        if ("$(Get-Prop $r 'roleDefinitionName')" -ne $Name -or -not $scope) { continue }
        if ($TargetId.Equals($scope, [System.StringComparison]::OrdinalIgnoreCase) -or $TargetId.StartsWith($scope + '/', [System.StringComparison]::OrdinalIgnoreCase)) { return $true }
    }
    return $false
}

# Data roles your session needs for Index (Search Service Contributor), Load (Search Index Data Contributor and
# Cognitive Services OpenAI User) and Verify. Owner is not enough: it has no data actions.
function Get-MissingOwnerRoles($Roles, [string]$SearchId, [string]$OpenAIId) {
    $missing = New-Object System.Collections.Generic.List[string]
    foreach ($pair in $OwnerRoles) {
        $target = if ($pair[1] -eq 'search') { $SearchId } else { $OpenAIId }
        if (-not (Test-HasRole $Roles $pair[0] $target)) { $missing.Add("$($pair[0]) sobre $(($target -split '/')[-1])") }
    }
    return ,$missing.ToArray()
}

# Runtime identity on Search: at most (or, with $Require, exactly) one Search Index Data Reader on the service itself;
# no other role on the service or below it, and no Search role on a wider scope.
function Test-RuntimeSearchRoles($Roles, [string]$SearchId, [bool]$Require) {
    $problems = New-Object System.Collections.Generic.List[string]
    $readers = 0
    foreach ($r in (To-List $Roles)) {
        $name = "$(Get-Prop $r 'roleDefinitionName')"
        $scope = "$(Get-Prop $r 'scope')".TrimEnd('/')
        $onService = $scope.Equals($SearchId, [System.StringComparison]::OrdinalIgnoreCase)
        $below = $scope.StartsWith($SearchId + '/', [System.StringComparison]::OrdinalIgnoreCase)
        $above = $scope -and $SearchId.StartsWith($scope + '/', [System.StringComparison]::OrdinalIgnoreCase)
        if ($onService -and $name -eq 'Search Index Data Reader') { $readers++ }
        elseif ($onService -or $below) { $problems.Add("rol no permitido sobre Search: $name en $scope") }
        elseif ($above -and $name -like 'Search *') { $problems.Add("rol de Search demasiado amplio: $name en $scope") }
    }
    if ($readers -gt 1) { $problems.Add("se esperaba como mucho 1 Search Index Data Reader y hay $readers") }
    if ($Require -and $readers -ne 1) { $problems.Add("$RuntimeIdentity sin Search Index Data Reader sobre el servicio (-Stage Roles)") }
    return ,$problems.ToArray()
}

function New-SelfTestService($Sku, $Status, $Auth, $KeysOff, $Public = 'Enabled', [switch]$Nested) {
    $p = [ordered]@{ status = $Status; provisioningState = 'Succeeded'; publicNetworkAccess = $Public; disableLocalAuth = $KeysOff; authOptions = $Auth }
    $o = [ordered]@{ name = 'motor-predictivo-search-dev'; location = 'Central US'; sku = @{ name = $Sku } }
    if ($Nested) { $o.properties = $p } else { foreach ($k in $p.Keys) { $o[$k] = $p[$k] } }
    return (ConvertTo-Json -InputObject $o -Depth 10 | ConvertFrom-Json)
}
function New-SelfTestRole([string]$Name, [string]$Scope) { return @{ roleDefinitionName = $Name; scope = $Scope } }
function New-SelfTestDeployment([string]$Name, [string]$Model, [string]$State) { return @{ name = $Name; properties = @{ model = @{ name = $Model }; provisioningState = $State } } }

function Invoke-SelfTest {
    $rg = '/subscriptions/s/resourceGroups/rg'
    $sid = "$rg/providers/Microsoft.Search/searchServices/motor-predictivo-search-dev"
    $oid = "$rg/providers/Microsoft.CognitiveServices/accounts/oai-mpa-dev-x"
    $both = @{ aadOrApiKey = @{ aadAuthFailureMode = 'http401WithBearerChallenge' } }
    $chat = New-SelfTestDeployment 'gpt-41-mini' 'gpt-4.1-mini' 'Succeeded'
    $emb = New-SelfTestDeployment 'text-embedding-3-small' 'text-embedding-3-small' 'Succeeded'
    $all = @((New-SelfTestRole 'Search Service Contributor' $sid), (New-SelfTestRole 'Search Index Data Contributor' $sid), (New-SelfTestRole 'Cognitive Services OpenAI User' $oid))
    $reader = New-SelfTestRole 'Search Index Data Reader' $sid
    $cases = @(
        @('servicio Free, Entra ID y claves (estado real del 2026-10-16)', ((Test-SearchService (New-SelfTestService 'free' 'running' $both $false)).Count -eq 0)),
        @('servicio Free con forma ARM (properties)', ((Test-SearchService (New-SelfTestService 'free' 'running' $both $false -Nested)).Count -eq 0)),
        @('servicio Free solo Entra ID (claves desactivadas)', ((Test-SearchService (New-SelfTestService 'free' 'running' $null $true)).Count -eq 0)),
        @('servicio Basic -> rechazado (cargo continuo)', ((Test-SearchService (New-SelfTestService 'basic' 'running' $both $false)).Count -gt 0)),
        @('servicio solo con claves -> rechazado', ((Test-SearchService (New-SelfTestService 'free' 'running' @{ apiKeyOnly = @{} } $false)).Count -gt 0)),
        @('servicio detenido -> rechazado', ((Test-SearchService (New-SelfTestService 'free' 'stopped' $both $false)).Count -gt 0)),
        @('servicio sin acceso publico -> rechazado', ((Test-SearchService (New-SelfTestService 'free' 'running' $both $false 'Disabled')).Count -gt 0)),
        @('servicio inexistente -> rechazado', ((Test-SearchService $null).Count -gt 0)),
        @('embeddings desplegados', ((Test-EmbeddingDeployment @($chat, $emb)).Count -eq 0)),
        @('sin despliegue de embeddings -> rechazado', ((Test-EmbeddingDeployment @($chat)).Count -gt 0)),
        @('embeddings fallidos -> rechazado', ((Test-EmbeddingDeployment @((New-SelfTestDeployment 'text-embedding-3-small' 'text-embedding-3-small' 'Failed'))).Count -gt 0)),
        @('tus tres roles de datos -> completos', ((Get-MissingOwnerRoles $all $sid $oid).Count -eq 0)),
        @('rol heredado del grupo -> cuenta', ((Get-MissingOwnerRoles @($all[0], (New-SelfTestRole 'Search Index Data Contributor' $rg), $all[2]) $sid $oid).Count -eq 0)),
        @('solo Owner -> faltan los tres', ((Get-MissingOwnerRoles @((New-SelfTestRole 'Owner' '/subscriptions/s')) $sid $oid).Count -eq 3)),
        @('rol sobre otro servicio -> no cuenta', ((Get-MissingOwnerRoles @((New-SelfTestRole 'Search Service Contributor' ($sid + '2')), $all[1], $all[2]) $sid $oid).Count -eq 1)),
        @('ejecucion sin rol antes de Roles -> conforme', ((Test-RuntimeSearchRoles @((New-SelfTestRole 'AcrPull' "$rg/providers/Microsoft.ContainerRegistry/registries/acr")) $sid $false).Count -eq 0)),
        @('ejecucion sin rol en Verify -> rechazado', ((Test-RuntimeSearchRoles @() $sid $true).Count -gt 0)),
        @('ejecucion con lector sobre el servicio -> conforme', ((Test-RuntimeSearchRoles @($reader) $sid $true).Count -eq 0)),
        @('ejecucion con lector sobre el grupo -> rechazado', ((Test-RuntimeSearchRoles @((New-SelfTestRole 'Search Index Data Reader' $rg)) $sid $false).Count -gt 0)),
        @('ejecucion con contribuidor sobre el servicio -> rechazado', ((Test-RuntimeSearchRoles @((New-SelfTestRole 'Search Index Data Contributor' $sid)) $sid $false).Count -gt 0)),
        @('ejecucion con dos lectores -> rechazado', ((Test-RuntimeSearchRoles @($reader, $reader) $sid $false).Count -gt 0)),
        @('solo lectura: search service show', (Test-ReadOnlyAz @('search', 'service', 'show', '--name', 'x'))),
        @('solo lectura: what-if', (Test-ReadOnlyAz @('deployment', 'group', 'what-if', '--resource-group', 'rg'))),
        @('solo lectura: search service update -> rechazado', (-not (Test-ReadOnlyAz @('search', 'service', 'update', '--name', 'x')))),
        @('solo lectura: role assignment create -> rechazado', (-not (Test-ReadOnlyAz @('role', 'assignment', 'create', '--role', 'x')))),
        @('solo lectura: deployment group create -> rechazado', (-not (Test-ReadOnlyAz @('deployment', 'group', 'create', '--name', 'x'))))
    )
    $failed = 0
    foreach ($case in $cases) {
        if ($case[1]) { Write-Host "  OK    $($case[0])" } else { $failed++; Write-Host "  FALLO $($case[0])" -ForegroundColor Red }
    }
    if ($failed) { Write-Host "SELFTEST: $failed fallos" -ForegroundColor Red; exit 1 }
    Write-Host "SELFTEST OK ($($cases.Count) casos)" -ForegroundColor Green
    exit 0
}

if ($SelfTest) { Invoke-SelfTest }

# ---- Azure ----------------------------------------------------------------------------------------------------------

function Get-Context {
    $account = Invoke-Az @('account', 'show', '--output', 'json') -What 'az account show'
    if ("$($account.tenantId)" -ne $ExpectedTenant) { Stop-U15 'la sesion no es del tenant de U10' }
    $rg = Invoke-Az @('group', 'show', '--name', $ResourceGroup, '--output', 'json') -What 'az group show'
    if ("$($rg.location)" -ne $Location) { Stop-U15 "el grupo no esta en $Location" }
    return @{ rgId = "$($rg.id)" }
}

function Get-CheckedService {
    $svc = Invoke-Az @('search', 'service', 'show', '--name', $SearchName, '--resource-group', $ResourceGroup, '--output', 'json') -What 'servicio de Search' -AllowFailure
    $problems = Test-SearchService $svc
    if ($problems.Count) { foreach ($p in $problems) { Write-Host "  PROBLEMA $p" -ForegroundColor Red }; Stop-U15 'el servicio de Search no es el esperado' }
    $script:SearchEndpoint = "$(Get-SvcProp $svc 'endpoint')".TrimEnd('/')
    if (-not $script:SearchEndpoint) { $script:SearchEndpoint = "https://$SearchName.search.windows.net" }
    return $svc
}

function Get-OpenAIAccount {
    $all = To-List (Invoke-Az @('resource', 'list', '--resource-group', $ResourceGroup, '--resource-type', 'Microsoft.CognitiveServices/accounts', '--output', 'json') -What 'cuentas de Azure OpenAI')
    $accounts = @(foreach ($a in $all) { if ("$($a.name)" -match $OpenAIPattern) { $a } })
    if ($accounts.Count -ne 1) { Stop-U15 "se esperaba 1 cuenta oai-mpa-dev-* (U13) y hay $($accounts.Count)" }
    $account = Invoke-Az @('cognitiveservices', 'account', 'show', '--name', $accounts[0].name, '--resource-group', $ResourceGroup, '--output', 'json') -What 'cuenta de U13'
    $script:OpenAIEndpoint = "$($account.properties.endpoint)".TrimEnd('/')
    return $account
}

function Get-EmbeddingProblems($Account) {
    $deps = Invoke-Az @('cognitiveservices', 'account', 'deployment', 'list', '--name', $Account.name, '--resource-group', $ResourceGroup, '--output', 'json') -What 'despliegues de U13'
    return (Test-EmbeddingDeployment $deps)
}

function Assert-Embeddings($Account) {
    $problems = Get-EmbeddingProblems $Account
    if ($problems.Count) { foreach ($p in $problems) { Write-Host "  PROBLEMA $p" -ForegroundColor Red }; Stop-U15 'faltan los embeddings' }
}

function Assert-OwnerRoles([string]$SearchId, [string]$OpenAIId) {
    $me = "$(Invoke-Az @('ad', 'signed-in-user', 'show', '--query', 'id', '--output', 'tsv') -Raw -What 'tu usuario')".Trim()
    $roles = Invoke-Az @('role', 'assignment', 'list', '--assignee', $me, '--all', '--output', 'json') -What 'tus roles'
    $missing = Get-MissingOwnerRoles $roles $SearchId $OpenAIId
    if ($missing.Count) {
        foreach ($m in $missing) { Write-Host "  FALTA  $m" -ForegroundColor Red }
        Stop-U15 'faltan roles de datos de tu sesion (README de U15, seccion Roles); tardan unos minutos en aplicarse'
    }
    Write-Host '  OK     tus roles de datos: Search Service Contributor, Search Index Data Contributor y Cognitive Services OpenAI User'
}

function Get-RuntimeRoles {
    $rt = Invoke-Az @('identity', 'show', '--name', $RuntimeIdentity, '--resource-group', $ResourceGroup, '--output', 'json') -What 'identidad de ejecucion'
    $roles = Invoke-Az @('role', 'assignment', 'list', '--assignee', $rt.principalId, '--all', '--output', 'json') -What 'roles de ejecucion'
    return @{ principalId = "$($rt.principalId)"; roles = $roles }
}

function Find-Python {
    foreach ($c in @(@('py', '-3'), @('python'), @('python3'))) {
        $cmd = Get-Command $c[0] -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($null -eq $cmd) { continue }
        $extra = @($c | Select-Object -Skip 1)
        $ok = & $cmd.Source @extra -c 'import sys; print(int(sys.version_info >= (3, 10)))' 2>$null
        if ("$ok".Trim() -eq '1') { return @{ Exe = $cmd.Source; Args = $extra } }
    }
    return $null
}

# Python writes UTF-8 and the console reads UTF-8 while it runs, so accented queries are not garbled (2026-10-17, Windows
# PowerShell 5.1 showed them in the OEM code page). Both settings are restored afterwards.
function Invoke-Setup($Py, [string]$Command, [string[]]$Extra = @()) {
    $arguments = @($Py.Args) + @($Setup, $Command, '--search-endpoint', $script:SearchEndpoint) + @($Extra)
    $previousIo = $env:PYTHONIOENCODING
    $previousOut = $null
    try { $previousOut = [Console]::OutputEncoding; [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false) } catch { $previousOut = $null }
    $env:PYTHONIOENCODING = 'utf-8'
    try {
        & $Py.Exe @arguments | Out-Host
        $code = $LASTEXITCODE
    }
    finally {
        $env:PYTHONIOENCODING = $previousIo
        if ($null -ne $previousOut) { try { [Console]::OutputEncoding = $previousOut } catch { } }
    }
    return $code
}

function Get-PythonOrStop {
    $py = Find-Python
    if ($null -eq $py) { Stop-U15 'Python 3.10+ no encontrado (py -3, python o python3)' }
    return $py
}

$script:Failed = 0
$script:SearchEndpoint = ''
$script:OpenAIEndpoint = ''
switch ($Stage) {
    'Preflight' {
        Step '1. Sesion y grupo'
        $ctx = Get-Context
        Write-Host "  OK     grupo $ResourceGroup en $Location"
        Step '2. Servicio de Azure AI Search'
        $svc = Get-CheckedService
        Write-Host "  OK     ${SearchName}: SKU $ExpectedSku, running, $($script:SearchEndpoint)"
        Write-Host "  OK     autenticacion: $(Get-AuthMode $svc)"
        if ((Get-SvcProp $svc 'disableLocalAuth') -ne $true) { Write-Host '  AVISO  las claves de API siguen activas: desactivarlas cuando la API use Search con Entra ID (este script no lo hace)' -ForegroundColor Yellow }
        Step '3. Embeddings (cuenta de U13)'
        $oai = Get-OpenAIAccount
        Assert-Embeddings $oai
        Write-Host "  OK     $EmbeddingDeployment en $($oai.name)"
        Step '4. Tus roles de datos'
        Assert-OwnerRoles "$($svc.id)" "$($oai.id)"
        Step '5. Identidad de ejecucion'
        $rt = Get-RuntimeRoles
        $problems = Test-RuntimeSearchRoles $rt.roles "$($svc.id)" $false
        if ($problems.Count) { foreach ($p in $problems) { Write-Host "  PROBLEMA $p" -ForegroundColor Red }; Stop-U15 "roles inesperados de $RuntimeIdentity" }
        if ((Test-RuntimeSearchRoles $rt.roles "$($svc.id)" $true).Count) { Write-Host "  INFO   $RuntimeIdentity sin rol sobre Search todavia (lo asigna -Stage Roles)" }
        else { Write-Host "  OK     $RuntimeIdentity con Search Index Data Reader solo sobre el servicio" }
        Step '6. Indice (solo lectura)'
        $py = Find-Python
        if ($null -eq $py) { Write-Host '  AVISO  Python 3.10+ no encontrado: Index, Load y Verify lo necesitan' -ForegroundColor Yellow }
        elseif ((Invoke-Setup $py 'status') -ne 0) { Write-Host '  AVISO  no se pudo leer el indice (roles recien asignados: espera unos minutos)' -ForegroundColor Yellow }
        Write-Host ''
        Write-Host 'PREFLIGHT OK' -ForegroundColor Green
    }
    'WhatIf' {
        $ctx = Get-Context
        Step 'validate'
        Invoke-Az @('deployment', 'group', 'validate', '--resource-group', $ResourceGroup, '--name', $DeploymentName, '--template-file', $Template, '--parameters', $Parameters, '--output', 'none') -Raw -What 'validate' | Out-Null
        Step 'what-if (informativo: deriva entre la plantilla y el servicio real)'
        $whatIf = Invoke-Az @('deployment', 'group', 'what-if', '--resource-group', $ResourceGroup, '--name', $DeploymentName, '--template-file', $Template, '--parameters', $Parameters, '--no-pretty-print', '--output', 'json') -What 'what-if'
        foreach ($c in (To-List (Get-Prop $whatIf 'changes'))) {
            if ("$($c.changeType)" -eq 'Ignore') { continue }
            Write-Host "  $($c.changeType)  $($c.resourceId)"
            foreach ($d in (To-List (Get-Prop $c 'delta'))) { Write-Host "      $($d.propertyChangeType) $($d.path)" }
        }
        Write-Host ''
        Write-Host 'WhatIf: solo informativo; no se ha creado ni cambiado nada.' -ForegroundColor Green
    }
    'Index' {
        $ctx = Get-Context
        $svc = Get-CheckedService
        $oai = Get-OpenAIAccount
        Assert-OwnerRoles "$($svc.id)" "$($oai.id)"
        $py = Get-PythonOrStop
        Confirm-Or-Stop 'INDICE' "crear o actualizar el indice u15-demo-documents en $SearchName"
        if ((Invoke-Setup $py 'index') -ne 0) { Stop-U15 'no se pudo crear el indice' }
        Write-Host 'Indice listo. Siguiente: -Stage Load.' -ForegroundColor Green
    }
    'Load' {
        $ctx = Get-Context
        $svc = Get-CheckedService
        $oai = Get-OpenAIAccount
        Assert-Embeddings $oai
        Assert-OwnerRoles "$($svc.id)" "$($oai.id)"
        $py = Get-PythonOrStop
        Confirm-Or-Stop 'CARGAR' "vectorizar y cargar el corpus sintetico en $SearchName"
        if ((Invoke-Setup $py 'load' @('--openai-endpoint', $script:OpenAIEndpoint, '--embedding-deployment', $EmbeddingDeployment)) -ne 0) { Stop-U15 'no se pudo cargar el corpus' }
        Write-Host 'Corpus cargado. Siguiente: -Stage Roles.' -ForegroundColor Green
    }
    'Roles' {
        $ctx = Get-Context
        $svc = Get-CheckedService
        $rt = Get-RuntimeRoles
        $problems = Test-RuntimeSearchRoles $rt.roles "$($svc.id)" $false
        if ($problems.Count) { foreach ($p in $problems) { Write-Host "  PROBLEMA $p" -ForegroundColor Red }; Stop-U15 "roles inesperados de $RuntimeIdentity" }
        if ((Test-RuntimeSearchRoles $rt.roles "$($svc.id)" $true).Count -eq 0) {
            Write-Host "$RuntimeIdentity ya tiene Search Index Data Reader sobre el servicio; nada que hacer." -ForegroundColor Green
        }
        else {
            Write-Host "Se asignara Search Index Data Reader a $RuntimeIdentity solo sobre $SearchName (lectura de documentos; sin claves ni escritura)."
            Confirm-Or-Stop 'ROL' "asignar el rol de lectura a $RuntimeIdentity"
            Invoke-Az @('role', 'assignment', 'create', '--assignee-object-id', $rt.principalId, '--assignee-principal-type', 'ServicePrincipal', '--role', $SearchReaderRoleId, '--scope', "$($svc.id)", '--output', 'none') -Raw -What 'asignacion de rol' | Out-Null
            Write-Host 'Rol asignado. Comprueba U12 con deploy-u12.ps1 -Stage Verify (debe seguir en verde). Siguiente: -Stage Verify.' -ForegroundColor Green
        }
    }
    'Verify' {
        $ctx = Get-Context
        $svc = Get-CheckedService
        Check $true "servicio ${SearchName}: SKU $ExpectedSku, running, $(Get-AuthMode $svc)"
        $oai = Get-OpenAIAccount
        Check ((Get-EmbeddingProblems $oai).Count -eq 0) "$EmbeddingDeployment desplegado en $($oai.name)"
        $rt = Get-RuntimeRoles
        $rtProblems = Test-RuntimeSearchRoles $rt.roles "$($svc.id)" $true
        Check ($rtProblems.Count -eq 0) "${RuntimeIdentity}: exactamente 1 Search Index Data Reader sobre el servicio y nada mas sobre Search"
        foreach ($p in $rtProblems) { Write-Host "         $p" }
        $py = Get-PythonOrStop
        New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null
        $verifyFile = Join-Path $EvidenceDir 'u15-verify.json'
        $code = Invoke-Setup $py 'verify' @('--openai-endpoint', $script:OpenAIEndpoint, '--embedding-deployment', $EmbeddingDeployment, '--evidence', $verifyFile)
        Check ($code -eq 0) 'indice, corpus sintetico, embeddings y filtro de grupos (con TU identidad, no la de la API)'
        $evidence = [ordered]@{
            date = (Get-Date).ToUniversalTime().ToString('o'); service = "$($svc.id)"; sku = $ExpectedSku; authentication = (Get-AuthMode $svc)
            embeddingDeployment = $EmbeddingDeployment; openAIAccount = "$($oai.name)"; runtimeIdentity = $RuntimeIdentity
            runtimeRolesConforming = ($rtProblems.Count -eq 0); setupVerify = $verifyFile; checksFailed = $script:Failed
            apiWired = $false
        }
        Set-Content -Path (Join-Path $EvidenceDir 'u15-evidence.json') -Value (ConvertTo-Json $evidence) -Encoding ASCII
        if ($script:Failed) { Stop-U15 "$($script:Failed) comprobaciones fallidas" }
        Write-Host ''
        Write-Host 'U15: Search verificado con tu identidad. La API todavia no consulta Search (pendiente de conectar).' -ForegroundColor Green
    }
}
