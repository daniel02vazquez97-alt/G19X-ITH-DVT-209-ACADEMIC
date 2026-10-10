# U12 (DT-100): guarded deployment of the `dev` system to Azure Container Apps, run by the project owner from the
# repository root with an Azure CLI session that is already signed in (the same way as deploy-dev.ps1 for U10):
#
#     powershell -ExecutionPolicy Bypass -File infra\azure\deploy-u12.ps1 -PreflightOnly
#     powershell -ExecutionPolicy Bypass -File infra\azure\deploy-u12.ps1 -Stage <stage> [-ImageTag <sha>] [-Yes]
#
# Stages, in this order the first time (infra/azure/u12/README.md):
#   -PreflightOnly (same as -Stage Preflight, the default): STRICTLY read-only. Sections 1-12: session, subscription,
#              group and existing U12 resources, providers and region, Key Vault, RBAC (your deploy/action, GitHub and
#              runtime identities), ACR, PostgreSQL, Container Apps, Bicep build/lint/parameters and the DT-100 values,
#              secret scan and configuration tests. Every az call is checked against a read-only allow list
#              (Test-ReadOnlyAz) before it runs; nothing is written to Azure or to disk. Ends with PREFLIGHT OK (exit
#              0) or PREFLIGHT BLOQUEADO (exit 1), and says whether the KeyVaultRole stage is needed.
#   KeyVaultRole  only if Preflight says your session lacks deploy/action: minimal custom role (that single action,
#              assignable only in the resource group) assigned to you on the Key Vault. Never to GitHub.
#   KeyVault   U10 redeploy with keyVaultArmSecretAccess=true; what-if must show ONLY the Key Vault, and only
#              enabledForTemplateDeployment and networkAcls.bypass. publicNetworkAccess stays Disabled.
#   Secrets    generates the two PostgreSQL passwords in the Key Vault if they do not exist yet (never printed,
#              never written to disk except a temporary request body that is deleted at once).
#   Core       ACR Basic, PostgreSQL 16 B1ms, Container Apps environment (Consumption), runtime identity and the
#              minimum roles of the GitHub identity. validate -> what-if (checked automatically) -> DESPLEGAR.
#   Apps       api, frontend and the bootstrap job with -ImageTag (pushed by GitHub Actions); then Firewall.
#   Firewall   PostgreSQL rules = the current outbound IPs of Container Apps (never 0.0.0.0); stale rules removed.
#   Bootstrap  starts the manual job (dataset -> migrate -> ingest -> forecast -> recommend) and waits for it.
#   Verify     checks and evidence (identifiers only) in tmp/u12-evidence/.
#   Stop/Start stops or starts the PostgreSQL server (cost control); the apps already scale to zero.
#   -SelfTest  offline checks of this script (no Azure call).
# It never asks for, stores or prints a password, token or connection string. ASCII only (Windows PowerShell 5.1).

[CmdletBinding()]
param(
    [ValidateSet('Preflight', 'KeyVaultRole', 'KeyVault', 'Secrets', 'Core', 'Apps', 'Firewall', 'Bootstrap', 'Verify', 'Stop', 'Start')]
    [string]$Stage = 'Preflight',
    [string]$ImageTag = '',
    [switch]$Yes,
    [switch]$SelfTest,
    [switch]$PreflightOnly
)

$ErrorActionPreference = 'Stop'
if ($PreflightOnly) {
    if ($PSBoundParameters.ContainsKey('Stage') -and $Stage -ne 'Preflight') { Write-Host "-PreflightOnly no se combina con -Stage $Stage" -ForegroundColor Red; exit 2 }
    $Stage = 'Preflight'
}
# The preflight is read-only by construction: Invoke-Az refuses anything outside Test-ReadOnlyAz while this is set.
$script:ReadOnly = ($Stage -eq 'Preflight' -and -not $SelfTest)
if ($PSVersionTable.PSVersion.Major -lt 6) { Remove-TypeData -TypeName System.Array -ErrorAction SilentlyContinue }

$ResourceGroup = 'rg-motor-predictivo-dev'
$Location = 'centralus'
$ExpectedTenant = '6ce4b1ba-ae4f-4887-bd6b-acb3c72039ad'
$U10Template = 'infra/azure/main.bicep'
$U10Parameters = 'infra/azure/parameters/dev.bicepparam'
$U10DeploymentName = 'u10-base-dev'
$U12Template = 'infra/azure/u12/main.bicep'
$U12DeploymentName = 'u12-dev'
$EntraSpec = 'infra/azure/entra/u11-entra.dev.json'
$EvidenceDir = 'tmp/u12-evidence'
$SecretNames = @('pg-owner-password', 'pg-app-password')
$KeyVaultApi = '2024-11-01'
# getSecret in a Bicep/ARM deployment needs this action on the vault (Microsoft Learn, "Use Azure Key Vault to pass
# a secure parameter value during deployment"). Only the person who deploys the infrastructure needs it.
$DeployAction = 'Microsoft.KeyVault/vaults/deploy/action'
$DeployRoleName = 'Key Vault Resource Manager Template Deployment Operator'
# OIDC subject of id-mpa-dev-github (U10, DT-098): GitHub's immutable format with owner and repository ids.
$ExpectedGithubSubject = 'repo:daniel02vazquez97-alt@290574726/G19X-ITH-DVT-209-ACADEMIC@1408075880:environment:dev'
$GithubAllowedRoles = @('Reader', 'Container Apps Contributor', 'AcrPush', 'Managed Identity Operator')
# Built-in roles (Microsoft Learn, "Azure built-in roles"); the two Container Apps / identity ones are resolved by
# name at run time and must exist with exactly that name.
$AcrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'
$AcrPushRoleId = '8311e382-0749-4cb8-b61a-304f252e45ec'
$ReaderRoleId = 'acdd72a7-3385-48ef-bd42-f606fba81ae7'
$NamedRoles = [ordered]@{ containerAppsContributorRoleId = 'Container Apps Contributor'; managedIdentityOperatorRoleId = 'Managed Identity Operator' }
$AllowedTypes = @(
    'Microsoft.ManagedIdentity/userAssignedIdentities', 'Microsoft.Authorization/roleAssignments',
    'Microsoft.ContainerRegistry/registries', 'Microsoft.DBforPostgreSQL/flexibleServers',
    'Microsoft.DBforPostgreSQL/flexibleServers/databases', 'Microsoft.DBforPostgreSQL/flexibleServers/configurations',
    'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules', 'Microsoft.App/managedEnvironments',
    'Microsoft.App/containerApps', 'Microsoft.App/jobs')

function Step([string]$Text) { Write-Host ''; Write-Host "== $Text" -ForegroundColor Cyan }
function Stop-U12([string]$Text) {
    Write-Host ''; Write-Host "DETENIDO: $Text" -ForegroundColor Red
    if ($script:ReadOnly) { Write-Host ''; Write-Host '== 12. Resultado' -ForegroundColor Cyan; Write-Host 'PREFLIGHT BLOQUEADO' -ForegroundColor Red }
    exit 1
}

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
        if ($element -is [System.Array]) { foreach ($inner in $element) { if ($null -ne $inner) { $items.Add($inner) } } }
        else { $items.Add($element) }
    }
    return ,$items.ToArray()
}

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

# Runs az; -Array: flat array of a JSON list; -Raw: text. Output is printed only on failure, and no command used
# here returns a secret value (Key Vault values are written, never read).
function Invoke-Az {
    param([string[]]$Arguments, [switch]$Raw, [switch]$Array, [string]$What = 'az', [switch]$AllowFailure)
    if ($script:ReadOnly -and -not (Test-ReadOnlyAz $Arguments)) { Stop-U12 ("comando no permitido en modo solo lectura: az " + (($Arguments | Select-Object -First 3) -join ' ')) }
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $output = & az @Arguments 2>&1
    $code = $LASTEXITCODE
    $ErrorActionPreference = $previous
    if ($code -ne 0) {
        if ($AllowFailure) { return $null }
        Write-Host (($output | ForEach-Object { "$_" }) -join "`n")
        Stop-U12 "$What fallo (codigo $code)"
    }
    $text = ($output | ForEach-Object { "$_" }) -join "`n"
    if ($Raw) { return $text }
    $json = ($output | Where-Object { $_ -isnot [System.Management.Automation.ErrorRecord] } | ForEach-Object { "$_" }) -join "`n"
    if ($Array) { return ,(ConvertFrom-AzJsonArray $json) }
    if ([string]::IsNullOrWhiteSpace($json)) { return $null }
    return (ConvertFrom-Json -InputObject $json)
}

function Save-Evidence([string]$Name, $Object) {
    Protect-Evidence $Object
    New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null
    Set-Content -Path (Join-Path $EvidenceDir $Name) -Value (ConvertTo-Json -InputObject $Object -Depth 20) -Encoding ASCII
}

function Confirm-Or-Stop([string]$Word, [string]$Prompt) {
    if ($Yes) { return }
    $answer = Read-Host "Escribe $Word para $Prompt"
    if ($answer -cne $Word) { Stop-U12 'cancelado por el responsable' }
}

# ---------------------------------------------------------------------------------------------------------
# Pure functions (exercised by -SelfTest without Azure).

# 32 characters from [A-Za-z0-9] with at least one of each class: valid for PostgreSQL Flexible Server, URL-safe,
# from the OS cryptographic generator. The value is only ever handed to az through a temporary request file.
function New-DbPassword {
    $alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        do {
            $bytes = New-Object byte[] 64
            $rng.GetBytes($bytes)
            $chars = New-Object System.Text.StringBuilder
            foreach ($b in $bytes) {
                if ($b -ge (256 - (256 % $alphabet.Length))) { continue }  # no modulo bias
                [void]$chars.Append($alphabet[$b % $alphabet.Length])
                if ($chars.Length -eq 32) { break }
            }
            $candidate = $chars.ToString()
        } while ($candidate.Length -ne 32 -or $candidate -cnotmatch '[A-Z]' -or $candidate -cnotmatch '[a-z]' -or $candidate -notmatch '[0-9]')
        return $candidate
    } finally { $rng.Dispose() }
}

# Leaf property paths of a what-if delta tree ("properties.networkAcls.bypass").
function Get-LeafPaths($Delta, [string]$Prefix = '') {
    $paths = New-Object System.Collections.Generic.List[string]
    foreach ($d in (As-Array $Delta)) {
        $path = "$(Get-Prop $d 'path')"
        $full = $path
        if ($Prefix) { $full = "$Prefix.$path" }
        $children = As-Array (Get-Prop $d 'children')
        if ($children.Count -eq 0) { $paths.Add($full) } else { foreach ($p in (Get-LeafPaths $children $full)) { $paths.Add($p) } }
    }
    return ,$paths.ToArray()
}

function Get-ChangeType($Change) {
    $after = Get-Prop $Change 'after'
    $before = Get-Prop $Change 'before'
    if ($after) { return "$(Get-Prop $after 'type')" }
    if ($before) { return "$(Get-Prop $before 'type')" }
    return ''
}

# KeyVault stage: only the vault may change, and only the two properties of DT-100.
function Get-LeafChanges($Delta) {
    $leaves = New-Object System.Collections.Generic.List[object]
    foreach ($d in (As-Array $Delta)) {
        $children = As-Array (Get-Prop $d 'children')
        if ($children.Count -eq 0) { $leaves.Add($d) } else { foreach ($l in (Get-LeafChanges $children)) { $leaves.Add($l) } }
    }
    return ,$leaves.ToArray()
}

# Known what-if noise on U10's Reader assignment: what-if cannot evaluate reference(<identity>).principalId, so it
# shows the unchanged principal as a Modify (plus principalType as NoEffect). Accepted ONLY when the assignment keeps
# the Reader role, every other leaf is NoEffect, the expression points at id-mpa-dev-github and the current principal
# is exactly that identity's principalId (read with az identity show). Role assignments cannot change principal anyway.
function Test-ReaderReferenceNoise($Change, [string]$GithubPrincipalId) {
    if (-not $GithubPrincipalId -or (Get-ChangeType $Change) -ne 'Microsoft.Authorization/roleAssignments') { return $false }
    $beforeRole = "$(Get-Prop (Get-Prop (Get-Prop $Change 'before') 'properties') 'roleDefinitionId')"
    $afterRole = "$(Get-Prop (Get-Prop (Get-Prop $Change 'after') 'properties') 'roleDefinitionId')"
    if ($beforeRole -ne $afterRole -or -not $afterRole.EndsWith('/acdd72a7-3385-48ef-bd42-f606fba81ae7')) { return $false }
    $leaves = Get-LeafChanges (Get-Prop $Change 'delta')
    if ($leaves.Count -eq 0) { return $false }
    foreach ($l in $leaves) {
        if ("$(Get-Prop $l 'propertyChangeType')" -eq 'NoEffect') { continue }
        $isPrincipal = "$(Get-Prop $l 'path')" -eq 'properties.principalId'
        $isReference = "$(Get-Prop $l 'after')" -match "^\[reference\('/subscriptions/[^']+/resourceGroups/[^']+/providers/Microsoft\.ManagedIdentity/userAssignedIdentities/id-mpa-dev-github', '[0-9-]+'\)\.principalId\]$"
        if (-not ($isPrincipal -and $isReference -and "$(Get-Prop $l 'before')" -eq $GithubPrincipalId)) { return $false }
    }
    return $true
}

# True while the what-if still modifies the Key Vault (option C not applied yet).
function Test-KeyVaultPending($WhatIf) {
    $kvChanges = @((As-Array (Get-Prop $WhatIf 'changes')) | Where-Object { "$(Get-Prop $_ 'changeType')" -eq 'Modify' -and (Get-ChangeType $_) -eq 'Microsoft.KeyVault/vaults' })
    return ($kvChanges.Count -gt 0)
}

function Test-KeyVaultWhatIf($WhatIf, [string]$GithubPrincipalId = '') {
    $problems = New-Object System.Collections.Generic.List[string]
    $allowedPaths = @('properties.enabledForTemplateDeployment', 'properties.networkAcls.bypass')
    $modified = 0
    foreach ($c in (As-Array (Get-Prop $WhatIf 'changes'))) {
        $kind = "$(Get-Prop $c 'changeType')"
        if ($kind -in @('NoChange', 'Ignore')) { continue }
        $type = Get-ChangeType $c
        if ($kind -eq 'Modify' -and (Test-ReaderReferenceNoise $c $GithubPrincipalId)) { continue }
        if ($kind -ne 'Modify' -or $type -ne 'Microsoft.KeyVault/vaults') { $problems.Add("cambio no permitido: $kind en $(Get-Prop $c 'resourceId')"); continue }
        $modified++
        foreach ($p in (Get-LeafPaths (Get-Prop $c 'delta'))) { if ($p -notin $allowedPaths) { $problems.Add("propiedad del Key Vault no autorizada: $p") } }
        $after = Get-Prop $c 'after'
        if ("$(Get-Prop (Get-Prop $after 'properties') 'publicNetworkAccess')" -ne 'Disabled') { $problems.Add('el Key Vault pasaria a tener acceso publico') }
    }
    if ($modified -gt 1) { $problems.Add('mas de un Key Vault modificado') }
    return ,$problems.ToArray()
}

# Core/Apps stages: only the resource types of U12, inside the resource group, with the agreed SKUs and settings.
function Test-U12WhatIf($WhatIf, [string]$RgId, [string[]]$RoleIds, [bool]$Apps) {
    $problems = New-Object System.Collections.Generic.List[string]
    $seen = @{}
    foreach ($c in (As-Array (Get-Prop $WhatIf 'changes'))) {
        $kind = "$(Get-Prop $c 'changeType')"
        if ($kind -eq 'Ignore') { continue }
        $id = "$(Get-Prop $c 'resourceId')"
        $type = Get-ChangeType $c
        if ($kind -notin @('Create', 'Modify', 'NoChange')) { $problems.Add("cambio no permitido: $kind en $id"); continue }
        if ($type -notin $AllowedTypes) { $problems.Add("recurso inesperado: $type ($id)"); continue }
        if (-not $id.StartsWith($RgId, [System.StringComparison]::OrdinalIgnoreCase)) { $problems.Add("fuera del grupo: $id") }
        if ($id -match '(?i)staging|-prod|openai|cognitive|search|machinelearning|powerbi') { $problems.Add("servicio o entorno no autorizado: $id") }
        $seen[$type] = 1 + [int]$seen[$type]
        $a = Get-Prop $c 'after'
        $p = Get-Prop $a 'properties'
        $loc = "$(Get-Prop $a 'location')"
        if ($loc -and ($loc -replace ' ', '').ToLower() -ne $Location) { $problems.Add("region distinta de ${Location}: $loc ($id)") }
        switch ($type) {
            'Microsoft.ContainerRegistry/registries' {
                if ("$(Get-Prop (Get-Prop $a 'sku') 'name')" -ne 'Basic') { $problems.Add('ACR no es Basic') }
                if ((Get-Prop $p 'adminUserEnabled') -ne $false) { $problems.Add('ACR con usuario administrador') }
            }
            'Microsoft.DBforPostgreSQL/flexibleServers' {
                if ("$(Get-Prop (Get-Prop $a 'sku') 'name')" -ne 'Standard_B1ms') { $problems.Add('PostgreSQL no es B1ms') }
                if ("$(Get-Prop $p 'version')" -ne '16') { $problems.Add('PostgreSQL no es 16') }
                if ("$(Get-Prop (Get-Prop $p 'highAvailability') 'mode')" -notin @('', 'Disabled')) { $problems.Add('PostgreSQL con alta disponibilidad') }
            }
            'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules' {
                $s = "$(Get-Prop $p 'startIpAddress')"; $e = "$(Get-Prop $p 'endIpAddress')"
                if ($s -ne $e -or $s -eq '0.0.0.0' -or $s -notmatch '^\d{1,3}(\.\d{1,3}){3}$') { $problems.Add("regla de firewall no permitida: $s-$e") }
                if (($id -split '/')[-1] -notlike 'aca-out-*') { $problems.Add("regla de firewall ajena a U12: $id") }
            }
            'Microsoft.DBforPostgreSQL/flexibleServers/configurations' {
                if (($id -split '/')[-1] -ne 'require_secure_transport' -or "$(Get-Prop $p 'value')" -ne 'ON') { $problems.Add("configuracion de PostgreSQL inesperada: $id") }
            }
            'Microsoft.App/managedEnvironments' {
                # Express does not run Container Apps Jobs (the bootstrap) nor allowInsecure (2026-10-09, DT-100).
                if ("$(Get-Prop $p 'environmentMode')" -cne 'WorkloadProfiles') { $problems.Add("entorno de Container Apps en modo '$(Get-Prop $p 'environmentMode')': debe ser WorkloadProfiles") }
                foreach ($w in (As-Array (Get-Prop $p 'workloadProfiles'))) { if ("$(Get-Prop $w 'workloadProfileType')" -ne 'Consumption') { $problems.Add('perfil de carga distinto de Consumption') } }
            }
            'Microsoft.App/containerApps' {
                $ingress = Get-Prop (Get-Prop $p 'configuration') 'ingress'
                if ($id -like '*-api') {
                    if ((Get-Prop $ingress 'external') -ne $false) { $problems.Add('la api tendria ingress publico') }
                    if ((Get-Prop $ingress 'allowInsecure') -ne $false) { $problems.Add('la api admitiria HTTP inseguro') }
                }
                elseif ($id -like '*-frontend') {
                    if ((Get-Prop $ingress 'external') -ne $true) { $problems.Add('el frontend sin ingress externo') }
                    if ((Get-Prop $ingress 'allowInsecure') -ne $false) { $problems.Add('el frontend admitiria HTTP inseguro') }
                } else { $problems.Add("app inesperada: $id") }
                foreach ($r in (As-Array (Get-Prop (Get-Prop $p 'configuration') 'registries'))) {
                    if ((Get-Prop $r 'passwordSecretRef') -or -not (Get-Prop $r 'identity')) { $problems.Add("registro con credenciales en $id") }
                }
            }
            'Microsoft.App/jobs' {
                if ("$(Get-Prop (Get-Prop $p 'configuration') 'triggerType')" -ne 'Manual') { $problems.Add('el job no es Manual') }
            }
            'Microsoft.Authorization/roleAssignments' {
                $rd = "$(Get-Prop $p 'roleDefinitionId')"
                if (-not @($RoleIds | Where-Object { $rd.EndsWith($_) }).Count) { $problems.Add("rol no autorizado: $rd") }
            }
        }
    }
    $expected = @('Microsoft.ContainerRegistry/registries', 'Microsoft.DBforPostgreSQL/flexibleServers', 'Microsoft.App/managedEnvironments', 'Microsoft.ManagedIdentity/userAssignedIdentities')
    if ($Apps) { $expected += @('Microsoft.App/containerApps', 'Microsoft.App/jobs') }
    foreach ($t in $expected) { if (-not $seen.ContainsKey($t)) { $problems.Add("falta el recurso esperado: $t") } }
    if ([int]$seen['Microsoft.Authorization/roleAssignments'] -ne 4) { $problems.Add("se esperaban 4 asignaciones de rol y hay $([int]$seen['Microsoft.Authorization/roleAssignments'])") }
    if ($Apps -and [int]$seen['Microsoft.App/containerApps'] -ne 2) { $problems.Add('se esperaban exactamente dos apps') }
    return ,$problems.ToArray()
}

function Test-SameList($A, $B) {
    $x = @((As-Array $A) | ForEach-Object { "$_" } | Sort-Object)
    $y = @((As-Array $B) | ForEach-Object { "$_" } | Sort-Object)
    return (($x -join '|') -ceq ($y -join '|'))
}

# Firewall rules of U12 that no longer match an outbound IP.
function Get-StaleRules([string[]]$RuleNames, [string[]]$Ips) {
    $wanted = @($Ips | ForEach-Object { 'aca-out-' + ($_ -replace '\.', '-') })
    return ,@($RuleNames | Where-Object { $_ -like 'aca-out-*' -and $_ -notin $wanted })
}

# Adds the frontend URL to spa.redirectUris of the U11 desired state (text edit: the file keeps its layout).
# Read-only allow list for -PreflightOnly: these az commands only read (or compile Bicep locally to stdout).
function Test-ReadOnlyAz([string[]]$Arguments) {
    $a = @($Arguments | ForEach-Object { "$_".ToLowerInvariant() })
    if ($a.Count -lt 2) { return $false }
    $two = $a[0] + ' ' + $a[1]
    $three = if ($a.Count -ge 3) { $two + ' ' + $a[2] } else { $two }
    if ($a -contains '--body' -or $a -contains '--set' -or $a -contains '--yes') { return $false }
    if ($two -in @('account show', 'group exists', 'group show', 'provider show', 'resource list', 'resource show')) { return $true }
    if ($three -in @('role assignment list', 'role definition list', 'ad signed-in-user show', 'identity federated-credential list')) { return $true }
    if ($two -eq 'identity show') { return $true }
    if ($two -eq 'bicep build') { return ($a -contains '--stdout') }  # never writes main.json
    if ($two -in @('bicep build-params')) { return ($a -contains '--stdout') }
    if ($two -in @('bicep lint', 'bicep version')) { return $true }
    if ($a[0] -eq 'rest') {
        $i = [array]::IndexOf($a, '--method')
        return ($i -ge 0 -and $i + 1 -lt $a.Count -and $a[$i + 1] -eq 'get')
    }
    return $false
}

# Does any of these role definitions grant $Action? Azure RBAC wildcards; NotActions of the same block subtract.
function Test-ActionAllowed($Definitions, [string]$Action) {
    foreach ($d in (As-Array $Definitions)) {
        foreach ($perm in (As-Array (Get-Prop $d 'permissions'))) {
            $grant = @((As-Array (Get-Prop $perm 'actions')) | Where-Object { $Action -like "$_" }).Count
            $deny = @((As-Array (Get-Prop $perm 'notActions')) | Where-Object { $Action -like "$_" }).Count
            if ($grant -gt 0 -and $deny -eq 0) { return $true }
        }
    }
    return $false
}

# Does a role assignment at $Scope reach $ResourceId (the resource itself, a parent scope or a management group)?
function Test-ScopeCovers([string]$Scope, [string]$ResourceId) {
    if ($Scope -match '(?i)^/providers/Microsoft\.Management/managementGroups/') { return $true }
    $s = $Scope.TrimEnd('/')
    if ($s -eq '') { return $true }
    return ($ResourceId.Equals($s, [System.StringComparison]::OrdinalIgnoreCase) -or
            $ResourceId.StartsWith($s + '/', [System.StringComparison]::OrdinalIgnoreCase))
}

# Evidence files never keep a secret value, whatever az returns: values inside any `secrets` list, values of
# variables whose name looks like a password, and properties named like a password or connection string.
function Test-SecretKey([string]$Key, [bool]$InSecrets, $Value) {
    if ($Value -isnot [string] -or $Value -eq '' -or $Value -eq '<redactado>') { return $false }
    if ($InSecrets -and $Key -eq 'value') { return $true }
    return ($Key -match '(?i)(password|connectionstring|clientsecret|accesstoken)$')
}
function Protect-Evidence($Node, [bool]$InSecrets = $false) {
    if ($null -eq $Node -or $Node -is [string] -or $Node -is [System.ValueType]) { return }
    if ($Node -is [System.Collections.IDictionary]) {
        $named = "$($Node['name'])" -match '(?i)password|secret'
        foreach ($k in @($Node.Keys)) {
            $v = $Node[$k]
            if ((Test-SecretKey "$k" ($InSecrets -or $named) $v)) { $Node[$k] = '<redactado>' } else { Protect-Evidence $v ("$k" -eq 'secrets') }
        }
    } elseif ($Node -is [System.Management.Automation.PSCustomObject]) {
        $nameProp = $Node.PSObject.Properties['name']
        $named = ($null -ne $nameProp) -and ("$($nameProp.Value)" -match '(?i)password|secret')
        foreach ($p in @($Node.PSObject.Properties)) {
            if ((Test-SecretKey $p.Name ($InSecrets -or $named) $p.Value)) { $p.Value = '<redactado>' } else { Protect-Evidence $p.Value ($p.Name -eq 'secrets') }
        }
    } elseif ($Node -is [System.Collections.IEnumerable]) {
        foreach ($item in $Node) { Protect-Evidence $item $InSecrets }
    }
}

function Add-RedirectUri([string]$Text, [string]$Uri) {
    if ($Uri -notmatch '^https://[a-z0-9.-]+\.azurecontainerapps\.io$') { throw "URL de frontend inesperada: $Uri" }
    if ($Text.Contains('"' + $Uri + '"')) { return $Text }
    $pattern = '("redirectUris":\s*\[)([^\]]*)(\])'
    $m = [regex]::Match($Text, $pattern)
    if (-not $m.Success) { throw 'no se encontro spa.redirectUris en el estado deseado de U11' }
    # A recreated environment gets a new default domain: the previous Container Apps URI is replaced, never kept.
    $inner = ($m.Groups[2].Value -replace ',\s*"https://[a-z0-9.-]+\.azurecontainerapps\.io"', '').TrimEnd()
    $replacement = $m.Groups[1].Value + $inner + ', "' + $Uri + '"' + $m.Groups[3].Value
    return $Text.Substring(0, $m.Index) + $replacement + $Text.Substring($m.Index + $m.Length)
}

function Resolve-RoleIds {
    $ids = [ordered]@{}
    foreach ($k in $NamedRoles.Keys) {
        $found = Invoke-Az @('role', 'definition', 'list', '--name', $NamedRoles[$k], '--query', '[].{name:name, roleName:roleName, roleType:roleType}', '--output', 'json') -Array -What "az role definition list ($($NamedRoles[$k]))"
        $builtIn = @($found | Where-Object { $_.roleType -eq 'BuiltInRole' -and $_.roleName -eq $NamedRoles[$k] })
        if ($builtIn.Count -ne 1) { Stop-U12 "no se encontro el rol integrado '$($NamedRoles[$k])'" }
        $ids[$k] = $builtIn[0].name
        Write-Host ("Rol {0}: {1}" -f $NamedRoles[$k], $builtIn[0].name)
    }
    return $ids
}

# Role assignments that reach $TargetId for a principal (direct, inherited and through groups) and their definitions.
function Get-RoleDefinitionsAt([string]$PrincipalId, [string]$TargetId) {
    $assignments = Invoke-Az @('role', 'assignment', 'list', '--assignee', $PrincipalId, '--scope', $TargetId, '--include-inherited', '--include-groups', '--output', 'json') -Array -What 'az role assignment list'
    $relevant = @($assignments | Where-Object { Test-ScopeCovers "$($_.scope)" $TargetId })
    $definitions = New-Object System.Collections.Generic.List[object]
    foreach ($rid in @($relevant | ForEach-Object { ("$($_.roleDefinitionId)" -split '/')[-1] } | Sort-Object -Unique)) {
        $found = Invoke-Az @('role', 'definition', 'list', '--name', $rid, '--output', 'json') -Array -What "az role definition list $rid"
        foreach ($f in $found) { $definitions.Add($f) }
    }
    return [ordered]@{ assignments = $relevant; definitions = $definitions.ToArray() }
}

function Get-SignedInUserId {
    $id = (Invoke-Az @('ad', 'signed-in-user', 'show', '--query', 'id', '--output', 'tsv') -Raw -What 'az ad signed-in-user show').Trim()
    if ($id -notmatch '^[0-9a-fA-F-]{36}$') { Stop-U12 'no se pudo leer el identificador de tu usuario' }
    return $id
}

if ($SelfTest) {
    $script:failed = 0
    function Check([string]$Name, [bool]$Ok) {
        if (-not $Ok) { $script:failed++ }
        Write-Host ("{0}  {1}" -f ($(if ($Ok) { 'OK  ' } else { 'FAIL' })), $Name)
    }
    $pw = @(1..20 | ForEach-Object { New-DbPassword })
    Check 'contrasenas: 32 caracteres alfanumericos con mayuscula, minuscula y digito' (@($pw | Where-Object { $_ -cmatch '^[A-Za-z0-9]{32}$' -and $_ -cmatch '[A-Z]' -and $_ -cmatch '[a-z]' -and $_ -match '[0-9]' }).Count -eq 20)
    Check 'contrasenas distintas en cada llamada' (@($pw | Sort-Object -Unique).Count -eq 20)
    Check 'lista JSON vacia -> 0 y de uno -> 1' (((ConvertFrom-AzJsonArray '[]').Count -eq 0) -and ((ConvertFrom-AzJsonArray '[{"a":1}]').Count -eq 1))
    $rg = '/subscriptions/s/resourceGroups/rg-motor-predictivo-dev'
    $roles = @($AcrPullRoleId, $AcrPushRoleId, 'cac0', 'mio0')
    function Ch($kind, $type, $name, $after) {
        $a = [ordered]@{ type = $type; location = 'centralus' }
        foreach ($k in $after.Keys) { $a[$k] = $after[$k] }
        return [ordered]@{ changeType = $kind; resourceId = "$rg/providers/$type/$name"; after = $a }
    }
    $role = { param($id) Ch 'Create' 'Microsoft.Authorization/roleAssignments' (New-Guid) @{ properties = @{ roleDefinitionId = "/x/roleDefinitions/$id" } } }
    $core = @(
        (Ch 'Create' 'Microsoft.ContainerRegistry/registries' 'acrmpadevx' @{ sku = @{ name = 'Basic' }; properties = @{ adminUserEnabled = $false } }),
        (Ch 'Create' 'Microsoft.DBforPostgreSQL/flexibleServers' 'psql-mpa-dev-x' @{ sku = @{ name = 'Standard_B1ms' }; properties = @{ version = '16'; highAvailability = @{ mode = 'Disabled' } } }),
        (Ch 'Create' 'Microsoft.DBforPostgreSQL/flexibleServers/databases' 'psql-mpa-dev-x/inventory' @{}),
        (Ch 'Create' 'Microsoft.DBforPostgreSQL/flexibleServers/configurations' 'psql-mpa-dev-x/require_secure_transport' @{ properties = @{ value = 'ON' } }),
        (Ch 'Create' 'Microsoft.App/managedEnvironments' 'cae-mpa-dev' @{ properties = @{ environmentMode = 'WorkloadProfiles'; workloadProfiles = @(@{ workloadProfileType = 'Consumption' }) } }),
        (Ch 'Create' 'Microsoft.ManagedIdentity/userAssignedIdentities' 'id-mpa-dev-runtime' @{}),
        (& $role $AcrPullRoleId), (& $role $AcrPushRoleId), (& $role 'cac0'), (& $role 'mio0'),
        [ordered]@{ changeType = 'Ignore'; resourceId = "$rg/providers/Microsoft.KeyVault/vaults/kv" })
    $roundTrip = { param($changes) ConvertFrom-Json -InputObject (ConvertTo-Json -InputObject ([ordered]@{ changes = $changes }) -Depth 20) }
    Check 'what-if de core conforme' ((Test-U12WhatIf (& $roundTrip $core) $rg $roles $false).Count -eq 0)
    $apps = $core + @(
        (Ch 'Create' 'Microsoft.App/containerApps' 'ca-mpa-dev-api' @{ properties = @{ configuration = @{ ingress = @{ external = $false; allowInsecure = $false }; registries = @(@{ identity = 'id' }) } } }),
        (Ch 'Create' 'Microsoft.App/containerApps' 'ca-mpa-dev-frontend' @{ properties = @{ configuration = @{ ingress = @{ external = $true; allowInsecure = $false }; registries = @(@{ identity = 'id' }) } } }),
        (Ch 'Create' 'Microsoft.App/jobs' 'caj-mpa-dev-bootstrap' @{ properties = @{ configuration = @{ triggerType = 'Manual' } } }),
        (Ch 'Create' 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules' 'psql-mpa-dev-x/aca-out-20-1-2-3' @{ properties = @{ startIpAddress = '20.1.2.3'; endIpAddress = '20.1.2.3' } }))
    Check 'what-if de apps conforme' ((Test-U12WhatIf (& $roundTrip $apps) $rg $roles $true).Count -eq 0)
    $bad = [ordered]@{
        'ACR Premium'          = (Ch 'Create' 'Microsoft.ContainerRegistry/registries' 'acr2' @{ sku = @{ name = 'Premium' }; properties = @{ adminUserEnabled = $false } })
        'ACR admin'            = (Ch 'Create' 'Microsoft.ContainerRegistry/registries' 'acr3' @{ sku = @{ name = 'Basic' }; properties = @{ adminUserEnabled = $true } })
        'regla 0.0.0.0'        = (Ch 'Create' 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules' 'psql/aca-out-0' @{ properties = @{ startIpAddress = '0.0.0.0'; endIpAddress = '0.0.0.0' } })
        'rango amplio'         = (Ch 'Create' 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules' 'psql/aca-out-r' @{ properties = @{ startIpAddress = '1.0.0.0'; endIpAddress = '1.255.255.255' } })
        'api publica'          = (Ch 'Modify' 'Microsoft.App/containerApps' 'ca-mpa-dev-api' @{ properties = @{ configuration = @{ ingress = @{ external = $true; allowInsecure = $false } } } })
        'api HTTP'             = (Ch 'Modify' 'Microsoft.App/containerApps' 'ca-mpa-dev-api' @{ properties = @{ configuration = @{ ingress = @{ external = $false; allowInsecure = $true } } } })
        'entorno Express'      = (Ch 'Modify' 'Microsoft.App/managedEnvironments' 'cae-mpa-dev' @{ properties = @{ environmentMode = 'Express'; workloadProfiles = @(@{ workloadProfileType = 'Consumption' }) } })
        'entorno sin modo'     = (Ch 'Modify' 'Microsoft.App/managedEnvironments' 'cae-mpa-dev' @{ properties = @{ workloadProfiles = @(@{ workloadProfileType = 'Consumption' }) } })
        'frontend HTTP'        = (Ch 'Modify' 'Microsoft.App/containerApps' 'ca-mpa-dev-frontend' @{ properties = @{ configuration = @{ ingress = @{ external = $true; allowInsecure = $true } } } })
        'registro con clave'   = (Ch 'Modify' 'Microsoft.App/containerApps' 'ca-mpa-dev-api' @{ properties = @{ configuration = @{ ingress = @{ external = $false }; registries = @(@{ passwordSecretRef = 'p'; username = 'u' }) } } })
        'Owner'                = (& $role '8e3af657-a8ff-443c-a75c-2fe8c4bcb635')
        'borrado'              = [ordered]@{ changeType = 'Delete'; resourceId = "$rg/providers/Microsoft.App/containerApps/x"; before = @{ type = 'Microsoft.App/containerApps' } }
        'Azure OpenAI'         = (Ch 'Create' 'Microsoft.CognitiveServices/accounts' 'openai' @{})
        'otra region'          = [ordered]@{ changeType = 'Create'; resourceId = "$rg/providers/Microsoft.App/managedEnvironments/e2"; after = @{ type = 'Microsoft.App/managedEnvironments'; location = 'eastus' } }
        'fuera del grupo'      = [ordered]@{ changeType = 'Create'; resourceId = '/subscriptions/s/resourceGroups/otro/providers/Microsoft.App/jobs/j'; after = @{ type = 'Microsoft.App/jobs'; location = 'centralus'; properties = @{ configuration = @{ triggerType = 'Manual' } } } }
        'job programado'       = (Ch 'Create' 'Microsoft.App/jobs' 'caj-2' @{ properties = @{ configuration = @{ triggerType = 'Schedule' } } })
        'PostgreSQL grande'    = (Ch 'Modify' 'Microsoft.DBforPostgreSQL/flexibleServers' 'psql-mpa-dev-x' @{ sku = @{ name = 'Standard_D4s_v3' }; properties = @{ version = '16' } })
        'PostgreSQL HA'        = (Ch 'Modify' 'Microsoft.DBforPostgreSQL/flexibleServers' 'psql-mpa-dev-x' @{ sku = @{ name = 'Standard_B1ms' }; properties = @{ version = '16'; highAvailability = @{ mode = 'ZoneRedundant' } } })
    }
    foreach ($name in $bad.Keys) {
        Check "what-if rechazado: $name" ((Test-U12WhatIf (& $roundTrip ($apps + @($bad[$name]))) $rg $roles $true).Count -gt 0)
    }
    $kvOk = ConvertFrom-Json -InputObject '{"changes":[{"changeType":"NoChange","resourceId":"/rg"},{"changeType":"Modify","resourceId":"/rg/kv","after":{"type":"Microsoft.KeyVault/vaults","properties":{"publicNetworkAccess":"Disabled"}},"delta":[{"path":"properties","propertyChangeType":"Modify","children":[{"path":"enabledForTemplateDeployment","propertyChangeType":"Modify","before":false,"after":true},{"path":"networkAcls","propertyChangeType":"Modify","children":[{"path":"bypass","propertyChangeType":"Modify","before":"None","after":"AzureServices"}]}]}]}]}'
    Check 'what-if del Key Vault conforme (solo dos propiedades)' ((Test-KeyVaultWhatIf $kvOk).Count -eq 0)
    $kvPublic = ConvertFrom-Json -InputObject '{"changes":[{"changeType":"Modify","resourceId":"/rg/kv","after":{"type":"Microsoft.KeyVault/vaults","properties":{"publicNetworkAccess":"Enabled"}},"delta":[{"path":"properties.publicNetworkAccess","propertyChangeType":"Modify"}]}]}'
    Check 'what-if del Key Vault con red publica -> rechazado' ((Test-KeyVaultWhatIf $kvPublic).Count -gt 0)
    $kvOther = ConvertFrom-Json -InputObject '{"changes":[{"changeType":"Modify","resourceId":"/rg/id","after":{"type":"Microsoft.ManagedIdentity/userAssignedIdentities"},"delta":[]}]}'
    Check 'what-if de U10 que toca otra cosa -> rechazado' ((Test-KeyVaultWhatIf $kvOther).Count -gt 0)
    $ref = "[reference('/subscriptions/s/resourceGroups/rg-motor-predictivo-dev/providers/Microsoft.ManagedIdentity/userAssignedIdentities/id-mpa-dev-github', '2023-01-31').principalId]"
    $reader = '/subscriptions/s/providers/Microsoft.Authorization/roleDefinitions/acdd72a7-3385-48ef-bd42-f606fba81ae7'
    $noise = { param($beforeId, $afterRef, $beforeRole, $afterRole, $extra)
        $delta = @([ordered]@{ path = 'properties.principalId'; propertyChangeType = 'Modify'; before = $beforeId; after = $afterRef },
                   [ordered]@{ path = 'properties.principalType'; propertyChangeType = 'NoEffect'; before = $null; after = 'ServicePrincipal' }) + $extra
        [ordered]@{ changeType = 'Modify'; resourceId = '/rg/providers/Microsoft.Authorization/roleAssignments/d55c'
            before = [ordered]@{ type = 'Microsoft.Authorization/roleAssignments'; properties = [ordered]@{ principalId = $beforeId; roleDefinitionId = $beforeRole } }
            after = [ordered]@{ type = 'Microsoft.Authorization/roleAssignments'; properties = [ordered]@{ principalId = $afterRef; roleDefinitionId = $afterRole } }
            delta = $delta } }
    $kvChange = (ConvertFrom-Json -InputObject (ConvertTo-Json -InputObject $kvOk -Depth 20)).changes
    $withNoise = { param($n) ConvertFrom-Json -InputObject (ConvertTo-Json -InputObject ([ordered]@{ changes = @($kvChange) + @($n) }) -Depth 20) }
    Check 'what-if de U10: ruido de reference() en el Reader de GitHub aceptado (mismo principal)' ((Test-KeyVaultWhatIf (& $withNoise (& $noise 'p-gh' $ref $reader $reader @())) 'p-gh').Count -eq 0)
    Check 'Key Vault pendiente: un Modify del vault junto al ruido del Reader -> se aplica (no ALREADY_CONFIGURED)' (Test-KeyVaultPending (& $withNoise (& $noise 'p-gh' $ref $reader $reader @())))
    $onlyNoise = ConvertFrom-Json -InputObject (ConvertTo-Json -InputObject ([ordered]@{ changes = @((& $noise 'p-gh' $ref $reader $reader @())) }) -Depth 20)
    Check 'Key Vault ya configurado: solo el ruido del Reader -> ALREADY_CONFIGURED' (-not (Test-KeyVaultPending $onlyNoise))
    Check 'Key Vault pendiente: un solo cambio en la lista tambien cuenta' (Test-KeyVaultPending (ConvertFrom-Json -InputObject (ConvertTo-Json -InputObject ([ordered]@{ changes = @($kvChange) }) -Depth 20)))
    Check 'ruido de reference(): sin principal conocido -> rechazado' ((Test-KeyVaultWhatIf (& $withNoise (& $noise 'p-gh' $ref $reader $reader @())) '').Count -gt 0)
    Check 'ruido de reference(): otro principal antes -> rechazado' ((Test-KeyVaultWhatIf (& $withNoise (& $noise 'p-otro' $ref $reader $reader @())) 'p-gh').Count -gt 0)
    Check 'ruido de reference(): otra identidad -> rechazado' ((Test-KeyVaultWhatIf (& $withNoise (& $noise 'p-gh' ($ref -replace 'id-mpa-dev-github', 'id-otra') $reader $reader @())) 'p-gh').Count -gt 0)
    Check 'ruido de reference(): cambio de rol -> rechazado' ((Test-KeyVaultWhatIf (& $withNoise (& $noise 'p-gh' $ref $reader ($reader -replace 'acdd72a7', '8e3af657') @())) 'p-gh').Count -gt 0)
    Check 'ruido de reference(): otra propiedad modificada -> rechazado' ((Test-KeyVaultWhatIf (& $withNoise (& $noise 'p-gh' $ref $reader $reader @([ordered]@{ path = 'properties.condition'; propertyChangeType = 'Modify'; before = $null; after = 'x' }))) 'p-gh').Count -gt 0)
    Check 'ruido de reference(): valor literal distinto -> rechazado' ((Test-KeyVaultWhatIf (& $withNoise (& $noise 'p-gh' 'p-nuevo' $reader $reader @())) 'p-gh').Count -gt 0)
    Check 'reglas obsoletas: solo las aca-out-* que ya no son IP de salida' ((Test-SameList (Get-StaleRules @('aca-out-1-2-3-4', 'aca-out-5-6-7-8', 'otra') @('5.6.7.8')) @('aca-out-1-2-3-4')))
    $reads = @(@('account', 'show'), @('group', 'show', '--name', 'g'), @('resource', 'list', '--resource-group', 'g'), @('resource', 'show', '--ids', 'x'),
        @('role', 'assignment', 'list', '--all'), @('role', 'definition', 'list', '--name', 'x'), @('ad', 'signed-in-user', 'show'),
        @('identity', 'show', '--name', 'x'), @('identity', 'federated-credential', 'list', '--identity-name', 'x'), @('provider', 'show', '--namespace', 'x'),
        @('bicep', 'build', '--file', 'm.bicep', '--stdout'), @('bicep', 'build-params', '--file', 'p', '--stdout'), @('bicep', 'lint', '--file', 'm'),
        @('rest', '--method', 'get', '--uri', 'u'))
    Check 'solo lectura: las lecturas del preflight se permiten' (@($reads | Where-Object { -not (Test-ReadOnlyAz $_) }).Count -eq 0)
    $writes = @(@('group', 'create'), @('group', 'delete'), @('deployment', 'group', 'create'), @('deployment', 'sub', 'what-if'), @('role', 'assignment', 'create'),
        @('role', 'definition', 'create'), @('keyvault', 'show'), @('keyvault', 'secret', 'set'), @('postgres', 'flexible-server', 'stop'), @('acr', 'login'),
        @('containerapp', 'update'), @('containerapp', 'show'), @('provider', 'register'), @('rest', '--method', 'put', '--uri', 'u'), @('rest', '--uri', 'u'),
        @('rest', '--method', 'get', '--uri', 'u', '--body', 'b'), @('bicep', 'build', '--file', 'm.bicep'), @('identity', 'federated-credential', 'create'),
        @('resource', 'delete', '--ids', 'x'), @('ad', 'app', 'update'), @('account', 'set'))
    Check 'solo lectura: escrituras, borrados y grupos de comandos no previstos se rechazan' (@($writes | Where-Object { Test-ReadOnlyAz $_ }).Count -eq 0)
    $defs = ConvertFrom-Json -InputObject ('{"owner":[{"roleName":"Owner","permissions":[{"actions":["*"],"notActions":[]}]}],' +
        '"contributor":[{"roleName":"Contributor","permissions":[{"actions":["*"],"notActions":["Microsoft.Authorization/*/Delete","Microsoft.Authorization/*/Write"]}]}],' +
        '"reader":[{"roleName":"Reader","permissions":[{"actions":["*/read"],"notActions":[]}]}],' +
        '"custom":[{"roleName":"KV deploy","permissions":[{"actions":["Microsoft.KeyVault/vaults/deploy/action"],"notActions":[]}]}],' +
        '"capps":[{"roleName":"Container Apps Contributor","permissions":[{"actions":["Microsoft.App/*","Microsoft.Authorization/*/read","Microsoft.Resources/deployments/*"],"notActions":[]}]}],' +
        '"kvdenied":[{"roleName":"x","permissions":[{"actions":["Microsoft.KeyVault/*"],"notActions":["Microsoft.KeyVault/vaults/deploy/action"]}]}]}')
    Check 'deploy/action: Owner, Contributor y el rol minimo la conceden' ((Test-ActionAllowed $defs.owner $DeployAction) -and (Test-ActionAllowed $defs.contributor $DeployAction) -and (Test-ActionAllowed $defs.custom $DeployAction))
    Check 'deploy/action: Reader, Container Apps Contributor y un NotAction no la conceden' (-not (Test-ActionAllowed $defs.reader $DeployAction) -and -not (Test-ActionAllowed $defs.capps $DeployAction) -and -not (Test-ActionAllowed $defs.kvdenied $DeployAction) -and -not (Test-ActionAllowed @() $DeployAction))
    $kvId = '/subscriptions/s/resourceGroups/rg-motor-predictivo-dev/providers/Microsoft.KeyVault/vaults/kv'
    Check 'ambitos: suscripcion, grupo, vault y grupo de administracion alcanzan el vault' ((Test-ScopeCovers '/subscriptions/s' $kvId) -and (Test-ScopeCovers $rg $kvId) -and (Test-ScopeCovers $kvId $kvId) -and (Test-ScopeCovers '/providers/Microsoft.Management/managementGroups/m' $kvId))
    Check 'ambitos: otro grupo o un prefijo parcial no alcanzan el vault' (-not (Test-ScopeCovers '/subscriptions/s/resourceGroups/rg-motor' $kvId) -and -not (Test-ScopeCovers '/subscriptions/s/resourceGroups/otro' $kvId))
    $leak = ConvertFrom-Json -InputObject ('{"changes":[{"after":{"properties":{"administratorLoginPassword":"S3cr3tValueA","passwordAuth":"Enabled",' +
        '"configuration":{"secrets":[{"name":"app-db-password","value":"S3cr3tValueB"}]},' +
        '"template":{"containers":[{"env":[{"name":"PGPASSWORD","value":"S3cr3tValueC"},{"name":"APP_ENV","value":"dev"},{"name":"PGPASSWORD","secretRef":"app-db-password"}]}]}}}}]}')
    Protect-Evidence $leak
    $leakJson = ConvertTo-Json -InputObject $leak -Depth 20
    Check 'evidencia: ningun valor de secreto llega al archivo' ($leakJson -notmatch 'S3cr3tValue' -and $leakJson -match '"dev"' -and $leakJson -match 'app-db-password' -and $leakJson -match 'Enabled')
    $leakDict = [ordered]@{ secrets = @([ordered]@{ name = 'x'; value = 'S3cr3tValueD' }); clientSecret = 'S3cr3tValueE'; keep = 'ok' }
    Protect-Evidence $leakDict
    Check 'evidencia: tambien en diccionarios' (((ConvertTo-Json -InputObject $leakDict -Depth 5) -notmatch 'S3cr3tValue') -and $leakDict.keep -eq 'ok')
    $spec = '{ "spa": { "displayName": "x", "redirectUris": ["http://localhost:5173", "http://localhost:8080"] } }'
    $once = Add-RedirectUri $spec 'https://ca-mpa-dev-frontend.abc.centralus.azurecontainerapps.io'
    Check 'redirect URI anadido una sola vez' ($once.Contains('"http://localhost:8080", "https://ca-mpa-dev-frontend.abc.centralus.azurecontainerapps.io"]') -and ((Add-RedirectUri $once 'https://ca-mpa-dev-frontend.abc.centralus.azurecontainerapps.io') -eq $once))
    $rejected = $false
    try { Add-RedirectUri $spec 'http://evil.example' | Out-Null } catch { $rejected = $true }
    Check 'redirect URI ajeno a Container Apps -> rechazado' $rejected
    $moved = Add-RedirectUri $once 'https://ca-mpa-dev-frontend.xyz.centralus.azurecontainerapps.io'
    Check 'redirect URI de un entorno recreado: sustituye al anterior' ($moved.Contains('"http://localhost:8080", "https://ca-mpa-dev-frontend.xyz.centralus.azurecontainerapps.io"]') -and -not $moved.Contains('abc.centralus'))
    Write-Host ("PowerShell {0}: {1}" -f $PSVersionTable.PSVersion, $(if ($script:failed -eq 0) { 'SELFTEST OK' } else { "SELFTEST FALLO ($($script:failed))" }))
    if ($script:failed -eq 0) { exit 0 } else { exit 1 }
}

# ---------------------------------------------------------------------------------------------------------
# -PreflightOnly / -Stage Preflight: strictly read-only (Test-ReadOnlyAz guards every az call; nothing is written).
$script:Blockers = New-Object System.Collections.Generic.List[string]
$script:Warnings = New-Object System.Collections.Generic.List[string]
function Section([string]$Title) { Write-Host ''; Write-Host "== $Title" -ForegroundColor Cyan }
function Pass([string]$Text) { Write-Host "  OK     $Text" }
function Note([string]$Text) { Write-Host "  INFO   $Text" }
function Warn([string]$Text) { $script:Warnings.Add($Text); Write-Host "  AVISO  $Text" -ForegroundColor Yellow }
function Block([string]$Text) { $script:Blockers.Add($Text); Write-Host "  BLOQUEO $Text" -ForegroundColor Red }
function Expect([bool]$Ok, [string]$Text) { if ($Ok) { Pass $Text } else { Block $Text } }
function Get-Res([string]$Type) {
    $found = Invoke-Az @('resource', 'list', '--resource-group', $ResourceGroup, '--resource-type', $Type, '--output', 'json') -Array -What "resource list $Type"
    return ,@($found)
}
function Show-Res([string]$Id) { return (Invoke-Az @('resource', 'show', '--ids', $Id, '--output', 'json') -What "resource show $Id") }
function Get-Arm([string]$Path, [string]$Api) {
    return (Invoke-Az @('rest', '--method', 'get', '--uri', "https://management.azure.com$($Path)?api-version=$Api", '--output', 'json') -AllowFailure -What "GET $Path")
}
function Test-SourceHas([string]$Path, [string[]]$Needles) {
    if (-not (Test-Path $Path)) { return $false }
    $code = ((Get-Content -Path $Path) | Where-Object { $_.TrimStart() -notmatch '^(//|#|@description)' }) -join "`n"
    foreach ($n in $Needles) { if (-not $code.Contains($n)) { return $false } }
    return $true
}
function Find-Python {
    foreach ($candidate in @(@('python'), @('python3'), @('py', '-3'))) {
        if (-not (Get-Command $candidate[0] -ErrorAction SilentlyContinue)) { continue }
        $exe = $candidate[0]; $pre = @($candidate | Select-Object -Skip 1)
        $previous = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
        $ok = & $exe @pre -c 'import sys; print(sys.version_info >= (3, 9))' 2>$null
        $code = $LASTEXITCODE; $ErrorActionPreference = $previous
        if ($code -eq 0 -and "$ok".Trim() -eq 'True') { return ,@($candidate) }
    }
    return ,@()
}
function Invoke-Python([string[]]$Python, [string[]]$Arguments, [string]$WorkDir) {
    $exe = $Python[0]; $pre = @($Python | Select-Object -Skip 1)
    $previous = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    Push-Location $WorkDir
    try { $output = & $exe @pre @Arguments 2>&1; $code = $LASTEXITCODE } finally { Pop-Location; $ErrorActionPreference = $previous }
    return [ordered]@{ code = $code; text = (($output | ForEach-Object { "$_" }) -join "`n") }
}

function Invoke-Preflight {
    trap { Write-Host ''; Write-Host "DETENIDO: $_" -ForegroundColor Red; Section '12. Resultado'; Write-Host 'PREFLIGHT BLOQUEADO' -ForegroundColor Red; exit 1 }
    $o = [char]0x00F3
    $dash = if ([Console]::OutputEncoding.CodePage -in @(65001, 1200)) { [char]0x2014 } else { '-' }
    Write-Host 'U12 PREFLIGHT (solo lectura: no crea, modifica ni elimina nada en Azure ni en disco)'
    if (-not (Test-Path $U12Template) -or -not (Test-Path $U10Template)) { Stop-U12 'ejecuta el script desde la raiz del repositorio' }

    Section "1. Sesi$($o)n Azure"
    $account = Invoke-Az @('account', 'show', '--output', 'json') -AllowFailure -What 'az account show'
    if ($null -eq $account) { Block 'sin sesion de Azure CLI: ejecuta az login'; Section '12. Resultado'; Write-Host 'PREFLIGHT BLOQUEADO' -ForegroundColor Red; exit 1 }
    Expect ($account.user.type -eq 'user') "sesion de usuario (no de servicio): $($account.user.type)"
    Expect ($account.tenantId -eq $ExpectedTenant) "tenant del proyecto: $($account.tenantId)"

    Section "2. Suscripci$($o)n"
    Note "suscripcion: $($account.name) ($($account.id))"
    Expect ($account.name -match 'Azure for Students') 'oferta Azure for Students'
    Expect ($account.state -eq 'Enabled') "estado: $($account.state)"
    $rgId = "/subscriptions/$($account.id)/resourceGroups/$ResourceGroup"

    Section '3. Resource Group'
    $rg = Invoke-Az @('group', 'show', '--name', $ResourceGroup, '--output', 'json') -AllowFailure -What 'az group show'
    if ($null -eq $rg) { Block "no existe $ResourceGroup (U10)"; Section '12. Resultado'; Write-Host 'PREFLIGHT BLOQUEADO' -ForegroundColor Red; exit 1 }
    Expect ((($rg.location -replace ' ', '').ToLower()) -eq $Location) "$ResourceGroup en $($rg.location)"
    $all = Invoke-Az @('resource', 'list', '--resource-group', $ResourceGroup, '--output', 'json') -Array -What 'az resource list'
    $mine = @($all | Where-Object { $_.type -in $AllowedTypes -or $_.type -eq 'Microsoft.KeyVault/vaults' })
    foreach ($r in $mine) { Note "existe: $($r.type) $($r.name)" }
    $foreign = @($all | Where-Object { $_.type -notin $AllowedTypes -and $_.type -notin @('Microsoft.KeyVault/vaults', 'Microsoft.Insights/actiongroups', 'Microsoft.Consumption/budgets') })
    foreach ($r in $foreign) { Warn "recurso ajeno a U10/U12 en el grupo: $($r.type) $($r.name)" }
    foreach ($r in @($all | Where-Object { $_.name -match '(?i)openai|cognitive|search|machinelearning|powerbi|staging|-prod' })) { Block "servicio futuro o entorno no autorizado en el grupo: $($r.name)" }

    Section '4. Providers'
    foreach ($ns in @('Microsoft.App', 'Microsoft.ContainerRegistry', 'Microsoft.DBforPostgreSQL', 'Microsoft.ManagedIdentity', 'Microsoft.KeyVault')) {
        $state = (Invoke-Az @('provider', 'show', '--namespace', $ns, '--query', 'registrationState', '--output', 'tsv') -Raw -What "provider $ns").Trim()
        if ($state -eq 'Registered') { Pass "${ns}: Registered" } else { Warn "${ns}: $state (antes de Core: az provider register --namespace $ns --wait)" }
    }
    foreach ($pair in @(@('Microsoft.App', 'managedEnvironments'), @('Microsoft.ContainerRegistry', 'registries'), @('Microsoft.DBforPostgreSQL', 'flexibleServers'))) {
        $locs = Invoke-Az @('provider', 'show', '--namespace', $pair[0], '--query', "resourceTypes[?resourceType=='$($pair[1])'].locations | [0]", '--output', 'json') -Array -What "regiones de $($pair[0])"
        Expect (@($locs | Where-Object { ("$_" -replace ' ', '').ToLower() -eq $Location }).Count -gt 0) "$($pair[0])/$($pair[1]) disponible en $Location"
    }
    $roleIds = Resolve-RoleIds

    Section '5. Key Vault'
    $built = Invoke-Az @('bicep', 'build-params', '--file', 'infra/azure/u12/dev.bicepparam', '--stdout') -What 'az bicep build-params (U12)'
    $u12Params = (ConvertFrom-Json -InputObject $built.parametersJson).parameters
    $kvName = "$($u12Params.keyVaultName.value)"
    $kv = Invoke-Az @('resource', 'show', '--resource-group', $ResourceGroup, '--name', $kvName, '--resource-type', 'Microsoft.KeyVault/vaults', '--output', 'json') -AllowFailure -What 'Key Vault de U10'
    if ($null -eq $kv) { Block "no existe el Key Vault $kvName (U10)"; Section '12. Resultado'; Write-Host 'PREFLIGHT BLOQUEADO' -ForegroundColor Red; exit 1 }
    $kvp = $kv.properties
    Expect ("$($kvp.publicNetworkAccess)" -eq 'Disabled') "publicNetworkAccess = $($kvp.publicNetworkAccess) (debe seguir Disabled)"
    Expect ($kvp.enableRbacAuthorization -eq $true) 'autorizacion RBAC'
    Expect ($kvp.enableSoftDelete -ne $false) 'borrado temporal activo'
    $optionC = ($kvp.enabledForTemplateDeployment -eq $true -and "$($kvp.networkAcls.bypass)" -eq 'AzureServices')
    if ($optionC) { Pass 'opcion C ya aplicada: enabledForTemplateDeployment=true, bypass=AzureServices' }
    else { Note ("opcion C pendiente (etapa KeyVault, CAMBIAR-KV): enabledForTemplateDeployment={0}, bypass={1}" -f $kvp.enabledForTemplateDeployment, $kvp.networkAcls.bypass) }

    Section '6. RBAC'
    $me = Get-SignedInUserId
    $myDefs = Get-RoleDefinitionsAt $me $kv.id
    Note ("tu sesion, roles que alcanzan el Key Vault: " + (@($myDefs.definitions | ForEach-Object { $_.roleName } | Sort-Object -Unique) -join ', '))
    $deployAllowed = Test-ActionAllowed $myDefs.definitions $DeployAction
    Write-Host '  KeyVault deploy/action:'
    if ($deployAllowed) { Write-Host '  ALLOWED' -ForegroundColor Green } else { Write-Host '  MISSING' -ForegroundColor Yellow }
    $gh = Invoke-Az @('identity', 'show', '--name', 'id-mpa-dev-github', '--resource-group', $ResourceGroup, '--output', 'json') -AllowFailure -What 'identidad de GitHub'
    if ($null -eq $gh) { Block 'no existe id-mpa-dev-github (U10)' }
    else {
        $fics = Invoke-Az @('identity', 'federated-credential', 'list', '--identity-name', $gh.name, '--resource-group', $ResourceGroup, '--output', 'json') -Array -What 'credenciales federadas'
        Expect ($fics.Count -eq 1 -and "$($fics[0].subject)" -ceq $ExpectedGithubSubject -and "$($fics[0].issuer)" -eq 'https://token.actions.githubusercontent.com' -and ((@($fics[0].audiences) -join ',') -eq 'api://AzureADTokenExchange')) "id-mpa-dev-github: una sola federacion OIDC, sujeto esperado, entorno dev ($(@($fics | ForEach-Object { $_.subject }) -join ', '))"
        $ghAll = Invoke-Az @('role', 'assignment', 'list', '--all', '--assignee', $gh.principalId, '--output', 'json') -Array -What 'roles de GitHub'
        $ghBad = @($ghAll | Where-Object { $_.roleDefinitionName -notin $GithubAllowedRoles -or -not "$($_.scope)".StartsWith($rgId, [System.StringComparison]::OrdinalIgnoreCase) })
        Expect ($ghBad.Count -eq 0) ("id-mpa-dev-github: roles " + ((@($ghAll | ForEach-Object { $_.roleDefinitionName }) -join ', ')) + ' (solo los autorizados, dentro del grupo)')
        Expect (-not (Test-ActionAllowed (Get-RoleDefinitionsAt $gh.principalId $kv.id).definitions $DeployAction)) "id-mpa-dev-github sin $DeployAction (no la necesita)"
    }
    $rt = Invoke-Az @('identity', 'show', '--name', 'id-mpa-dev-runtime', '--resource-group', $ResourceGroup, '--output', 'json') -AllowFailure -What 'identidad de ejecucion'
    if ($null -eq $rt) { Note 'id-mpa-dev-runtime no existe todavia (la crea Core)' }
    else {
        $rtAll = Invoke-Az @('role', 'assignment', 'list', '--all', '--assignee', $rt.principalId, '--output', 'json') -Array -What 'roles de ejecucion'
        Expect (@($rtAll | Where-Object { $_.roleDefinitionName -ne 'AcrPull' }).Count -eq 0) ("id-mpa-dev-runtime: roles " + ((@($rtAll | ForEach-Object { $_.roleDefinitionName }) -join ', ')) + ' (solo AcrPull)')
    }
    $myRg = Invoke-Az @('role', 'assignment', 'list', '--assignee', $me, '--scope', $rgId, '--include-inherited', '--include-groups', '--output', 'json') -Array -What 'tus roles en el grupo'
    Note ("tu sesion, roles en el grupo: " + (@($myRg | ForEach-Object { $_.roleDefinitionName } | Sort-Object -Unique) -join ', '))
    Pass ("roles integrados resueltos: Container Apps Contributor {0}, Managed Identity Operator {1}" -f $roleIds.containerAppsContributorRoleId, $roleIds.managedIdentityOperatorRoleId)

    Section '7. ACR'
    $acrs = Get-Res 'Microsoft.ContainerRegistry/registries'
    if ($acrs.Count -eq 0) { Note 'sin registro todavia (Core crea ACR Basic sin usuario administrador)' }
    foreach ($r in $acrs) {
        $acr = Show-Res $r.id
        Expect ("$($acr.sku.name)" -eq 'Basic') "$($acr.name): SKU $($acr.sku.name)"
        Expect ($acr.properties.adminUserEnabled -eq $false) "$($acr.name): usuario administrador deshabilitado"
        $onAcr = Invoke-Az @('role', 'assignment', 'list', '--scope', $acr.id, '--output', 'json') -Array -What 'roles sobre el ACR'
        Expect (@($onAcr | Where-Object { $_.roleDefinitionName -notin @('AcrPull', 'AcrPush') }).Count -eq 0) ("roles sobre el ACR: " + (@($onAcr | ForEach-Object { $_.roleDefinitionName }) -join ', '))
    }
    if ($acrs.Count -gt 1) { Block 'mas de un registro en el grupo' }

    Section '8. PostgreSQL'
    $caps = Get-Arm "/subscriptions/$($account.id)/providers/Microsoft.DBforPostgreSQL/locations/$Location/capabilities" '2024-08-01'
    $capsText = if ($null -ne $caps) { ConvertTo-Json -InputObject $caps -Depth 30 -Compress } else { '' }
    Expect ($capsText -match 'Standard_B1ms') "Flexible Server Standard_B1ms ofrecido en $Location para esta suscripcion"
    if ($capsText -match '"16"') { Pass "PostgreSQL 16 ofrecido en $Location" } else { Warn "no se encontro la version 16 en las capacidades de $Location (revisar antes de Core)" }
    $servers = Get-Res 'Microsoft.DBforPostgreSQL/flexibleServers'
    if ($servers.Count -eq 0) { Note 'sin servidor todavia (Core crea Flexible Server 16, B1ms, sin HA, TLS obligatorio)' }
    foreach ($r in $servers) {
        $pg = Show-Res $r.id
        Expect ("$($pg.sku.name)" -eq 'Standard_B1ms') "$($pg.name): SKU $($pg.sku.name)"
        Expect ("$($pg.properties.version)" -eq '16') "$($pg.name): version $($pg.properties.version)"
        Expect ("$($pg.properties.highAvailability.mode)" -in @('', 'Disabled')) "$($pg.name): sin alta disponibilidad"
        Note "$($pg.name): estado $($pg.properties.state)"
        $tls = Get-Arm "$($pg.id)/configurations/require_secure_transport" '2024-08-01'
        Expect ("$($tls.properties.value)" -eq 'on' -or "$($tls.properties.value)" -eq 'ON') 'require_secure_transport = ON'
        $rules = Get-Arm "$($pg.id)/firewallRules" '2024-08-01'
        foreach ($rule in (As-Array $rules.value)) {
            $s = "$($rule.properties.startIpAddress)"; $e = "$($rule.properties.endIpAddress)"
            if ($s -eq '0.0.0.0' -or $s -ne $e) { Block "regla de firewall no permitida: $($rule.name) $s-$e" }
            elseif ($rule.name -like 'aca-out-*') { Pass "regla $($rule.name) $s" }
            else { Warn "regla ajena a U12 (no se toca): $($rule.name) $s" }
        }
    }
    if ($servers.Count -gt 1) { Block 'mas de un servidor PostgreSQL en el grupo' }

    Section '9. Container Apps'
    $envs = Get-Res 'Microsoft.App/managedEnvironments'
    $apps = Get-Res 'Microsoft.App/containerApps'
    $jobs = Get-Res 'Microsoft.App/jobs'
    if (($envs.Count + $apps.Count + $jobs.Count) -eq 0) { Note 'sin entorno, apps ni job todavia (Core y Apps los crean)' }
    foreach ($r in $envs) {
        $env = Show-Res $r.id
        $profiles = @((As-Array $env.properties.workloadProfiles) | ForEach-Object { "$($_.workloadProfileType)" })
        Expect (@($profiles | Where-Object { $_ -ne 'Consumption' }).Count -eq 0) "$($env.name): perfiles $($profiles -join ', ')"
        $mode = "$($env.properties.environmentMode)"
        if ($mode -ceq 'WorkloadProfiles') { Pass "$($env.name): modo WorkloadProfiles (admite el job de bootstrap)" }
        else { Warn "$($env.name): modo '$mode', sin jobs; Core intentara pasarlo a WorkloadProfiles y, si Azure no lo admite, hay que recrearlo (README de U12, 5.2)" }
    }
    if ($envs.Count -gt 1) { Block 'mas de un entorno de Container Apps en el grupo' }
    foreach ($r in $apps) {
        $app = Show-Res $r.id
        $ing = $app.properties.configuration.ingress
        if ($app.name -like '*-api') { Expect ($ing.external -eq $false -and $ing.allowInsecure -eq $false) "$($app.name): ingress interno, solo HTTPS" }
        elseif ($app.name -like '*-frontend') { Expect ($ing.external -eq $true -and $ing.allowInsecure -eq $false) "$($app.name): ingress externo solo HTTPS" }
        else { Block "app no prevista: $($app.name)" }
        $regs = @((As-Array $app.properties.configuration.registries))
        Expect (@($regs | Where-Object { $_.passwordSecretRef -or -not $_.identity }).Count -eq 0) "$($app.name): imagenes con identidad administrada"
    }
    foreach ($r in $jobs) {
        $job = Show-Res $r.id
        Expect ("$($job.properties.configuration.triggerType)" -eq 'Manual') "$($job.name): job manual"
    }

    Section '10. Bicep'
    foreach ($t in @($U12Template, $U10Template)) {
        Invoke-Az @('bicep', 'build', '--file', $t, '--stdout') -Raw -What "az bicep build $t" | Out-Null
        Pass "build: $t"
        $lint = Invoke-Az @('bicep', 'lint', '--file', $t) -Raw -What "az bicep lint $t"
        Expect (-not ($lint -match '(?im)\(\d+,\d+\)\s*:\s*(Warning|Error)\b')) "lint sin avisos: $t"
    }
    $u10Built = Invoke-Az @('bicep', 'build-params', '--file', $U10Parameters, '--stdout') -What 'az bicep build-params (U10)'
    Pass 'parametros de U10 y U12 compilan'
    $secretLike = @($u12Params.PSObject.Properties | Where-Object { $_.Name -match '(?i)password|secret|connectionstring|token' })
    Expect ($secretLike.Count -eq 0) 'parametros de U12 sin nada con aspecto de secreto'
    Expect ($Location -eq 'centralus') 'DT-100 region = centralus'
    Expect (Test-SourceHas 'infra/azure/u12/modules/environment.bicep' @("workloadProfileType: 'Consumption'")) 'DT-100 compute = Container Apps Consumption'
    Expect (-not (Test-SourceHas 'infra/azure/u12/modules/environment.bicep' @('Dedicated'))) 'DT-100 sin perfiles Dedicated'
    Expect (Test-SourceHas 'infra/azure/u12/modules/registry.bicep' @("name: 'Basic'", 'adminUserEnabled: false')) 'DT-100 registry = ACR Basic sin administrador'
    Expect (Test-SourceHas 'infra/azure/u12/modules/postgres.bicep' @("version: '16'", "name: 'Standard_B1ms'", "mode: 'Disabled'")) 'DT-100 postgresql = Flexible Server 16, Standard_B1ms, sin HA'
    Expect ((Test-SourceHas $U10Parameters @('param keyVaultArmSecretAccess = true')) -and (Test-SourceHas 'infra/azure/modules/base.bicep' @("publicNetworkAccess: 'Disabled'"))) 'DT-100 Key Vault = opcion C (privado + plantillas)'
    Expect (-not (Test-SourceHas 'infra/azure/u12/modules/apps.bicep' @('keyVaultUrl'))) 'sin referencias de Key Vault en tiempo de ejecucion'

    Section '11. Seguridad'
    $python = Find-Python
    if ($python.Count -eq 0) { Warn 'Python 3.9+ no encontrado: no se ejecutan el detector de secretos ni las pruebas de configuracion' }
    else {
        $scan = Invoke-Python $python @('infra/ci/secret_scan.py') (Get-Location).Path
        $scanLine = @($scan.text -split "`n" | Where-Object { $_ -match '^secret scan:' }) -join ''
        Expect ($scan.code -eq 0) "detector de secretos: $scanLine"
        $tests = Invoke-Python $python @('-m', 'unittest', 'test_u12_config.Infrastructure', 'test_u12_config.Images', 'test_u12_config.Bootstrap', 'test_u12_config.Workflow', 'test_u12_config.ScriptSource') (Join-Path (Get-Location).Path 'infra/tests')
        $ran = @($tests.text -split "`n" | Where-Object { $_ -match '^(Ran |OK|FAILED)' }) -join ' '
        Expect ($tests.code -eq 0) "pruebas de configuracion de U12: $ran"
    }
    Expect (Test-SourceHas '.github/workflows/deploy-dev.yml' @('id-token: write', 'contents: read')) 'workflow: OIDC con permisos minimos'
    Expect (-not (Test-SourceHas '.github/workflows/deploy-dev.yml' @('secrets.'))) 'workflow sin secretos de GitHub'

    Section '12. Resultado'
    foreach ($w in $script:Warnings) { Write-Host "  aviso: $w" -ForegroundColor Yellow }
    if ($script:Blockers.Count -gt 0) {
        foreach ($b in $script:Blockers) { Write-Host "  bloqueo: $b" -ForegroundColor Red }
        Write-Host 'PREFLIGHT BLOQUEADO' -ForegroundColor Red
        exit 1
    }
    Write-Host 'PREFLIGHT OK' -ForegroundColor Green
    if ($deployAllowed) {
        Write-Host "U12 PREFLIGHT OK $dash KeyVaultRole no requerido" -ForegroundColor Green
        if ($optionC) { Write-Host 'Siguiente etapa: -Stage Secrets (la opcion C del Key Vault ya esta aplicada)' } else { Write-Host 'Siguiente etapa: -Stage KeyVault (CAMBIAR-KV)' }
    }
    else { Write-Host "U12 PREFLIGHT OK $dash requiere etapa KeyVaultRole" -ForegroundColor Yellow; Write-Host 'Siguiente etapa: -Stage KeyVaultRole (crea el rol minimo; luego repetir -PreflightOnly)' }
    exit 0
}

if ($Stage -eq 'Preflight' -and -not $SelfTest) { Invoke-Preflight }

# ---------------------------------------------------------------------------------------------------------
if (-not (Test-Path $U12Template) -or -not (Test-Path $U10Template)) { Stop-U12 'ejecuta el script desde la raiz del repositorio' }
New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null

Step "Sesion de Azure CLI (fase $Stage)"
$account = Invoke-Az @('account', 'show', '--output', 'json') -What 'az account show (ejecuta az login primero)'
Write-Host ("Tenant: {0} | suscripcion: {1} ({2}) | cuenta: {3}" -f $account.tenantId, $account.name, $account.state, $account.user.type)
if ($account.tenantId -ne $ExpectedTenant) { Stop-U12 'tenant distinto del de DT-098' }
if ($account.name -notmatch 'Azure for Students') { Stop-U12 'la suscripcion activa no es Azure for Students' }
if ($account.state -ne 'Enabled') { Stop-U12 'la suscripcion no esta habilitada' }
if ($account.user.type -ne 'user') { Stop-U12 'la sesion debe ser la del responsable' }
$rgId = "/subscriptions/$($account.id)/resourceGroups/$ResourceGroup"
$exists = (Invoke-Az @('group', 'exists', '--name', $ResourceGroup) -Raw -What 'az group exists').Trim()
if ($exists -ne 'true') { Stop-U12 "no existe $ResourceGroup (U10)" }

# Parameters: dev.bicepparam is the single source; dynamic values are set here and passed as a temporary ARM file.
function Get-U12Parameters([hashtable]$Overrides) {
    $built = Invoke-Az @('bicep', 'build-params', '--file', 'infra/azure/u12/dev.bicepparam', '--stdout') -What 'az bicep build-params'
    $params = ConvertFrom-Json -InputObject $built.parametersJson
    foreach ($k in $Overrides.Keys) {
        if ($null -eq $params.parameters.PSObject.Properties[$k]) { $params.parameters | Add-Member -NotePropertyName $k -NotePropertyValue ([pscustomobject]@{ value = $null }) }
        $params.parameters.$k.value = $Overrides[$k]
    }
    $secretLike = @($params.parameters.PSObject.Properties | Where-Object { $_.Name -match '(?i)password|secret|connectionstring|token' })
    if ($secretLike.Count) { Stop-U12 ('parametros con aspecto de secreto (las contrasenas solo llegan por getSecret): ' + (($secretLike | ForEach-Object { $_.Name }) -join ', ')) }
    $file = Join-Path $EvidenceDir "parameters-$Stage.json"
    Set-Content -Path $file -Value (ConvertTo-Json -InputObject $params -Depth 20) -Encoding ASCII
    return $file
}

function Read-Evidence([string]$Name) {
    $path = Join-Path $EvidenceDir $Name
    if (-not (Test-Path $path)) { return $null }
    return (Get-Content -Raw -Path $path | ConvertFrom-Json)
}

function Invoke-U12Deployment([hashtable]$Overrides, [bool]$Apps, [string]$Word) {
    $roleIds = Resolve-RoleIds
    $Overrides['containerAppsContributorRoleId'] = $roleIds.containerAppsContributorRoleId
    $Overrides['managedIdentityOperatorRoleId'] = $roleIds.managedIdentityOperatorRoleId
    $paramFile = Get-U12Parameters $Overrides
    $deployArgs = @('--resource-group', $ResourceGroup, '--name', $U12DeploymentName, '--template-file', $U12Template, '--parameters', "@$paramFile")
    Invoke-Az @('bicep', 'lint', '--file', $U12Template) -Raw -What 'az bicep lint' | Out-Null
    $validation = Invoke-Az (@('deployment', 'group', 'validate') + $deployArgs + @('--output', 'json')) -What 'validate'
    if ($validation.error) { Stop-U12 ('validate devolvio error: ' + ($validation.error | ConvertTo-Json -Depth 10)) }
    Write-Host "validate: $($validation.properties.provisioningState)"
    $whatIf = Invoke-Az (@('deployment', 'group', 'what-if') + $deployArgs + @('--result-format', 'FullResourcePayloads', '--no-pretty-print', '--output', 'json')) -What 'what-if'
    Save-Evidence "what-if-$Stage.json" $whatIf
    foreach ($c in (As-Array $whatIf.changes)) { if ($c.changeType -ne 'Ignore') { Write-Host (" {0,-9} {1}" -f $c.changeType, $c.resourceId) } }
    $allowedRoles = @($AcrPullRoleId, $AcrPushRoleId, $roleIds.containerAppsContributorRoleId, $roleIds.managedIdentityOperatorRoleId)
    $problems = Test-U12WhatIf $whatIf $rgId $allowedRoles $Apps
    if ($problems.Count -gt 0) {
        Write-Host ''; Write-Host 'WHAT-IF NO AUTORIZADO' -ForegroundColor Red
        $problems | ForEach-Object { Write-Host " - $_" }
        exit 2
    }
    Write-Host 'what-if conforme: solo recursos de U12 en el grupo, con los SKU y la configuracion de DT-100' -ForegroundColor Green
    Confirm-Or-Stop $Word 'desplegar exactamente esos cambios'
    $deployment = Invoke-Az (@('deployment', 'group', 'create') + $deployArgs + @('--output', 'json')) -What 'create'
    if ($deployment.properties.provisioningState -ne 'Succeeded') { Stop-U12 "el despliegue termino en $($deployment.properties.provisioningState)" }
    Write-Host "create: Succeeded"
    $out = $deployment.properties.outputs
    $summary = [ordered]@{}
    foreach ($p in $out.PSObject.Properties) { $summary[$p.Name] = $p.Value.value }
    Save-Evidence 'outputs.json' $summary
    return $summary
}

function Update-Firewall($Outputs, [string]$Tag) {
    $ips = Invoke-Az @('containerapp', 'show', '--name', $Outputs.apiName, '--resource-group', $ResourceGroup, '--query', 'properties.outboundIpAddresses', '--output', 'json') -Array -What 'az containerapp show (IP de salida)'
    $ips = @($ips | ForEach-Object { "$_" } | Where-Object { $_ -match '^\d{1,3}(\.\d{1,3}){3}$' } | Sort-Object -Unique)
    if ($ips.Count -eq 0) {
        Stop-U12 ("Container Apps no publica IP de salida para este entorno. No se abre PostgreSQL: la alternativa es la regla 0.0.0.0 " +
                  "(cualquier servicio de Azure, tambien de otros clientes) o una red privada; ambas requieren decision del responsable (DT-100).")
    }
    Write-Host "IP de salida de Container Apps ($($ips.Count)): $($ips -join ', ')"
    $previous = Read-Evidence 'postgres-ips.json'
    $same = $previous -and (Test-SameList (As-Array $previous.ips) $ips)
    if (-not $same) {
        Step 'Reglas de firewall de PostgreSQL = IP de salida actuales'
        Invoke-U12Deployment @{ deployApps = $true; imageTag = $Tag; postgresAllowedIps = $ips } $true 'FIREWALL' | Out-Null
        Save-Evidence 'postgres-ips.json' ([ordered]@{ date = (Get-Date).ToUniversalTime().ToString('o'); ips = $ips })
    } else { Write-Host 'Las reglas ya coinciden con las IP de salida.' }
    $rules = Invoke-Az @('postgres', 'flexible-server', 'firewall-rule', 'list', '--resource-group', $ResourceGroup, '--server-name', $Outputs.postgresName, '--output', 'json') -Array -What 'firewall-rule list'
    foreach ($stale in (Get-StaleRules @($rules | ForEach-Object { $_.name }) $ips)) {
        Invoke-Az @('postgres', 'flexible-server', 'firewall-rule', 'delete', '--resource-group', $ResourceGroup, '--server-name', $Outputs.postgresName, '--name', $stale, '--yes') -Raw -What "borrar regla $stale" | Out-Null
        Write-Host "  regla obsoleta borrada: $stale"
    }
    $foreign = @($rules | Where-Object { $_.name -notlike 'aca-out-*' })
    if ($foreign.Count) { Write-Host ("AVISO: reglas que no son de U12 (no se tocan): " + (($foreign | ForEach-Object { "$($_.name) $($_.startIpAddress)-$($_.endIpAddress)" }) -join '; ')) -ForegroundColor Yellow }
}

$kvName = (ConvertFrom-Json -InputObject ((Invoke-Az @('bicep', 'build-params', '--file', 'infra/azure/u12/dev.bicepparam', '--stdout') -What 'build-params').parametersJson)).parameters.keyVaultName.value
$kv = Invoke-Az @('resource', 'show', '--resource-group', $ResourceGroup, '--name', $kvName, '--resource-type', 'Microsoft.KeyVault/vaults', '--output', 'json') -What 'Key Vault de U10'

function Get-LiveTag([string]$AppName) {
    $image = Invoke-Az @('containerapp', 'show', '--name', $AppName, '--resource-group', $ResourceGroup, '--query', 'properties.template.containers[0].image', '--output', 'tsv') -Raw -What "az containerapp show $AppName"
    $tag = ($image.Trim() -split ':')[-1]
    if ($tag -notmatch '^[0-9a-f]{7,40}$') { Stop-U12 "etiqueta de imagen inesperada en $AppName" }
    return $tag
}

# HTTP status of a GET without credentials (Windows PowerShell 5.1 and PowerShell 7 throw on 4xx/5xx).
function Get-HttpStatus([string]$Uri) {
    try { return [int](Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec 120).StatusCode }
    catch { if ($_.Exception.Response) { return [int]$_.Exception.Response.StatusCode } else { return 0 } }
}

function Get-Outputs {
    $o = Read-Evidence 'outputs.json'
    if (-not $o) { Stop-U12 'falta tmp/u12-evidence/outputs.json: ejecuta antes la fase Core' }
    return $o
}

switch ($Stage) {
    'KeyVaultRole' {
        Step "Rol personalizado minimo para $DeployAction (solo si tu sesion no lo tiene)"
        $me = Get-SignedInUserId
        $mine = Get-RoleDefinitionsAt $me $kv.id
        if (Test-ActionAllowed $mine.definitions $DeployAction) { Write-Host "ALREADY_ALLOWED: tu sesion ya tiene $DeployAction; no se crea ningun rol." -ForegroundColor Green; break }
        $found = Invoke-Az @('role', 'definition', 'list', '--name', $DeployRoleName, '--scope', $rgId, '--output', 'json') -Array -What 'buscar el rol personalizado'
        $custom = @($found | Where-Object { $_.roleType -eq 'CustomRole' -and $_.roleName -eq $DeployRoleName })
        if ($custom.Count -gt 1) { Stop-U12 "hay mas de un rol '$DeployRoleName'" }
        if ($custom.Count -eq 0) {
            $definition = [ordered]@{
                Name = $DeployRoleName; IsCustom = $true
                Description = 'Lets Azure Resource Manager read Key Vault secrets during a template deployment (getSecret). Nothing else.'
                Actions = @($DeployAction); NotActions = @(); DataActions = @(); NotDataActions = @(); AssignableScopes = @($rgId) }
            Write-Host (ConvertTo-Json -InputObject $definition -Depth 5)
            Confirm-Or-Stop 'CREAR-ROL' "crear ese rol personalizado (asignable solo en $ResourceGroup)"
            $file = Join-Path $EvidenceDir 'role-definition.json'
            Set-Content -Path $file -Value (ConvertTo-Json -InputObject $definition -Depth 5) -Encoding ASCII
            Invoke-Az @('role', 'definition', 'create', '--role-definition', "@$file", '--output', 'json') -What 'az role definition create' | Out-Null
            for ($i = 0; $i -lt 12; $i++) {  # the new definition takes a moment to be listed
                $found = Invoke-Az @('role', 'definition', 'list', '--name', $DeployRoleName, '--scope', $rgId, '--output', 'json') -Array -What 'buscar el rol personalizado'
                $custom = @($found | Where-Object { $_.roleType -eq 'CustomRole' -and $_.roleName -eq $DeployRoleName })
                if ($custom.Count) { break }
                Start-Sleep -Seconds 10
            }
            if ($custom.Count -ne 1) { Stop-U12 'el rol personalizado aun no aparece; repetir esta fase en unos minutos' }
        }
        $actions = @((As-Array $custom[0].permissions) | ForEach-Object { (As-Array $_.actions) })
        $scopes = @((As-Array $custom[0].assignableScopes))
        if ($actions.Count -ne 1 -or $actions[0] -ne $DeployAction -or @($scopes | Where-Object { -not "$_".StartsWith($rgId, [System.StringComparison]::OrdinalIgnoreCase) }).Count) {
            Stop-U12 "el rol '$DeployRoleName' existente no es el minimo (acciones o ambitos de mas); no se usa"
        }
        Confirm-Or-Stop 'ASIGNAR-ROL' "asignar '$DeployRoleName' a tu usuario solo sobre el Key Vault $($kv.name)"
        Invoke-Az @('role', 'assignment', 'create', '--assignee-object-id', $me, '--assignee-principal-type', 'User', '--role', $custom[0].name, '--scope', $kv.id, '--output', 'json') -What 'az role assignment create' | Out-Null
        Write-Host "Asignado. Los cambios de RBAC pueden tardar unos minutos; repetir Preflight." -ForegroundColor Green
    }
    'KeyVault' {
        Step 'U10: el despliegue de plantillas puede leer secretos (DT-100); la red publica sigue deshabilitada'
        $u10Args = @('--name', $U10DeploymentName, '--location', $Location, '--template-file', $U10Template, '--parameters', $U10Parameters)
        $whatIf = Invoke-Az (@('deployment', 'sub', 'what-if') + $u10Args + @('--result-format', 'FullResourcePayloads', '--no-pretty-print', '--output', 'json')) -What 'what-if de U10'
        Save-Evidence 'what-if-KeyVault.json' $whatIf
        foreach ($c in (As-Array $whatIf.changes)) { if ($c.changeType -ne 'Ignore') { Write-Host (" {0,-9} {1}" -f $c.changeType, $c.resourceId) } }
        $ghPrincipal = "$((Invoke-Az @('identity', 'show', '--name', 'id-mpa-dev-github', '--resource-group', $ResourceGroup, '--output', 'json') -What 'identidad de GitHub').principalId)"
        $problems = Test-KeyVaultWhatIf $whatIf $ghPrincipal
        if ($problems.Count) { Write-Host 'WHAT-IF NO AUTORIZADO' -ForegroundColor Red; $problems | ForEach-Object { Write-Host " - $_" }; exit 2 }
        foreach ($c in (As-Array $whatIf.changes)) {
            if ($c.changeType -eq 'Modify' -and (Test-ReaderReferenceNoise $c $ghPrincipal)) {
                Write-Host "  (sin cambio real) $(($c.resourceId -split '/')[-1]): Reader de id-mpa-dev-github; what-if no evalua reference().principalId, el principal sigue siendo $ghPrincipal" -ForegroundColor DarkGray
            }
        }
        if (-not (Test-KeyVaultPending $whatIf)) { Write-Host 'ALREADY_CONFIGURED: el Key Vault ya permite getSecret a las plantillas.' -ForegroundColor Green; break }
        Confirm-Or-Stop 'CAMBIAR-KV' 'cambiar SOLO enabledForTemplateDeployment y networkAcls.bypass del Key Vault de U10'
        $d = Invoke-Az (@('deployment', 'sub', 'create') + $u10Args + @('--output', 'json')) -What 'despliegue de U10'
        if ($d.properties.provisioningState -ne 'Succeeded') { Stop-U12 "U10 termino en $($d.properties.provisioningState)" }
        $kv = Invoke-Az @('resource', 'show', '--resource-group', $ResourceGroup, '--name', $kvName, '--resource-type', 'Microsoft.KeyVault/vaults', '--output', 'json') -What 'Key Vault de U10'
        if ($kv.properties.publicNetworkAccess -ne 'Disabled' -or $kv.properties.enabledForTemplateDeployment -ne $true -or $kv.properties.networkAcls.bypass -ne 'AzureServices') { Stop-U12 'el Key Vault no quedo como se esperaba' }
        Write-Host 'Key Vault: publicNetworkAccess=Disabled, plantillas=true, bypass=AzureServices' -ForegroundColor Green
    }
    'Secrets' {
        Step 'Contrasenas de PostgreSQL en el Key Vault (se generan solo si no existen; nunca se muestran)'
        foreach ($name in $SecretNames) {
            $uri = "https://management.azure.com$($kv.id)/secrets/$($name)?api-version=$KeyVaultApi"
            $existing = Invoke-Az @('rest', '--method', 'get', '--uri', $uri, '--output', 'json') -What "secreto $name" -AllowFailure
            if ($existing) { Write-Host "  ${name}: ya existe (no se toca)"; continue }
            $file = Join-Path $EvidenceDir "request-$([guid]::NewGuid().ToString('N')).json"
            try {
                Set-Content -Path $file -Value (ConvertTo-Json -InputObject ([ordered]@{ properties = [ordered]@{ value = (New-DbPassword); contentType = 'PostgreSQL password (U12, DT-100)' } }) -Depth 5) -Encoding ASCII
                Invoke-Az @('rest', '--method', 'put', '--uri', $uri, '--body', "@$file", '--headers', 'Content-Type=application/json', '--output', 'none') -Raw -What "crear el secreto $name" | Out-Null
            } finally { Remove-Item -Path $file -Force -ErrorAction SilentlyContinue }
            Write-Host "  ${name}: creado en el Key Vault"
        }
        Write-Host 'Secretos listos. Ningun valor se mostro ni quedo en disco.' -ForegroundColor Green
    }
    'Core' {
        Step 'Core: ACR, PostgreSQL, entorno de Container Apps, identidad de ejecucion y roles de GitHub'
        $out = Invoke-U12Deployment @{ deployApps = $false } $false 'DESPLEGAR'
        $envNow = Invoke-Az @('resource', 'show', '--resource-group', $ResourceGroup, '--name', $out.environmentName, '--resource-type', 'Microsoft.App/managedEnvironments', '--output', 'json') -What 'entorno de Container Apps'
        if ("$($envNow.properties.environmentMode)" -cne 'WorkloadProfiles') {
            Stop-U12 ("el entorno $($out.environmentName) sigue en modo '$($envNow.properties.environmentMode)' (sin jobs): Azure no lo convirtio. " +
                      'Recrearlo segun infra/azure/u12/README.md 5.2 y repetir Core.')
        }
        Write-Host "Entorno $($out.environmentName): modo WorkloadProfiles" -ForegroundColor Green
        $entraText = Get-Content -Raw -Path $EntraSpec
        $newText = Add-RedirectUri $entraText $out.frontendUrl
        if ($newText -ne $entraText) { Set-Content -Path $EntraSpec -Value $newText -NoNewline -Encoding ASCII; Write-Host "Redirect URI de la SPA anadido al estado deseado de U11: $($out.frontendUrl)" }
        $gh = Invoke-Az @('identity', 'show', '--name', 'id-mpa-dev-github', '--resource-group', $ResourceGroup, '--output', 'json') -What 'identidad de GitHub'
        $vars = [ordered]@{
            AZURE_CLIENT_ID = $gh.clientId; AZURE_TENANT_ID = $account.tenantId; AZURE_SUBSCRIPTION_ID = $account.id
            AZURE_RESOURCE_GROUP = $ResourceGroup; ACR_NAME = $out.registryName; ACR_LOGIN_SERVER = $out.registryLoginServer
            CA_API = $out.apiName; CA_FRONTEND = $out.frontendName; CAJ_BOOTSTRAP = $out.bootstrapName
        }
        $static = (ConvertFrom-Json -InputObject ((Invoke-Az @('bicep', 'build-params', '--file', 'infra/azure/u12/dev.bicepparam', '--stdout') -What 'build-params').parametersJson)).parameters
        $vars['ENTRA_TENANT_ID'] = $static.entraTenantId.value
        $vars['ENTRA_API_CLIENT_ID'] = $static.entraApiClientId.value
        $vars['ENTRA_SPA_CLIENT_ID'] = $static.entraSpaClientId.value
        $lines = @('# Variables (no secretas) del entorno `dev` de GitHub para .github/workflows/deploy-dev.yml (U12, DT-100).',
                   '# Requieren el entorno: gh api -X PUT repos/{owner}/{repo}/environments/dev')
        foreach ($k in $vars.Keys) { $lines += "gh variable set $k --env dev --body `"$($vars[$k])`"" }
        Set-Content -Path (Join-Path $EvidenceDir 'github-dev-variables.txt') -Value $lines -Encoding ASCII
        Write-Host ''
        Write-Host "Siguientes pasos: 1) deploy-u11.ps1 (redirect URI); 2) variables de GitHub en $EvidenceDir/github-dev-variables.txt;"
        Write-Host '3) ejecutar el workflow "Deploy dev" (publica las imagenes); 4) -Stage Apps -ImageTag <sha del workflow>.'
    }
    'Apps' {
        if ($ImageTag -notmatch '^[0-9a-f]{7,40}$') { Stop-U12 'falta -ImageTag con el SHA publicado por el workflow "Deploy dev"' }
        Get-Outputs | Out-Null
        $previous = Read-Evidence 'postgres-ips.json'
        $ips = @(); if ($previous) { $ips = @((As-Array $previous.ips)) }
        Step "Apps: api (interna), frontend (HTTPS) y job de bootstrap con la etiqueta $ImageTag"
        $out = Invoke-U12Deployment @{ deployApps = $true; imageTag = $ImageTag; postgresAllowedIps = $ips } $true 'DESPLEGAR'
        Update-Firewall $out $ImageTag
        Write-Host "Frontend: $($out.frontendUrl). Siguiente: -Stage Bootstrap." -ForegroundColor Green
    }
    'Firewall' {
        $out = Get-Outputs
        Update-Firewall $out (Get-LiveTag $out.apiName)
    }
    'Bootstrap' {
        $out = Get-Outputs
        Step "Bootstrap: $($out.bootstrapName) (dataset -> migraciones -> ingesta -> forecast -> recomendaciones)"
        $state = (Invoke-Az @('postgres', 'flexible-server', 'show', '--resource-group', $ResourceGroup, '--name', $out.postgresName, '--query', 'state', '--output', 'tsv') -Raw -What 'estado de PostgreSQL').Trim()
        if ($state -ne 'Ready') { Stop-U12 "PostgreSQL esta en estado $state (usa -Stage Start)" }
        $exec = Invoke-Az @('containerapp', 'job', 'start', '--name', $out.bootstrapName, '--resource-group', $ResourceGroup, '--output', 'json') -What 'az containerapp job start'
        $execName = "$($exec.name)"
        Write-Host "Ejecucion: $execName"
        $deadline = (Get-Date).AddMinutes(45)
        do {
            Start-Sleep -Seconds 15
            $status = (Invoke-Az @('containerapp', 'job', 'execution', 'show', '--name', $out.bootstrapName, '--resource-group', $ResourceGroup, '--job-execution-name', $execName, '--query', 'properties.status', '--output', 'tsv') -Raw -What 'estado de la ejecucion').Trim()
            Write-Host "  $(Get-Date -Format HH:mm:ss) $status"
        } while ($status -in @('Running', 'Processing', '') -and (Get-Date) -lt $deadline)
        $logs = Invoke-Az @('containerapp', 'job', 'logs', 'show', '--name', $out.bootstrapName, '--resource-group', $ResourceGroup, '--execution', $execName, '--container', 'bootstrap', '--format', 'text') -Raw -What 'registros del job' -AllowFailure
        if ($logs) { Set-Content -Path (Join-Path $EvidenceDir "bootstrap-$execName.log") -Value $logs -Encoding UTF8; Write-Host $logs }
        else { Write-Host '(registros no disponibles por CLI sin Log Analytics: portal > el job > Execution history > Console logs)' -ForegroundColor Yellow }
        $history = @(); $h = Read-Evidence 'bootstrap-executions.json'; if ($h) { $history = @((As-Array $h)) }
        $history += [ordered]@{ execution = $execName; status = $status; date = (Get-Date).ToUniversalTime().ToString('o'); imageTag = (Get-LiveTag $out.apiName) }
        Save-Evidence 'bootstrap-executions.json' $history
        if ($status -ne 'Succeeded') { Stop-U12 "el bootstrap termino en $status" }
        Write-Host 'BOOTSTRAP Succeeded' -ForegroundColor Green
    }
    'Stop' {
        $out = Get-Outputs
        Invoke-Az @('postgres', 'flexible-server', 'stop', '--resource-group', $ResourceGroup, '--name', $out.postgresName) -Raw -What 'detener PostgreSQL' | Out-Null
        Write-Host 'PostgreSQL detenido (Azure lo arranca solo a los 7 dias). Las apps ya escalan a cero.' -ForegroundColor Green
    }
    'Start' {
        $out = Get-Outputs
        Invoke-Az @('postgres', 'flexible-server', 'start', '--resource-group', $ResourceGroup, '--name', $out.postgresName) -Raw -What 'arrancar PostgreSQL' | Out-Null
        Write-Host 'PostgreSQL arrancado.' -ForegroundColor Green
    }
    'Verify' {
        $out = Get-Outputs
        Step 'Verificacion'
        $acr = Invoke-Az @('acr', 'show', '--name', $out.registryName, '--output', 'json') -What 'acr show'
        $pg = Invoke-Az @('postgres', 'flexible-server', 'show', '--resource-group', $ResourceGroup, '--name', $out.postgresName, '--output', 'json') -What 'postgres show'
        $tls = (Invoke-Az @('postgres', 'flexible-server', 'parameter', 'show', '--resource-group', $ResourceGroup, '--server-name', $out.postgresName, '--name', 'require_secure_transport', '--query', 'value', '--output', 'tsv') -Raw -What 'require_secure_transport').Trim()
        $rules = Invoke-Az @('postgres', 'flexible-server', 'firewall-rule', 'list', '--resource-group', $ResourceGroup, '--server-name', $out.postgresName, '--output', 'json') -Array -What 'firewall'
        $api = Invoke-Az @('containerapp', 'show', '--name', $out.apiName, '--resource-group', $ResourceGroup, '--output', 'json') -What 'api'
        $fe = Invoke-Az @('containerapp', 'show', '--name', $out.frontendName, '--resource-group', $ResourceGroup, '--output', 'json') -What 'frontend'
        $job = Invoke-Az @('containerapp', 'job', 'show', '--name', $out.bootstrapName, '--resource-group', $ResourceGroup, '--output', 'json') -What 'job'
        $gh = Invoke-Az @('identity', 'show', '--name', 'id-mpa-dev-github', '--resource-group', $ResourceGroup, '--output', 'json') -What 'identidad de GitHub'
        $ghRoles = Invoke-Az @('role', 'assignment', 'list', '--all', '--assignee', $gh.principalId, '--output', 'json') -Array -What 'roles de GitHub'
        $rt = Invoke-Az @('identity', 'show', '--name', 'id-mpa-dev-runtime', '--resource-group', $ResourceGroup, '--output', 'json') -What 'identidad de ejecucion'
        $rtRoles = Invoke-Az @('role', 'assignment', 'list', '--all', '--assignee', $rt.principalId, '--output', 'json') -Array -What 'roles de ejecucion'
        $registries = @(@($api, $fe, $job) | ForEach-Object { (As-Array $_.properties.configuration.registries) })
        $executions = Invoke-Az @('containerapp', 'job', 'execution', 'list', '--name', $out.bootstrapName, '--resource-group', $ResourceGroup, '--output', 'json') -Array -What 'ejecuciones del job'
        $last = @($executions | Sort-Object { "$($_.properties.startTime)" } -Descending | Select-Object -First 1)
        $frontendStatus = Get-HttpStatus $out.frontendUrl
        $apiStatus = Get-HttpStatus ($out.frontendUrl.TrimEnd('/') + '/api/v1/me')  # API reached through the proxy, no token -> 401
        $envs = @(@($api, $job) | ForEach-Object { (As-Array $_.properties.template.containers) } | ForEach-Object { (As-Array $_.env) })
        $secretEnvs = @($envs | Where-Object { $_.name -match '(?i)password' })
        $urls = @($envs | Where-Object { $_.name -eq 'DATABASE_URL' })
        $me = Get-SignedInUserId
        $ghAllowed = $GithubAllowedRoles
        $checks = [ordered]@{
            'ACR Basic sin usuario administrador'                = ($acr.sku.name -eq 'Basic' -and $acr.adminUserEnabled -eq $false)
            'PostgreSQL 16, B1ms, sin alta disponibilidad'        = ("$($pg.version)" -eq '16' -and $pg.sku.name -eq 'Standard_B1ms' -and $pg.highAvailability.mode -eq 'Disabled')
            'PostgreSQL con TLS obligatorio'                     = ($tls -eq 'ON')
            'firewall: solo IP de salida (aca-out-*), sin 0.0.0.0' = ($rules.Count -gt 0 -and @($rules | Where-Object { $_.name -notlike 'aca-out-*' -or $_.startIpAddress -ne $_.endIpAddress -or $_.startIpAddress -eq '0.0.0.0' }).Count -eq 0)
            'api sin ingress publico y solo HTTPS'               = ($api.properties.configuration.ingress.external -eq $false -and $api.properties.configuration.ingress.allowInsecure -eq $false)
            'entorno en modo WorkloadProfiles (admite jobs)'     = ("$((Invoke-Az @('resource', 'show', '--resource-group', $ResourceGroup, '--name', $out.environmentName, '--resource-type', 'Microsoft.App/managedEnvironments', '--output', 'json') -What 'entorno').properties.environmentMode)" -ceq 'WorkloadProfiles')
            'frontend solo HTTPS'                                = ($fe.properties.configuration.ingress.external -eq $true -and $fe.properties.configuration.ingress.allowInsecure -eq $false)
            'imagenes con identidad administrada, sin credenciales' = ($registries.Count -eq 3 -and @($registries | Where-Object { $_.passwordSecretRef -or $_.username -or -not $_.identity }).Count -eq 0)
            'job de bootstrap manual'                            = ($job.properties.configuration.triggerType -eq 'Manual')
            'GitHub: 4 roles minimos, todos dentro del grupo'     = ($ghRoles.Count -eq 4 -and @($ghRoles | Where-Object { $_.roleDefinitionName -notin $ghAllowed -or -not $_.scope.StartsWith($rgId, [System.StringComparison]::OrdinalIgnoreCase) }).Count -eq 0)
            'identidad de ejecucion: solo AcrPull sobre el ACR'  = ($rtRoles.Count -eq 1 -and $rtRoles[0].roleDefinitionName -eq 'AcrPull' -and $rtRoles[0].scope -eq $acr.id)
            'Key Vault opcion C: privado, plantillas=true, bypass=AzureServices' = ($kv.properties.publicNetworkAccess -eq 'Disabled' -and $kv.properties.enabledForTemplateDeployment -eq $true -and $kv.properties.networkAcls.bypass -eq 'AzureServices')
            'tu sesion puede usar getSecret (deploy/action)'     = (Test-ActionAllowed (Get-RoleDefinitionsAt $me $kv.id).definitions $DeployAction)
            'GitHub sin deploy/action'                           = (-not (Test-ActionAllowed (Get-RoleDefinitionsAt $gh.principalId $kv.id).definitions $DeployAction))
            'contrasenas solo como secretRef, DATABASE_URL sin contrasena' = ($secretEnvs.Count -eq 3 -and @($secretEnvs | Where-Object { $_.value -or -not $_.secretRef }).Count -eq 0 -and $urls.Count -eq 2 -and @($urls | Where-Object { "$($_.value)" -match '://[^/@:]+:[^@]*@' }).Count -eq 0)
            'PostgreSQL arrancado (Ready)'                       = ("$($pg.state)" -eq 'Ready')
            'bootstrap: ultima ejecucion Succeeded'              = ($last.Count -eq 1 -and "$($last[0].properties.status)" -eq 'Succeeded')
            'frontend responde 200 por HTTPS'                    = ($frontendStatus -eq 200)
            'API viva tras el proxy (/api/v1/me sin token -> 401)' = ($apiStatus -eq 401)
        }
        $failed = 0
        foreach ($k in $checks.Keys) { $ok = [bool]$checks[$k]; if (-not $ok) { $failed++ }; Write-Host ("{0}  {1}" -f ($(if ($ok) { 'OK  ' } else { 'FAIL' })), $k) }
        Save-Evidence 'u12-evidence.json' ([ordered]@{
            date = (Get-Date).ToUniversalTime().ToString('o'); subscriptionId = $account.id; tenantId = $account.tenantId; resourceGroup = $ResourceGroup
            frontendUrl = $out.frontendUrl; apiInternalFqdn = $api.properties.configuration.ingress.fqdn; imageTag = (Get-LiveTag $out.apiName)
            registry = [ordered]@{ name = $acr.name; id = $acr.id; sku = $acr.sku.name; adminUserEnabled = $acr.adminUserEnabled }
            postgres = [ordered]@{ name = $pg.name; id = $pg.id; version = $pg.version; sku = $pg.sku.name; state = $pg.state; requireSecureTransport = $tls
                                   firewall = @($rules | ForEach-Object { [ordered]@{ name = $_.name; ip = $_.startIpAddress } }) }
            containerApps = [ordered]@{ environment = $out.environmentName; api = $api.id; frontend = $fe.id; bootstrap = $job.id }
            githubRoles = @($ghRoles | ForEach-Object { [ordered]@{ role = $_.roleDefinitionName; scope = $_.scope } })
            runtimeRoles = @($rtRoles | ForEach-Object { [ordered]@{ role = $_.roleDefinitionName; scope = $_.scope } })
            keyVault = [ordered]@{ name = $kv.name; publicNetworkAccess = $kv.properties.publicNetworkAccess; enabledForTemplateDeployment = $kv.properties.enabledForTemplateDeployment; bypass = $kv.properties.networkAcls.bypass }
            bootstrapLastExecution = [ordered]@{ name = $(if ($last.Count) { $last[0].name } else { $null }); status = $(if ($last.Count) { $last[0].properties.status } else { $null }) }
            http = [ordered]@{ frontend = $frontendStatus; apiThroughProxyWithoutToken = $apiStatus }
            checksFailed = $failed })
        Write-Host ''; Write-Host "Evidencia: $EvidenceDir/u12-evidence.json (solo identificadores). Smoke:"
        Write-Host "  `$env:SMOKE_FRONTEND_URL='$($out.frontendUrl)'; `$env:SMOKE_API_URL='none'; `$env:SMOKE_TIMEOUT='120'; python infra/docker/smoke.py --entra"
        if ($failed) { Stop-U12 "$failed comprobacion(es) fallaron" }
        Write-Host 'U12: dev verificado.' -ForegroundColor Green
    }
}
