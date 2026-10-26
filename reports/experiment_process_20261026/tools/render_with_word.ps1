param([Parameter(Mandatory=$true)][string]$DocumentPath,[Parameter(Mandatory=$true)][string]$PdfPath)
$ErrorActionPreference='Stop'
$absoluteDoc=[System.IO.Path]::GetFullPath($DocumentPath)
$absolutePdf=[System.IO.Path]::GetFullPath($PdfPath)
$app=$null
$document=$null
$closeApp=$false
try {
  $app=New-Object -ComObject Word.Application
  $closeApp=($app.Documents.Count -eq 0 -and -not $app.Visible)
  $previousAlerts=$app.DisplayAlerts
  $app.DisplayAlerts=0
  $document=$app.Documents.Open($absoluteDoc,$false,$true,$false)
  $document.Repaginate()
  $document.Fields.Update() | Out-Null
  $pages=$document.ComputeStatistics(2)
  $document.ExportAsFixedFormat($absolutePdf,17)
  Write-Output (@{renderer='Microsoft Word PDF export';pages=$pages;pdf=$absolutePdf} | ConvertTo-Json -Compress)
} finally {
  if ($document) { $document.Close(0); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($document) }
  if ($app) { $app.DisplayAlerts=$previousAlerts; if ($closeApp) {$app.Quit()}; [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app) }
}
