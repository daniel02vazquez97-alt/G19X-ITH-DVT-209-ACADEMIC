# U11 (DT-099): reproducible configuration of the Microsoft Entra ID app registrations of `dev`, run by the
# project owner from the repository root with an Azure CLI session that is already signed in:
#
#     powershell -ExecutionPolicy Bypass -File infra\azure\deploy-u11.ps1
#
# Desired state: infra/azure/entra/u11-entra.dev.json (identifiers only). The script never creates, asks for,
# stores or prints a client secret, certificate, password or token, and it never touches Azure resources
# (U10's resource group and GitHub identity are not involved). Steps, each one a hard stop on failure:
#  1. signed-in tenant and subscription are the expected ones (DT-098);
#  2. the account may register applications (or both already exist); otherwise it stops and names the
#     missing permission. It never tries to elevate privileges;
#  3. existing registrations are looked up by display name: more than one is a stop (no duplicates);
#  4. plan: what would be created or changed. Nothing to do -> ALREADY_CONFIGURED;
#  5. confirmation (type CONFIGURAR; -Yes skips it), then create/patch through Microsoft Graph (az rest);
#  6. verification: both apps and service principals, the four app roles, the scope, the redirect URIs, no
#     implicit grant, no secrets, no certificates, no federated credentials, no duplicates;
#  7. evidence with identifiers only in tmp/u11-evidence/ (ignored by Git), plus entra-dev.env with the
#     three identifiers that the API and the SPA need (not secrets).
#
# App role assignments are separate and explicit (ASSUMPTION-010: no role is granted by default):
#   -AssignRole VIEWER[,PLANNER...]   assigns those roles to the SIGNED-IN user only;
#   -RemoveRole VIEWER[,...]          removes those assignments from the signed-in user.
# Other options:
#   -SelfTest        offline checks of this script's JSON handling and comparisons (no Azure call);
#   -PreflightOnly   steps 1-4 read-only, then stop;
#   -Yes             skips the confirmations;
#   -Rollback <run>  deletes ONLY the objects that run <run> created (tmp/u11-evidence/created-<run>.json),
#                    after typing ELIMINAR. Never anything else. Deleted registrations stay restorable for
#                    30 days in Entra ID (Deleted applications).
# ASCII only on purpose: Windows PowerShell 5.1 reads scripts without BOM as ANSI.

[CmdletBinding()]
param(
    [switch]$Yes,
    [switch]$SelfTest,
    [switch]$PreflightOnly,
    [string[]]$AssignRole = @(),
    [string[]]$RemoveRole = @(),
    [string]$Rollback = ''
)

$ErrorActionPreference = 'Stop'
# Windows PowerShell 5.1 serialises some arrays as {"value": [...], "Count": n} because of an extended type
# for System.Array; Graph would reject those bodies. PowerShell 6+ has no such type data.
if ($PSVersionTable.PSVersion.Major -lt 6) { Remove-TypeData -TypeName System.Array -ErrorAction SilentlyContinue }

$SpecPath = 'infra/azure/entra/u11-entra.dev.json'
$EvidenceDir = 'tmp/u11-evidence'
$Graph = 'https://graph.microsoft.com/v1.0'
# Directory roles that may register applications even when "Users can register applications" is No
# (Microsoft Learn, "Delegate app registration permissions"): template IDs of the built-in roles.
$AppCreatorRoles = @{
    'cf1c38e5-3621-4004-a7cb-879624dced7c' = 'Application Developer'
    '9b895d92-2cd3-44c7-9d02-a6ac2d5ea5c3' = 'Application Administrator'
    '158c047a-c907-4556-b7ef-446551a6b5f7' = 'Cloud Application Administrator'
    '62e90394-69f5-4237-9190-012177145e10' = 'Global Administrator'
}
$RunId = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$script:Created = New-Object System.Collections.Generic.List[object]

function Step([string]$Text) { Write-Host ''; Write-Host "== $Text" -ForegroundColor Cyan }

function Save-Created {
    if ($script:Created.Count -eq 0) { return }
    $record = [ordered]@{ runId = $RunId; created = $script:Created.ToArray() }
    Set-Content -Path (Join-Path $EvidenceDir "created-$RunId.json") -Value (ConvertTo-Json -InputObject $record -Depth 10) -Encoding ASCII
}

function Stop-U11([string]$Text) {
    Write-Host ''
    Write-Host "DETENIDO: $Text" -ForegroundColor Red
    if ($script:Created.Count -gt 0) {
        Save-Created
        Write-Host "Esta ejecucion creo $($script:Created.Count) objeto(s). Para deshacer SOLO esos objetos:" -ForegroundColor Yellow
        Write-Host "    powershell -ExecutionPolicy Bypass -File infra\azure\deploy-u11.ps1 -Rollback $RunId" -ForegroundColor Yellow
    }
    exit 1
}

# Same normalisation as deploy-dev.ps1 (U10): a JSON array is always a flat array, whatever the PowerShell.
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

# A property that may be missing, null, a scalar or an array -> flat array.
function As-Array($Value) {
    $items = New-Object System.Collections.Generic.List[object]
    if ($null -eq $Value) { return ,$items.ToArray() }
    if ($Value -is [System.Array]) {
        foreach ($v in $Value) {
            if ($v -is [System.Array]) { foreach ($i in $v) { if ($null -ne $i) { $items.Add($i) } } }
            elseif ($null -ne $v) { $items.Add($v) }
        }
    } else { $items.Add($Value) }
    return ,$items.ToArray()
}

function Get-Prop($Object, [string]$Name) {
    if ($null -eq $Object) { return $null }
    if ($Object -is [System.Collections.IDictionary]) { return $Object[$Name] }
    $p = $Object.PSObject.Properties[$Name]
    if ($null -eq $p) { return $null }
    return $p.Value
}

function Test-SameStrings($A, $B) {
    $x = @((As-Array $A) | ForEach-Object { "$_" } | Sort-Object)
    $y = @((As-Array $B) | ForEach-Object { "$_" } | Sort-Object)
    if ($x.Count -ne $y.Count) { return $false }
    for ($i = 0; $i -lt $x.Count; $i++) { if ($x[$i] -cne $y[$i]) { return $false } }
    return $true
}

$DeniedPattern = 'Authorization_RequestDenied|Insufficient privileges|Forbidden'

# Runs az; returns parsed JSON (-Array: flat array, -Raw: text). Stops on a non-zero exit, with a precise
# message when Entra ID denies the operation. No command used here prints a token.
function Invoke-Az {
    param([string[]]$Arguments, [switch]$Raw, [switch]$Array, [string]$What = 'az', [switch]$AllowFailure)
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $output = & az @Arguments 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = $previous
    $text = ($output | ForEach-Object { "$_" }) -join "`n"
    if ($code -ne 0) {
        if ($AllowFailure) { return $null }
        Write-Host $text
        if ($text -match $DeniedPattern) {
            Stop-U11 ("$What denegado por Microsoft Entra ID (Authorization_RequestDenied). No se intenta elevar privilegios. " +
                      "Para registrar aplicaciones hace falta que 'Users can register applications' este en Yes o el rol 'Application Developer'; " +
                      "para asignar roles, ser propietario del service principal de la API o un rol de administrador de aplicaciones.")
        }
        Stop-U11 "$What fallo (codigo $code)"
    }
    if ($Raw) { return $text }
    $json = ($output | Where-Object { $_ -isnot [System.Management.Automation.ErrorRecord] } | ForEach-Object { "$_" }) -join "`n"
    if ($Array) { return ,(ConvertFrom-AzJsonArray $json) }
    if ([string]::IsNullOrWhiteSpace($json)) { return $null }
    return (ConvertFrom-Json -InputObject $json)
}

# Microsoft Graph through `az rest` (the CLI's own delegated session); bodies go through a temporary file.
function Invoke-Graph {
    param([string]$Method, [string]$Path, $Body = $null, [string]$What = '', [switch]$AllowFailure)
    $arguments = @('rest', '--method', $Method, '--uri', "$Graph$Path", '--headers', 'Content-Type=application/json', '--output', 'json')
    $file = Join-Path $EvidenceDir "request-$RunId.json"
    if ($null -ne $Body) {
        Set-Content -Path $file -Value (ConvertTo-Json -InputObject $Body -Depth 20) -Encoding ASCII
        $arguments += @('--body', "@$file")
    }
    if (-not $What) { $What = "Graph $Method $Path" }
    try { return (Invoke-Az $arguments -What $What -AllowFailure:$AllowFailure) }
    finally { if ($null -ne $Body) { Remove-Item -Path $file -ErrorAction SilentlyContinue } }
}

# Graph collections come as {"value": [...]}.
function Get-GraphList([string]$Path) {
    $result = Invoke-Graph -Method 'GET' -Path $Path
    return ,(As-Array (Get-Prop $result 'value'))
}

# ---------------------------------------------------------------------------------------------------------
# Desired state and comparisons: pure functions, exercised by -SelfTest without Azure.

function New-ApiDesired($Spec, [string]$ApiAppId, [string]$SpaAppId) {
    $scope = $Spec.api.scope
    $preAuthorized = @()
    if ($SpaAppId) { $preAuthorized = @([ordered]@{ appId = $SpaAppId; delegatedPermissionIds = @($scope.id) }) }
    $roles = @()
    foreach ($r in (As-Array $Spec.api.appRoles)) {
        $roles += [ordered]@{ id = $r.id; value = $r.value; displayName = $r.displayName; description = $r.description
                              allowedMemberTypes = (As-Array $r.allowedMemberTypes); isEnabled = [bool]$r.isEnabled }
    }
    return [ordered]@{
        signInAudience = $Spec.signInAudience
        identifierUris = @("api://$ApiAppId")
        api = [ordered]@{
            requestedAccessTokenVersion = [int]$Spec.api.requestedAccessTokenVersion
            oauth2PermissionScopes = @([ordered]@{
                id = $scope.id; value = $scope.value; type = $scope.type; isEnabled = [bool]$scope.isEnabled
                adminConsentDisplayName = $scope.adminConsentDisplayName; adminConsentDescription = $scope.adminConsentDescription
                userConsentDisplayName = $scope.userConsentDisplayName; userConsentDescription = $scope.userConsentDescription
            })
            preAuthorizedApplications = $preAuthorized
        }
        appRoles = $roles
        web = [ordered]@{ redirectUris = @(); implicitGrantSettings = [ordered]@{ enableIdTokenIssuance = $false; enableAccessTokenIssuance = $false } }
    }
}

function New-SpaDesired($Spec, [string]$ApiAppId) {
    return [ordered]@{
        signInAudience = $Spec.signInAudience
        isFallbackPublicClient = $false
        spa = [ordered]@{ redirectUris = (As-Array $Spec.spa.redirectUris) }
        web = [ordered]@{ redirectUris = @(); implicitGrantSettings = [ordered]@{ enableIdTokenIssuance = $false; enableAccessTokenIssuance = $false } }
        publicClient = [ordered]@{ redirectUris = @() }
        requiredResourceAccess = @([ordered]@{ resourceAppId = $ApiAppId; resourceAccess = @([ordered]@{ id = $Spec.api.scope.id; type = 'Scope' }) })
    }
}

function Compare-Implicit($Current) {
    $diff = New-Object System.Collections.Generic.List[string]
    $web = Get-Prop $Current 'web'
    $implicit = Get-Prop $web 'implicitGrantSettings'
    if ((Get-Prop $implicit 'enableIdTokenIssuance') -eq $true -or (Get-Prop $implicit 'enableAccessTokenIssuance') -eq $true) { $diff.Add('web.implicitGrantSettings') }
    if ((As-Array (Get-Prop $web 'redirectUris')).Count -ne 0) { $diff.Add('web.redirectUris') }
    return ,$diff.ToArray()
}

# Differences between an application read from Graph and the desired state (empty: configured).
function Compare-Api($Current, $Desired) {
    $diff = New-Object System.Collections.Generic.List[string]
    if ((Get-Prop $Current 'signInAudience') -ne $Desired.signInAudience) { $diff.Add('signInAudience') }
    if (-not (Test-SameStrings (Get-Prop $Current 'identifierUris') $Desired.identifierUris)) { $diff.Add('identifierUris') }
    $api = Get-Prop $Current 'api'
    if ("$(Get-Prop $api 'requestedAccessTokenVersion')" -ne "$($Desired.api.requestedAccessTokenVersion)") { $diff.Add('api.requestedAccessTokenVersion') }
    $scopes = As-Array (Get-Prop $api 'oauth2PermissionScopes')
    $want = $Desired.api.oauth2PermissionScopes[0]
    $ok = ($scopes.Count -eq 1)
    if ($ok) {
        foreach ($k in @('id', 'value', 'type', 'isEnabled', 'adminConsentDisplayName', 'adminConsentDescription', 'userConsentDisplayName', 'userConsentDescription')) {
            if ("$(Get-Prop $scopes[0] $k)" -cne "$($want[$k])") { $ok = $false }
        }
    }
    if (-not $ok) { $diff.Add('api.oauth2PermissionScopes') }
    $pre = As-Array (Get-Prop $api 'preAuthorizedApplications')
    $wantPre = As-Array $Desired.api.preAuthorizedApplications
    $okPre = ($pre.Count -eq $wantPre.Count)
    if ($okPre -and $wantPre.Count -eq 1) {
        $okPre = ((Get-Prop $pre[0] 'appId') -eq $wantPre[0].appId) -and (Test-SameStrings (Get-Prop $pre[0] 'delegatedPermissionIds') $wantPre[0].delegatedPermissionIds)
    }
    if (-not $okPre) { $diff.Add('api.preAuthorizedApplications') }
    $roles = As-Array (Get-Prop $Current 'appRoles')
    $okRoles = ($roles.Count -eq $Desired.appRoles.Count)
    if ($okRoles) {
        foreach ($w in $Desired.appRoles) {
            $match = @($roles | Where-Object { (Get-Prop $_ 'id') -eq $w.id })
            if ($match.Count -ne 1) { $okRoles = $false; continue }
            foreach ($k in @('value', 'displayName', 'description', 'isEnabled')) { if ("$(Get-Prop $match[0] $k)" -cne "$($w[$k])") { $okRoles = $false } }
            if (-not (Test-SameStrings (Get-Prop $match[0] 'allowedMemberTypes') $w.allowedMemberTypes)) { $okRoles = $false }
        }
    }
    if (-not $okRoles) { $diff.Add('appRoles') }
    foreach ($d in (Compare-Implicit $Current)) { $diff.Add($d) }
    return ,$diff.ToArray()
}

function Compare-Spa($Current, $Desired) {
    $diff = New-Object System.Collections.Generic.List[string]
    if ((Get-Prop $Current 'signInAudience') -ne $Desired.signInAudience) { $diff.Add('signInAudience') }
    if ((Get-Prop $Current 'isFallbackPublicClient') -eq $true) { $diff.Add('isFallbackPublicClient') }
    if (-not (Test-SameStrings (Get-Prop (Get-Prop $Current 'spa') 'redirectUris') $Desired.spa.redirectUris)) { $diff.Add('spa.redirectUris') }
    if ((As-Array (Get-Prop (Get-Prop $Current 'publicClient') 'redirectUris')).Count -ne 0) { $diff.Add('publicClient.redirectUris') }
    $rra = As-Array (Get-Prop $Current 'requiredResourceAccess')
    $want = $Desired.requiredResourceAccess[0]
    $ok = ($rra.Count -eq 1) -and ((Get-Prop $rra[0] 'resourceAppId') -eq $want.resourceAppId)
    if ($ok) {
        $access = As-Array (Get-Prop $rra[0] 'resourceAccess')
        $ok = ($access.Count -eq 1) -and ((Get-Prop $access[0] 'id') -eq $want.resourceAccess[0].id) -and ((Get-Prop $access[0] 'type') -eq 'Scope')
    }
    if (-not $ok) { $diff.Add('requiredResourceAccess') }
    foreach ($d in (Compare-Implicit $Current)) { $diff.Add($d) }
    return ,$diff.ToArray()
}

# Secrets and certificates must never exist on these objects (the SPA is a public client; the API needs none).
function Get-CredentialProblems($Object, [string]$Label) {
    $problems = New-Object System.Collections.Generic.List[string]
    if ((As-Array (Get-Prop $Object 'passwordCredentials')).Count -ne 0) { $problems.Add("$Label tiene secretos de cliente (passwordCredentials)") }
    if ((As-Array (Get-Prop $Object 'keyCredentials')).Count -ne 0) { $problems.Add("$Label tiene certificados o claves (keyCredentials)") }
    return ,$problems.ToArray()
}

function Test-Spec($Spec) {
    $problems = New-Object System.Collections.Generic.List[string]
    $guid = '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    $values = @((As-Array $Spec.api.appRoles) | ForEach-Object { $_.value })
    if (-not (Test-SameStrings $values @('VIEWER', 'ANALYST', 'PLANNER', 'ADMIN'))) { $problems.Add('los app roles deben ser exactamente los cuatro de ASSUMPTION-010') }
    $ids = @((As-Array $Spec.api.appRoles) | ForEach-Object { $_.id }) + @($Spec.api.scope.id)
    foreach ($id in $ids) { if ("$id" -notmatch $guid) { $problems.Add("GUID invalido: $id") } }
    if (@($ids | Sort-Object -Unique).Count -ne $ids.Count) { $problems.Add('GUID repetidos') }
    if ($Spec.api.scope.value -ne 'access_as_user') { $problems.Add('el scope debe ser access_as_user') }
    # dev: Vite and Docker on localhost, and (U12, DT-100) the HTTPS frontend of Azure Container Apps.
    foreach ($uri in (As-Array $Spec.spa.redirectUris)) { if ("$uri" -notmatch '^(http://localhost:\d+|https://[a-z0-9.-]+\.azurecontainerapps\.io)$') { $problems.Add("redirect URI no permitido en dev: $uri") } }
    if ("$($Spec.tenantId)" -notmatch $guid) { $problems.Add('tenantId invalido') }
    return ,$problems.ToArray()
}

if ($SelfTest) {
    $script:failed = 0
    function Check([string]$Name, [bool]$Ok) {
        if (-not $Ok) { $script:failed++ }
        Write-Host ("{0}  {1}" -f ($(if ($Ok) { 'OK  ' } else { 'FAIL' })), $Name)
    }
    foreach ($pair in @(@('[]', 0), @('', 0), @('null', 0), @('[{"a":1}]', 1), @('[{"a":1},{"a":2}]', 2))) {
        Check ("lista JSON '{0}' -> {1}" -f $pair[0], $pair[1]) ((ConvertFrom-AzJsonArray $pair[0]).Count -eq $pair[1])
    }
    $spec = Get-Content -Raw -Path $SpecPath | ConvertFrom-Json
    Check 'especificacion valida (cuatro roles de ASSUMPTION-010, GUID fijos, scope, redirect URIs)' ((Test-Spec $spec).Count -eq 0)
    $apiId = 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee'; $spaId = '12345678-bbbb-4ccc-8ddd-eeeeeeeeeeee'
    $apiDesired = New-ApiDesired $spec $apiId $spaId
    $spaDesired = New-SpaDesired $spec $apiId
    $apiJson = ConvertTo-Json -InputObject $apiDesired -Depth 20
    $spaJson = ConvertTo-Json -InputObject $spaDesired -Depth 20
    # Round trip through JSON, as Graph returns it: a configured application has no differences.
    Check 'API configurada -> sin diferencias (ALREADY_CONFIGURED)' ((Compare-Api (ConvertFrom-Json -InputObject $apiJson) $apiDesired).Count -eq 0)
    Check 'SPA configurada -> sin diferencias (ALREADY_CONFIGURED)' ((Compare-Spa (ConvertFrom-Json -InputObject $spaJson) $spaDesired).Count -eq 0)
    Check 'listas de un elemento siguen siendo listas en el cuerpo JSON' (($apiJson -match '"oauth2PermissionScopes":\s*\[') -and ($apiJson -match '"preAuthorizedApplications":\s*\[') -and ($apiJson -match '"identifierUris":\s*\[') -and ($spaJson -match '"requiredResourceAccess":\s*\[') -and ($spaJson -match '"resourceAccess":\s*\['))
    Check 'listas vacias se envian como []' (($apiJson -match '"redirectUris":\s*\[\s*\]') -and ($spaJson -match '"publicClient":\s*\{\s*"redirectUris":\s*\[\s*\]'))
    Check 'allowedMemberTypes es una lista plana ["User"] en el cuerpo' (($apiJson -replace '\s', '') -match '"allowedMemberTypes":\["User"\]')
    Check 'redirect URIs como lista plana en el cuerpo' (($spaJson -replace '\s', '') -match '"redirectUris":\["http://localhost:5173","http://localhost:8080"\]')
    Check 'comparacion de listas elemento a elemento' ((Test-SameStrings @('a', 'b') @('b', 'a')) -and -not (Test-SameStrings @('a b') @('a', 'b')) -and -not (Test-SameStrings @('a') @('a', 'a')))
    Check 'ningun secreto en los cuerpos' (-not (($apiJson + $spaJson) -match 'passwordCredentials|keyCredentials|secret'))
    $fresh = ConvertFrom-Json -InputObject '{"signInAudience":"AzureADMyOrg","identifierUris":[],"api":{"requestedAccessTokenVersion":null,"oauth2PermissionScopes":[],"preAuthorizedApplications":[]},"appRoles":[],"web":{"redirectUris":[],"implicitGrantSettings":{"enableIdTokenIssuance":false,"enableAccessTokenIssuance":false}}}'
    Check 'API recien creada -> uris, version, scope, preautorizacion y roles' (Test-SameStrings (Compare-Api $fresh $apiDesired) @('identifierUris', 'api.requestedAccessTokenVersion', 'api.oauth2PermissionScopes', 'api.preAuthorizedApplications', 'appRoles'))
    $implicit = ConvertFrom-Json -InputObject ($spaJson -replace '"enableAccessTokenIssuance":\s*false', '"enableAccessTokenIssuance": true')
    Check 'flujo implicito activado -> diferencia' ((Compare-Spa $implicit $spaDesired) -contains 'web.implicitGrantSettings')
    $otherUri = ConvertFrom-Json -InputObject $spaJson
    $otherUri.spa.redirectUris = @('http://localhost:5173')
    Check 'redirect URI ausente -> diferencia' ((Compare-Spa $otherUri $spaDesired) -contains 'spa.redirectUris')
    $graphScope = ConvertFrom-Json -InputObject $spaJson
    $graphScope.requiredResourceAccess[0].resourceAppId = '00000003-0000-0000-c000-000000000000'
    Check 'permiso de otra API (Graph) -> diferencia' ((Compare-Spa $graphScope $spaDesired) -contains 'requiredResourceAccess')
    $roleChanged = ConvertFrom-Json -InputObject $apiJson
    $roleChanged.appRoles[0].value = 'Viewer'
    Check 'valor de rol cambiado -> diferencia' ((Compare-Api $roleChanged $apiDesired) -contains 'appRoles')
    Check 'secreto de cliente -> detectado' ((Get-CredentialProblems (ConvertFrom-Json -InputObject '{"passwordCredentials":[{"keyId":"x"}],"keyCredentials":[]}') 'x').Count -eq 1)
    Check 'certificado -> detectado' ((Get-CredentialProblems (ConvertFrom-Json -InputObject '{"passwordCredentials":[],"keyCredentials":[{"keyId":"x"}]}') 'x').Count -eq 1)
    Check 'sin secretos -> limpio' ((Get-CredentialProblems (ConvertFrom-Json -InputObject '{"passwordCredentials":[],"keyCredentials":[]}') 'x').Count -eq 0)
    $bad = Get-Content -Raw -Path $SpecPath | ConvertFrom-Json
    $bad.api.appRoles[3].value = 'Administrator'
    Check 'rol fuera de ASSUMPTION-010 -> especificacion rechazada' ((Test-Spec $bad).Count -gt 0)
    Write-Host ("PowerShell {0}: {1}" -f $PSVersionTable.PSVersion, $(if ($script:failed -eq 0) { 'SELFTEST OK' } else { "SELFTEST FALLO ($($script:failed))" }))
    if ($script:failed -eq 0) { exit 0 } else { exit 1 }
}

# ---------------------------------------------------------------------------------------------------------
if (-not (Test-Path $SpecPath)) { Stop-U11 'ejecuta el script desde la raiz del repositorio' }
New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null
$Spec = Get-Content -Raw -Path $SpecPath | ConvertFrom-Json
$specProblems = Test-Spec $Spec
if ($specProblems.Count -gt 0) { Stop-U11 ("especificacion invalida: " + ($specProblems -join '; ')) }
$KnownRoles = @{}
foreach ($r in (As-Array $Spec.api.appRoles)) { $KnownRoles[$r.value] = $r.id }
$requestedRoles = @(@($AssignRole) + @($RemoveRole) | ForEach-Object { "$_".Split(',') } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
foreach ($name in $requestedRoles) { if (-not $KnownRoles.ContainsKey($name)) { Stop-U11 "rol desconocido: $name (VIEWER, ANALYST, PLANNER, ADMIN)" } }

function Confirm-Or-Stop([string]$Word, [string]$Prompt) {
    if ($Yes) { return }
    $answer = Read-Host "Escribe $Word para $Prompt"
    if ($answer -cne $Word) { Stop-U11 'cancelado por el responsable' }
}

# Rollback: only what one run of this script recorded as created ---------------------------------------
if ($Rollback) {
    Step "Rollback de la ejecucion $Rollback"
    if ($Rollback -notmatch '^\d{8}T\d{6}Z$') { Stop-U11 'identificador de ejecucion invalido' }
    $file = Join-Path $EvidenceDir "created-$Rollback.json"
    if (-not (Test-Path $file)) { Stop-U11 "no existe ${file}: solo se deshace lo que registro una ejecucion de este script" }
    $items = As-Array (Get-Content -Raw -Path $file | ConvertFrom-Json).created
    foreach ($item in $items) { Write-Host ("  {0} {1} (objectId {2})" -f $item.kind, $item.displayName, $item.id) }
    Confirm-Or-Stop 'ELIMINAR' 'borrar EXACTAMENTE estos objetos y ninguno mas'
    foreach ($kind in @('servicePrincipal', 'application')) {
        foreach ($item in @($items | Where-Object { $_.kind -eq $kind })) {
            $path = "/servicePrincipals/$($item.id)"
            if ($kind -eq 'application') { $path = "/applications/$($item.id)" }
            $current = Invoke-Graph -Method 'GET' -Path $path -AllowFailure
            if ($null -eq $current) { Write-Host "  ya no existe: $($item.displayName)"; continue }
            if ($current.appId -ne $item.appId) { Stop-U11 "el objeto $($item.id) no coincide con el registro; no se borra" }
            Invoke-Graph -Method 'DELETE' -Path $path -What "borrar $kind $($item.displayName)" | Out-Null
            Write-Host "  borrado: $kind $($item.displayName)"
        }
    }
    Write-Host 'ROLLBACK COMPLETADO (las aplicaciones quedan 30 dias en Deleted applications de Entra ID).'
    exit 0
}

# 1 ------------------------------------------------------------------------------------------------------
Step '1. Sesion de Azure CLI: tenant y suscripcion'
$account = Invoke-Az @('account', 'show', '--output', 'json') -What 'az account show (ejecuta az login primero)'
Write-Host ("Tenant: {0} | suscripcion: {1} | tipo de cuenta: {2}" -f $account.tenantId, $account.name, $account.user.type)
if ($account.tenantId -ne $Spec.tenantId) { Stop-U11 "el tenant activo no es el de DT-098 ($($Spec.tenantId))" }
if ($account.name -notmatch [regex]::Escape($Spec.subscriptionName)) { Stop-U11 "la suscripcion activa no es $($Spec.subscriptionName)" }
if ($account.user.type -ne 'user') { Stop-U11 'la sesion debe ser la del responsable (usuario), no una entidad de servicio' }
$UserId = (Invoke-Az @('ad', 'signed-in-user', 'show', '--query', '{id:id}', '--output', 'json') -What 'az ad signed-in-user show').id
Write-Host "Usuario (objectId): $UserId"

# 2 ------------------------------------------------------------------------------------------------------
Step '2. Permisos minimos en el tenant'
$policy = Invoke-Graph -Method 'GET' -Path '/policies/authorizationPolicy' -AllowFailure
$usersCanCreate = $null
if ($null -ne $policy) { $usersCanCreate = Get-Prop (Get-Prop $policy 'defaultUserRolePermissions') 'allowedToCreateApps' }
$myRoles = As-Array (Get-Prop (Invoke-Graph -Method 'GET' -Path '/me/memberOf/microsoft.graph.directoryRole' -AllowFailure) 'value')
$creatorRoles = @($myRoles | Where-Object { $AppCreatorRoles.ContainsKey("$(Get-Prop $_ 'roleTemplateId')") } | ForEach-Object { $AppCreatorRoles["$(Get-Prop $_ 'roleTemplateId')"] })
$policyText = 'no se pudo leer'
if ($null -ne $usersCanCreate) { $policyText = "$usersCanCreate" }
$rolesText = 'ninguno'
if ($creatorRoles.Count) { $rolesText = $creatorRoles -join ', ' }
Write-Host "Los usuarios pueden registrar aplicaciones: $policyText | roles de directorio que lo permiten: $rolesText"
$CanCreate = ($usersCanCreate -eq $true) -or ($creatorRoles.Count -gt 0)

# 3 ------------------------------------------------------------------------------------------------------
Step '3. Registros existentes (sin duplicados)'
function Find-App([string]$Name) {
    $found = Invoke-Az @('ad', 'app', 'list', '--filter', "displayName eq '$Name'", '--output', 'json') -Array -What "az ad app list ($Name)"
    if ($found.Count -gt 1) { Stop-U11 "hay $($found.Count) aplicaciones llamadas ${Name}: no se crea otra ni se elige una; revisalas en Entra ID" }
    if ($found.Count -eq 1) { return (Invoke-Graph -Method 'GET' -Path "/applications/$($found[0].id)") }
    return $null
}
function Find-Sp([string]$AppId) {
    $found = Invoke-Az @('ad', 'sp', 'list', '--filter', "appId eq '$AppId'", '--output', 'json') -Array -What 'az ad sp list'
    if ($found.Count -gt 1) { Stop-U11 "hay $($found.Count) service principals para $AppId" }
    if ($found.Count -eq 1) { return (Invoke-Graph -Method 'GET' -Path "/servicePrincipals/$($found[0].id)") }
    return $null
}
$ApiApp = Find-App $Spec.api.displayName
$SpaApp = Find-App $Spec.spa.displayName
foreach ($pair in @(@($ApiApp, 'API'), @($SpaApp, 'SPA'))) {
    if ($pair[0]) { Write-Host ("{0}: existe (appId {1})" -f $pair[1], $pair[0].appId) } else { Write-Host ("{0}: no existe" -f $pair[1]) }
    if ($pair[0]) { $p = Get-CredentialProblems $pair[0] $pair[1]; if ($p.Count) { Stop-U11 (($p -join '; ') + ': U11 no admite secretos; retiralos en Entra ID antes de continuar') } }
}
if ((-not $ApiApp -or -not $SpaApp) -and -not $CanCreate) {
    if ($null -eq $usersCanCreate) {
        Write-Host 'No se pudo leer la politica de registro; se intentara y una denegacion detendra el script.' -ForegroundColor Yellow
    } else {
        Stop-U11 ("la cuenta no puede registrar aplicaciones ('Users can register applications' = No y sin rol 'Application Developer'). " +
                  'Un administrador del tenant debe asignarle ese rol o crear los registros. No se intenta elevar privilegios.')
    }
}

# 4 ------------------------------------------------------------------------------------------------------
Step '4. Plan'
$plan = New-Object System.Collections.Generic.List[string]
if (-not $ApiApp) { $plan.Add("CREAR aplicacion $($Spec.api.displayName) (API) y configurarla") }
if (-not $SpaApp) { $plan.Add("CREAR aplicacion $($Spec.spa.displayName) (SPA) y configurarla") }
if ($ApiApp -and $SpaApp) {
    $d = Compare-Api $ApiApp (New-ApiDesired $Spec $ApiApp.appId $SpaApp.appId)
    if ($d.Count) { $plan.Add("ACTUALIZAR API: $($d -join ', ')") }
    $d = Compare-Spa $SpaApp (New-SpaDesired $Spec $ApiApp.appId)
    if ($d.Count) { $plan.Add("ACTUALIZAR SPA: $($d -join ', ')") }
}
if ($ApiApp) {
    $sp = Find-Sp $ApiApp.appId
    if (-not $sp) { $plan.Add('CREAR service principal de la API') }
    elseif ($sp.appRoleAssignmentRequired -ne $true) { $plan.Add('ACTUALIZAR service principal de la API: appRoleAssignmentRequired') }
}
if ($SpaApp -and -not (Find-Sp $SpaApp.appId)) { $plan.Add('CREAR service principal de la SPA') }
if ($plan.Count -eq 0) { Write-Host 'ALREADY_CONFIGURED' -ForegroundColor Green } else { foreach ($line in $plan) { Write-Host "  $line" } }
if ($PreflightOnly) { Write-Host ''; Write-Host 'PreflightOnly: sin cambios. Fin.'; exit 0 }

# 5 ------------------------------------------------------------------------------------------------------
function New-App([string]$Name, [string]$Kind) {
    $app = Invoke-Az @('ad', 'app', 'create', '--display-name', $Name, '--sign-in-audience', $Spec.signInAudience, '--output', 'json') -What "az ad app create ($Name)"
    $script:Created.Add([ordered]@{ kind = 'application'; role = $Kind; id = $app.id; appId = $app.appId; displayName = $Name })
    Save-Created
    Write-Host "  creada: $Name (appId $($app.appId))"
    return $app
}
function New-Sp([string]$AppId, [string]$Kind) {
    $sp = Invoke-Az @('ad', 'sp', 'create', '--id', $AppId, '--output', 'json') -What "az ad sp create ($Kind)"
    $script:Created.Add([ordered]@{ kind = 'servicePrincipal'; role = $Kind; id = $sp.id; appId = $AppId; displayName = $sp.displayName })
    Save-Created
    Write-Host "  creado: service principal ($Kind)"
    return $sp
}
function Ensure-Owner([string]$Collection, [string]$ObjectId, [string]$Label) {
    $owners = Get-GraphList "/$Collection/$ObjectId/owners?`$select=id"
    if (@($owners | Where-Object { $_.id -eq $UserId }).Count -ge 1) { return }
    Invoke-Graph -Method 'POST' -Path "/$Collection/$ObjectId/owners/`$ref" -Body ([ordered]@{ '@odata.id' = "$Graph/directoryObjects/$UserId" }) -What "anadir propietario ($Label)" | Out-Null
    Write-Host "  propietario anadido: $Label"
}

if ($plan.Count -gt 0) {
    Step '5. Configuracion'
    Confirm-Or-Stop 'CONFIGURAR' 'aplicar el plan en Microsoft Entra ID'
    if (-not $ApiApp) { $ApiApp = New-App $Spec.api.displayName 'api' }
    if (-not $SpaApp) { $SpaApp = New-App $Spec.spa.displayName 'spa' }
    # The scope must exist before a client is pre-authorized for it: first the API without pre-authorization.
    $apiNow = Invoke-Graph -Method 'GET' -Path "/applications/$($ApiApp.id)"
    $scopeIds = @((As-Array (Get-Prop (Get-Prop $apiNow 'api') 'oauth2PermissionScopes')) | ForEach-Object { $_.id })
    if ($scopeIds -notcontains $Spec.api.scope.id) {
        Invoke-Graph -Method 'PATCH' -Path "/applications/$($ApiApp.id)" -Body (New-ApiDesired $Spec $ApiApp.appId '') -What 'configurar la API (scope, roles, token v2)' | Out-Null
    }
    $apiDesired = New-ApiDesired $Spec $ApiApp.appId $SpaApp.appId
    if ((Compare-Api (Invoke-Graph -Method 'GET' -Path "/applications/$($ApiApp.id)") $apiDesired).Count -gt 0) {
        Invoke-Graph -Method 'PATCH' -Path "/applications/$($ApiApp.id)" -Body $apiDesired -What 'configurar la API' | Out-Null
    }
    Write-Host '  API configurada'
    $spaDesired = New-SpaDesired $Spec $ApiApp.appId
    if ((Compare-Spa (Invoke-Graph -Method 'GET' -Path "/applications/$($SpaApp.id)") $spaDesired).Count -gt 0) {
        Invoke-Graph -Method 'PATCH' -Path "/applications/$($SpaApp.id)" -Body $spaDesired -What 'configurar la SPA' | Out-Null
    }
    Write-Host '  SPA configurada'
    $ApiSp = Find-Sp $ApiApp.appId
    if (-not $ApiSp) { $ApiSp = New-Sp $ApiApp.appId 'api' }
    if ($ApiSp.appRoleAssignmentRequired -ne $true) {
        Invoke-Graph -Method 'PATCH' -Path "/servicePrincipals/$($ApiSp.id)" -Body ([ordered]@{ appRoleAssignmentRequired = $true }) -What 'exigir asignacion en la API' | Out-Null
        Write-Host '  API: appRoleAssignmentRequired activado (filtra clientes; a los usuarios sin rol los bloquea la API con 403)'
    }
    if (-not (Find-Sp $SpaApp.appId)) { New-Sp $SpaApp.appId 'spa' | Out-Null }
}
$ApiSp = Find-Sp $ApiApp.appId
$SpaSp = Find-Sp $SpaApp.appId
if ($ApiSp -and $SpaSp) {
    # Owner of the API's service principal = may assign users to its roles (Learn, "Assign users and groups").
    Ensure-Owner 'applications' $ApiApp.id 'aplicacion API'
    Ensure-Owner 'applications' $SpaApp.id 'aplicacion SPA'
    Ensure-Owner 'servicePrincipals' $ApiSp.id 'service principal API'
    Ensure-Owner 'servicePrincipals' $SpaSp.id 'service principal SPA'
}

# Role assignments: explicit, signed-in user only ------------------------------------------------------
if ($requestedRoles.Count -gt 0) {
    Step 'Asignaciones de roles del usuario actual'
    if (-not $ApiSp) { Stop-U11 'no existe el service principal de la API' }
    $assigned = Get-GraphList "/servicePrincipals/$($ApiSp.id)/appRoleAssignedTo"
    foreach ($name in @(@($AssignRole) | ForEach-Object { "$_".Split(',') } | ForEach-Object { $_.Trim() } | Where-Object { $_ })) {
        $roleId = $KnownRoles[$name]
        if (@($assigned | Where-Object { $_.principalId -eq $UserId -and $_.appRoleId -eq $roleId }).Count) { Write-Host "  $name ya estaba asignado"; continue }
        Invoke-Graph -Method 'POST' -Path "/servicePrincipals/$($ApiSp.id)/appRoleAssignedTo" -Body ([ordered]@{ principalId = $UserId; resourceId = $ApiSp.id; appRoleId = $roleId }) -What "asignar $name" | Out-Null
        Write-Host "  $name asignado al usuario actual"
    }
    foreach ($name in @(@($RemoveRole) | ForEach-Object { "$_".Split(',') } | ForEach-Object { $_.Trim() } | Where-Object { $_ })) {
        $roleId = $KnownRoles[$name]
        foreach ($a in @($assigned | Where-Object { $_.principalId -eq $UserId -and $_.appRoleId -eq $roleId })) {
            Invoke-Graph -Method 'DELETE' -Path "/servicePrincipals/$($ApiSp.id)/appRoleAssignedTo/$($a.id)" -What "retirar $name" | Out-Null
            Write-Host "  $name retirado del usuario actual"
        }
    }
    Write-Host 'Los roles cambiados llegan en el siguiente token: cierra sesion en la SPA y vuelve a entrar.'
}

# 6 ------------------------------------------------------------------------------------------------------
Step '6. Verificacion'
$script:failures = 0
function Assert([string]$Name, [bool]$Ok) {
    if (-not $Ok) { $script:failures++ }
    $label = 'FAIL'; $color = 'Red'
    if ($Ok) { $label = 'OK  '; $color = 'Green' }
    Write-Host "$label  $Name" -ForegroundColor $color
}
$apiList = Invoke-Az @('ad', 'app', 'list', '--filter', "displayName eq '$($Spec.api.displayName)'", '--output', 'json') -Array -What 'az ad app list'
$spaList = Invoke-Az @('ad', 'app', 'list', '--filter', "displayName eq '$($Spec.spa.displayName)'", '--output', 'json') -Array -What 'az ad app list'
Assert 'una sola aplicacion API y una sola SPA (sin duplicados)' (($apiList.Count -eq 1) -and ($spaList.Count -eq 1))
$ApiApp = Invoke-Graph -Method 'GET' -Path "/applications/$($ApiApp.id)"
$SpaApp = Invoke-Graph -Method 'GET' -Path "/applications/$($SpaApp.id)"
Assert 'API: api://<appId>, token v2, scope access_as_user, cuatro app roles, SPA preautorizada, sin flujo implicito' ((Compare-Api $ApiApp (New-ApiDesired $Spec $ApiApp.appId $SpaApp.appId)).Count -eq 0)
Assert 'SPA: redirect URIs exactos en la plataforma SPA, solo el scope de la API, sin flujo implicito' ((Compare-Spa $SpaApp (New-SpaDesired $Spec $ApiApp.appId)).Count -eq 0)
Assert 'API y SPA son registros distintos' ($ApiApp.appId -ne $SpaApp.appId)
$ApiSp = Find-Sp $ApiApp.appId
$SpaSp = Find-Sp $SpaApp.appId
Assert 'service principals de la API y de la SPA' (($null -ne $ApiSp) -and ($null -ne $SpaSp))
$credentialProblems = (Get-CredentialProblems $ApiApp 'API') + (Get-CredentialProblems $SpaApp 'SPA')
if ($ApiSp) { $credentialProblems += (Get-CredentialProblems $ApiSp 'service principal API') }
if ($SpaSp) { $credentialProblems += (Get-CredentialProblems $SpaSp 'service principal SPA') }
Assert 'cero secretos de cliente y cero certificados (aplicaciones y service principals)' ($credentialProblems.Count -eq 0)
$fics = (Get-GraphList "/applications/$($ApiApp.id)/federatedIdentityCredentials") + (Get-GraphList "/applications/$($SpaApp.id)/federatedIdentityCredentials")
Assert 'sin credenciales federadas en estas aplicaciones (la de GitHub es la identidad de U10)' ($fics.Count -eq 0)
Assert 'API: appRoleAssignmentRequired activado (los usuarios sin rol reciben 403 de la API)' (($null -ne $ApiSp) -and ($ApiSp.appRoleAssignmentRequired -eq $true))
$roleById = @{}
foreach ($k in $KnownRoles.Keys) { $roleById[$KnownRoles[$k]] = $k }
$assignmentSummary = @()
if ($ApiSp) {
    foreach ($a in (Get-GraphList "/servicePrincipals/$($ApiSp.id)/appRoleAssignedTo")) {
        $assignmentSummary += [ordered]@{ principalId = $a.principalId; principalType = $a.principalType; role = $roleById["$($a.appRoleId)"] }
    }
}
Assert 'toda asignacion es uno de los cuatro roles' (@($assignmentSummary | Where-Object { -not $_.role }).Count -eq 0)
if ($assignmentSummary.Count) {
    Write-Host ('Asignaciones: ' + (($assignmentSummary | ForEach-Object { "$($_.role) -> $($_.principalType) $($_.principalId)" }) -join '; '))
} else {
    Write-Host 'Asignaciones: ninguna (la API responde 403 a todo salvo /me). Para la prueba real: -AssignRole VIEWER'
}

# 7 ------------------------------------------------------------------------------------------------------
$evidence = [ordered]@{
    date = (Get-Date).ToUniversalTime().ToString('o'); runId = $RunId; tenantId = $account.tenantId; subscription = $account.name
    api = [ordered]@{
        displayName = $ApiApp.displayName; appId = $ApiApp.appId; objectId = $ApiApp.id; servicePrincipalId = $ApiSp.id
        identifierUri = "api://$($ApiApp.appId)"; scope = "api://$($ApiApp.appId)/$($Spec.api.scope.value)"; scopeId = $Spec.api.scope.id
        audience = $ApiApp.appId; issuer = "https://login.microsoftonline.com/$($account.tenantId)/v2.0"
        requestedAccessTokenVersion = $ApiApp.api.requestedAccessTokenVersion; appRoleAssignmentRequired = $ApiSp.appRoleAssignmentRequired
        appRoles = @((As-Array $ApiApp.appRoles) | ForEach-Object { [ordered]@{ value = $_.value; id = $_.id; isEnabled = $_.isEnabled; allowedMemberTypes = (As-Array $_.allowedMemberTypes) } })
    }
    spa = [ordered]@{ displayName = $SpaApp.displayName; appId = $SpaApp.appId; objectId = $SpaApp.id; servicePrincipalId = $SpaSp.id; redirectUris = (As-Array $SpaApp.spa.redirectUris) }
    clientSecrets = 0; certificates = 0; credentialProblems = $credentialProblems; assignments = $assignmentSummary
    createdThisRun = $script:Created.ToArray(); checksFailed = $script:failures
}
Set-Content -Path (Join-Path $EvidenceDir 'u11-evidence.json') -Value (ConvertTo-Json -InputObject $evidence -Depth 20) -Encoding ASCII
Set-Content -Path (Join-Path $EvidenceDir 'entra-dev.env') -Encoding ASCII -Value @(
    '# U11 (DT-099): identificadores de Entra ID de dev (no son secretos). Generado por infra/azure/deploy-u11.ps1.',
    "ENTRA_TENANT_ID=$($account.tenantId)", "ENTRA_API_CLIENT_ID=$($ApiApp.appId)", "ENTRA_SPA_CLIENT_ID=$($SpaApp.appId)")
Set-Content -Path (Join-Path $EvidenceDir 'frontend.env.development.local') -Encoding ASCII -Value @(
    '# Para npm run dev con Entra ID: copiar a frontend/.env.development.local (ignorado por Git). U11, DT-099.',
    'VITE_APP_ENV=dev', "VITE_ENTRA_TENANT_ID=$($account.tenantId)", "VITE_ENTRA_SPA_CLIENT_ID=$($SpaApp.appId)",
    "VITE_ENTRA_API_SCOPE=api://$($ApiApp.appId)/$($Spec.api.scope.value)", 'VITE_ENTRA_REDIRECT_URI=http://localhost:5173')
Write-Host ''
Write-Host "Evidencia (solo identificadores): $EvidenceDir/u11-evidence.json, entra-dev.env y frontend.env.development.local"
if ($script:failures -gt 0) { Stop-U11 "$($script:failures) comprobacion(es) fallaron" }
if ($plan.Count -eq 0 -and $script:Created.Count -eq 0) { Write-Host 'ALREADY_CONFIGURED' -ForegroundColor Green }
Write-Host 'U11: Entra ID configurado y verificado.' -ForegroundColor Green
