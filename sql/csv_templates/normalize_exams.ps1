param(
  [Parameter(Mandatory = $true)] [string] $InFile,
  [Parameter(Mandatory = $true)] [string] $OutFile,
  [string] $School = "CUJ"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Parse-Date([string] $s) {
  if (-not $s) { return $null }
  try { [datetime]::ParseExact($s.Trim(), 'dd/MM/yyyy', $null) } catch { $null }
}

function Parse-Time([string] $s) {
  if (-not $s) { return $null }
  try { [datetime]::ParseExact($s.Trim(), 'h:mm tt', $null) } catch { $null }
}

function Split-TimeRange([string] $s) {
  if (-not $s) { return $null }
  $parts = $s -split '\s*to\s*', 2
  if ($parts.Count -ne 2) { return $null }
  $start = Parse-Time $parts[0]
  $end   = Parse-Time $parts[1]
  if ($start -and $end) { @{ Start = $start; End = $end } } else { $null }
}

function Dept-From-Branch([string] $b) {
  if (-not $b) { return "ECE" }
  if ($b -match '(?i)avionics') { return "ECE (Avionics)" }
  "ECE"
}

# --- use the parameters you pass! ---
if (-not (Test-Path -LiteralPath $InFile)) {
  throw "Input file not found: $InFile"
}

$rows = Import-Csv -LiteralPath $InFile

$normalized = foreach ($r in $rows) {
  $code  = ($r.'Course Code').Trim()
  $title = ($r.'Course Title').Trim()
  $date  = Parse-Date $r.'Date of Exam'
  $rng   = Split-TimeRange $r.Time
  $dept  = Dept-From-Branch $r.Branch

  if (-not $code -or -not $title -or -not $date -or -not $rng) {
    Write-Warning ("Skipping row (cannot parse): " + ($r | ConvertTo-Json -Compress))
    continue
  }

  $start = Get-Date -Year $date.Year -Month $date.Month -Day $date.Day `
                    -Hour $rng.Start.Hour -Minute $rng.Start.Minute -Second 0
  $end   = Get-Date -Year $date.Year -Month $date.Month -Day $date.Day `
                    -Hour $rng.End.Hour   -Minute $rng.End.Minute   -Second 0

  $mins = [int]([timespan]($end - $start)).TotalMinutes
  if ($mins -le 0) { $mins = 120 }

  $slot = if ($start.Hour -lt 13) { "FN" } else { "AN" }

  [pscustomobject]@{
    course_code      = $code
    course_name      = $title
    department       = $dept
    duration_minutes = $mins
    exam_date        = $date.ToString('yyyy-MM-dd')
    school           = $School
    slot             = $slot
  }
}

if (-not $normalized) {
  throw "No valid rows parsed. Check column names: 'Course Code','Course Title','Date of Exam','Time','Branch'."
}

$normalized | Export-Csv -LiteralPath $OutFile -NoTypeInformation -Encoding UTF8
Write-Host "✅ Wrote $OutFile with $($normalized.Count) rows."
