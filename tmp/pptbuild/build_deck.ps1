$ErrorActionPreference = 'Stop'

$workspace = 'C:\Users\samee\OneDrive\Desktop\nyc-mobility-surge-pipeline'
$outputDir = Join-Path $workspace 'output\presentation'
$renderDir = Join-Path $workspace 'tmp\pptbuild\renders'
New-Item -ItemType Directory -Force -Path $outputDir, $renderDir | Out-Null
$pptxPath = Join-Path $outputDir 'NYC_Mobility_Intelligence_Classic_ML_12_Slide_Deck.pptx'
$pdfPath = Join-Path $renderDir 'preview.pdf'

$pp = New-Object -ComObject PowerPoint.Application
$pp.Visible = -1
$deck = $pp.Presentations.Add()
$pp.WindowState = 2
$deck.PageSetup.SlideWidth = 960
$deck.PageSetup.SlideHeight = 540

$BG = 0xEAF3F7
$PANEL = 0xFFFFFF
$PANEL2 = 0xE2ECF1
$WHITE = 0x4D3217
$MUTED = 0x857066
$TEAL = 0x786F1F
$AMBER = 0x368BB7
$RED = 0x474F8F
$LINE = 0xD2D4D8
$FONT = 'Aptos'
$TITLEFONT = 'Georgia'

function Add-Rect($slide, $x, $y, $w, $h, $fill, $line = $LINE, $radius = $false) {
    $type = 1
    $s = $slide.Shapes.AddShape($type, $x, $y, $w, $h)
    $s.Fill.ForeColor.RGB = $fill
    $s.Line.ForeColor.RGB = $line
    $s.Line.Weight = 0.8
    return $s
}

function Add-Text($slide, $text, $x, $y, $w, $h, $size = 16, $color = $WHITE, $bold = $false, $align = 1, $fill = $null) {
    $s = $slide.Shapes.AddTextbox(1, $x, $y, $w, $h)
    if ($null -ne $fill) {
        $s.Fill.Visible = -1
        $s.Fill.ForeColor.RGB = $fill
    } else { $s.Fill.Visible = 0 }
    $s.Line.Visible = 0
    $s.TextFrame.MarginLeft = 3
    $s.TextFrame.MarginRight = 3
    $s.TextFrame.MarginTop = 2
    $s.TextFrame.MarginBottom = 2
    $s.TextFrame.WordWrap = -1
    $s.TextFrame.AutoSize = 0
    $s.TextFrame.TextRange.Text = $text
    $s.TextFrame.TextRange.Font.Name = $FONT
    $s.TextFrame.TextRange.Font.Size = [single]$size
    $s.TextFrame.TextRange.Font.Color.RGB = $color
    $s.TextFrame.TextRange.Font.Bold = $(if ($bold) { -1 } else { 0 })
    $s.TextFrame.TextRange.ParagraphFormat.Alignment = [int]$align
    return $s
}

function Add-Card($slide, $x, $y, $w, $h, $title, $body, $accent = $TEAL) {
    Add-Rect $slide $x $y $w 2 $accent $accent | Out-Null
    $heading = Add-Text $slide $title $x ($y + 10) $w 28 15 $WHITE $true
    $heading.TextFrame.TextRange.Font.Name = $TITLEFONT
    Add-Text $slide $body $x ($y + 42) $w ($h - 45) 11.5 $MUTED $false | Out-Null
}

function Add-Header($slide, $num, $kicker, $title) {
    Add-Text $slide (('{0:D2}' -f $num) + '  /  ' + $kicker.ToUpper()) 38 18 650 18 8 $AMBER $true | Out-Null
    $heading = Add-Text $slide $title 38 45 870 43 27 $WHITE $true
    $heading.TextFrame.TextRange.Font.Name = $TITLEFONT
    Add-Rect $slide 38 91 884 1 $LINE $LINE | Out-Null
}

function Add-Footer($slide, $num, $source = '') {
    if ($source) { Add-Text $slide $source 38 507 780 15 7.5 $MUTED | Out-Null }
    Add-Text $slide (('{0:D2}' -f $num) + ' / 12') 870 507 52 15 7.5 $MUTED $false 3 | Out-Null
}

function New-Slide($num, $kicker, $title) {
    $slide = $deck.Slides.Add($deck.Slides.Count + 1, 12)
    $slide.FollowMasterBackground = 0
    $slide.Background.Fill.ForeColor.RGB = $BG
    Add-Header $slide $num $kicker $title
    return $slide
}

# 1 Cover
$s = $deck.Slides.Add(1, 12)
$s.FollowMasterBackground = 0
$s.Background.Fill.ForeColor.RGB = $BG
$coverKicker = Add-Text $s 'UNIVERSITY PROJECT DEFENSE  /  BIG DATA SYSTEMS' 250 82 460 20 9 $AMBER $true 2
$coverTitle = Add-Text $s 'NYC Mobility Intelligence' 110 135 740 62 38 $WHITE $true 2
$coverTitle.TextFrame.TextRange.Font.Name = $TITLEFONT
Add-Text $s 'Urban Mobility, Demand Forecasting and Explainable Surge Pricing' 150 212 660 30 17 $MUTED $false 2 | Out-Null
Add-Rect $s 350 258 260 2 $AMBER $AMBER | Out-Null
Add-Text $s 'NYC Yellow Taxi Big Data Analytics  -  Apache Spark  -  SQLite  -  Streamlit' 190 282 580 24 12 $WHITE $false 2 | Out-Null
Add-Text $s 'Yellamandala Sameer' 84 348 250 22 13 $WHITE $true 2 | Out-Null
Add-Text $s '2023BCS-073' 84 374 250 18 10 $MUTED $false 2 | Out-Null
Add-Text $s 'Sama Ruthwik Reddy' 355 348 250 22 13 $WHITE $true 2 | Out-Null
Add-Text $s '2023BCS-079' 355 374 250 18 10 $MUTED $false 2 | Out-Null
Add-Text $s 'Netipattu Rahil' 626 348 250 22 13 $WHITE $true 2 | Out-Null
Add-Text $s '2023BCS-080' 626 374 250 18 10 $MUTED $false 2 | Out-Null
Add-Text $s 'Department of Computer Science and Engineering' 280 474 400 18 10 $MUTED $false 2 | Out-Null

# 2 Problem and big data rationale
$s = New-Slide 2 'Problem statement and motivation' 'Why NYC Mobility Analytics?'
Add-Card $s 38 112 390 92 'Fragmented mobility signals' 'Millions of trips contain demand, congestion and pricing patterns that manual analysis cannot reveal.' $TEAL
Add-Card $s 38 218 390 92 'Operational planning gap' 'Operators need zone and hour level insight to anticipate demand and explain pricing decisions.' $AMBER
Add-Card $s 38 324 390 92 'Batch and live views' 'Historical analytics and simulated dispatch events require separate but connected processing paths.' $TEAL
Add-Rect $s 458 112 464 304 $PANEL2 $LINE $true | Out-Null
Add-Text $s 'WHY THIS QUALIFIES AS BIG DATA' 482 132 410 20 10 $TEAL $true | Out-Null
Add-Text $s '29.7M' 480 174 180 50 34 $AMBER $true | Out-Null
Add-Text $s 'raw trip records' 482 220 180 20 10 $MUTED | Out-Null
Add-Text $s '488 MiB' 700 174 180 50 34 $AMBER $true | Out-Null
Add-Text $s 'compressed Parquet' 702 220 180 20 10 $MUTED | Out-Null
Add-Text $s "Volume: tens of millions of observations`r`nVariety: temporal, spatial, fare and passenger fields`r`nVelocity: simulated event ingestion for live analytics`r`nProcessing: distributed transformations and aggregations" 482 270 400 112 13 $WHITE | Out-Null
Add-Footer $s 2

# 3 Objectives
$s = New-Slide 3 'Objectives and proposed solution' 'Project Objectives'
Add-Card $s 38 112 205 158 '01  Distributed ETL' 'Validate, clean and aggregate eight monthly Parquet files with PySpark.' $AMBER
Add-Card $s 257 112 205 158 '02  Demand analytics' 'Measure hourly demand, congestion, revenue and pickup hotspots.' $TEAL
Add-Card $s 476 112 205 158 '03  Pricing intelligence' 'Apply percentile-based surge tiers with reasons and fare impact.' $AMBER
Add-Card $s 695 112 227 158 '04  Interactive UI' 'Present historical, forecast and simulated live metrics in Streamlit.' $TEAL
Add-Rect $s 38 298 884 58 $PANEL2 $LINE $true | Out-Null
Add-Text $s 'BATCH' 54 316 72 20 9 $AMBER $true 2 | Out-Null
Add-Text $s 'TLC Parquet   >   Spark ETL   >   Aggregated CSV   >   SQLite   >   Dashboard' 140 311 760 30 13 $WHITE $true 2 | Out-Null
Add-Rect $s 38 372 884 58 $PANEL2 $LINE $true | Out-Null
Add-Text $s 'LIVE DEMO' 52 390 76 20 9 $TEAL $true 2 | Out-Null
Add-Text $s 'Trip templates   >   Event generator   >   SQLite live buffer   >   Auto-refresh UI' 140 385 760 30 13 $WHITE $true 2 | Out-Null
Add-Footer $s 3 'Live events are simulated from historical trip templates. No live TLC GPS feed is used.'

# 4 Dataset
$s = New-Slide 4 'Dataset and source' 'NYC Yellow Taxi Trip Records'
Add-Card $s 38 112 410 116 'Official source' "NYC Taxi and Limousine Commission Trip Record Data`r`nEight monthly Yellow Taxi Parquet files: January to August 2026" $TEAL
Add-Card $s 38 244 410 134 'Local dataset scale' "29,703,355 raw records`r`n511,451,602 bytes, approximately 488 MiB`r`n261 pickup zones represented in the serving layer" $AMBER
Add-Card $s 470 112 452 266 'What each trip describes' "Pickup and drop-off timestamps`r`nPickup and drop-off Taxi Zone IDs`r`nPassenger count and trip distance`r`nFare, tips and total amount`r`nRate and payment attributes`r`n`r`nTaxi Zone lookup: borough, zone name and service zone" $TEAL
Add-Footer $s 4 'Source: NYC TLC Trip Record Data and Yellow Taxi Trip Records Data Dictionary'

# 5 Cleaning
$s = New-Slide 5 'Data cleaning and processing' 'From Raw Trips to Analytical Tables'
Add-Card $s 38 110 260 94 '01  Schema validation' 'Require pickup/drop-off timestamps, passenger count, distance, zone IDs, fare and total amount.' $TEAL
Add-Card $s 38 216 260 94 '02  Quality filters' 'Remove null locations and invalid trips. Enforce passenger, fare, distance and duration limits.' $AMBER
Add-Card $s 38 322 260 94 '03  Feature engineering' 'Calculate duration, hour, weekday, date, month, weekend flag and speed in mph.' $TEAL
Add-Card $s 320 110 602 94 'Business rules' 'Passengers 1-6  /  Fare $2.50-$500  /  Distance 0.10-150 miles  /  Duration 1-300 minutes  /  Valid Taxi Zone IDs 1-265' $AMBER
Add-Card $s 320 216 602 94 'Spatial enrichment' 'Join the official Taxi Zone lookup to attach zone name, borough and service zone to every pickup location.' $TEAL
Add-Card $s 320 322 602 94 'Aggregation outputs' '168 weekday-hour rows  /  261 zone summaries  /  36,947 zone-hour records  /  244 daily trend rows  /  36,947 pricing windows' $AMBER
Add-Footer $s 5

# 6 Architecture
$s = New-Slide 6 'System architecture' 'Batch Analytics and Simulated Live Operations'
Add-Text $s 'HISTORICAL BATCH PATH' 50 104 250 18 9 $AMBER $true | Out-Null
$x = 38
$labels = @('TLC Parquet','PySpark ETL','Processed CSV','SQLite','Streamlit')
for ($i=0; $i -lt $labels.Count; $i++) {
    Add-Rect $s $x 134 148 56 $PANEL $LINE $true | Out-Null
    Add-Text $s $labels[$i] ($x+6) 150 136 22 12 $WHITE $true 2 | Out-Null
    if ($i -lt $labels.Count-1) { Add-Text $s '>' ($x+150) 150 30 22 15 $AMBER $true 2 | Out-Null }
    $x += 176
}
Add-Text $s 'SIMULATED LIVE PATH' 50 242 250 18 9 $TEAL $true | Out-Null
$x = 38
$labels = @('Trip sample pool','Event generator','Live buffer','Live queries','Auto-refresh UI')
for ($i=0; $i -lt $labels.Count; $i++) {
    Add-Rect $s $x 272 148 56 $PANEL $LINE $true | Out-Null
    Add-Text $s $labels[$i] ($x+6) 288 136 22 12 $WHITE $true 2 | Out-Null
    if ($i -lt $labels.Count-1) { Add-Text $s '>' ($x+150) 288 30 22 15 $TEAL $true 2 | Out-Null }
    $x += 176
}
Add-Card $s 38 370 428 80 'Serving layer' 'SQLite stores historical aggregates, pricing windows and the bounded live_trips event buffer.' $AMBER
Add-Card $s 494 370 428 80 'Separation of concerns' 'Historical metrics remain distinct from simulated live events to preserve data provenance.' $TEAL
Add-Footer $s 6

# 7 Tech stack
$s = New-Slide 7 'Technology stack' 'Tools Used Across the Pipeline'
Add-Card $s 38 112 280 116 'Processing' "Python 3.12`r`nApache Spark / PySpark 3.5.1`r`nPandas, PyArrow and scikit-learn" $AMBER
Add-Card $s 340 112 280 116 'Storage and serving' "Parquet raw data lake`r`nCSV analytical exports`r`nSQLite with SQLAlchemy" $TEAL
Add-Card $s 642 112 280 116 'Visualization' "Streamlit`r`nPlotly interactive charts`r`nFolium geospatial maps" $AMBER
Add-Card $s 38 252 280 116 'Analytics logic' "Gradient-boosting demand model`r`nSeasonal comparison baseline`r`nMedian-based spike detection" $TEAL
Add-Card $s 340 252 280 116 'Quality assurance' "Pytest regression tests`r`nSchema and null validation`r`nDatabase integrity checks" $AMBER
Add-Card $s 642 252 280 116 'Application design' "Parameterized SQL queries`r`nCached database connection`r`nAuto-refreshing live fragment" $TEAL
Add-Footer $s 7

# 8 Models
$s = New-Slide 8 'Analytical models' 'Demand Forecasting, Spike Detection and Surge Pricing'
Add-Card $s 38 112 280 240 'Demand forecast' "Model: histogram gradient-boosting regressor`r`nFeatures: hour, weekday, month, weekend and borough`r`nOutput: next six hours with an uncertainty band`r`n`r`nTrained on January-July data and tested chronologically on August." $TEAL
Add-Card $s 340 112 280 240 'Demand-spike detection' "Baseline: median trip demand for each pickup zone`r`nAlert: at least 35% above baseline`r`nSeverity: Elevated or Critical`r`n`r`nShows observed demand, normal demand and percentage increase." $AMBER
Add-Card $s 642 112 280 240 'Explainable surge pricing' "Below P50: 1.0x`r`nP50 and above: 1.3x`r`nP75 and above: 1.8x`r`nP90 and above: 2.5x`r`n`r`nThe dashboard explains the threshold and fare impact for every decision." $TEAL
Add-Rect $s 38 376 884 54 $PANEL2 $LINE $true | Out-Null
Add-Text $s 'MODEL EVALUATION' 56 392 126 18 9 $TEAL $true | Out-Null
Add-Text $s 'Chronological holdout: ML WAPE 14.99% versus 18.49% for the seasonal baseline. Pricing and live events remain simulations.' 190 386 708 30 12 $WHITE $true 2 | Out-Null
Add-Footer $s 8

# 9 Dashboard
$s = New-Slide 9 'Dashboard and live operations' 'Six Interactive Views in Streamlit'
Add-Card $s 38 112 280 92 'Executive Intelligence' 'KPIs, six-hour forecast and priority demand-spike alerts.' $TEAL
Add-Card $s 340 112 280 92 'Demand and Congestion' 'Weekday-hour heatmap and traffic-speed profile.' $AMBER
Add-Card $s 642 112 280 92 'Pickup Hotspots' 'Ranked zones and an interactive NYC map.' $TEAL
Add-Card $s 38 222 280 92 'Explainable Pricing' 'Zone, weekday and hour controls with decision rationale.' $AMBER
Add-Card $s 340 222 280 92 'Daily Trends' 'Trip volume, gross revenue, fare and distance over time.' $TEAL
Add-Card $s 642 222 280 92 'Live Operations' 'Streaming rate, live revenue, hotspots, alerts and recent dispatches.' $AMBER
Add-Rect $s 38 344 884 82 $PANEL2 $LINE $true | Out-Null
Add-Text $s 'LIVE DEMONSTRATION' 56 362 170 18 9 $TEAL $true | Out-Null
Add-Text $s 'Start or pause the background generator, inject a 50-ride burst, watch the two-second refresh, and explain how burst intensity changes the pricing tier.' 230 354 660 42 13 $WHITE | Out-Null
Add-Footer $s 9

# 10 Results
$s = New-Slide 10 'Results and capabilities' 'Processed Data and Delivered Analytics'
$metrics = @(
    @('29.7M','raw trip records'),
    @('21.0M','retained trips in serving summaries'),
    @('$618.5M','aggregated gross revenue'),
    @('261','pickup zones')
)
$x=38
foreach($m in $metrics){ Add-Rect $s $x 112 205 92 $PANEL $LINE $true | Out-Null; Add-Text $s $m[0] ($x+12) 127 181 36 25 $AMBER $true | Out-Null; Add-Text $s $m[1].ToUpper() ($x+12) 169 181 22 8 $MUTED $true | Out-Null; $x+=219 }
Add-Card $s 38 228 424 196 'Implemented capabilities' "Distributed cleaning and aggregation with PySpark`r`nZone and hour level demand analysis`r`nPercentile-based explainable pricing`r`nTrained ML six-hour forecast with uncertainty`r`nDemand-spike alerts and simulated live operations" $TEAL
Add-Card $s 482 228 440 196 'Serving layer evidence' "168 weekday-hour demand rows`r`n36,947 zone-hour demand rows`r`n36,947 pricing decision windows`r`n244 daily observations`r`nTop zones: Upper East Side South, JFK Airport and Midtown Center" $AMBER
Add-Footer $s 10 'Metrics read from the local Parquet files and db/mobility.db serving database.'

# 11 Limitations
$s = New-Slide 11 'Limitations and future scope' 'Current Boundaries and Next Steps'
Add-Card $s 38 112 280 270 'Achievements' "End-to-end batch pipeline`r`nInteractive six-view dashboard`r`nExplainable percentile pricing`r`nEvaluated gradient-boosting forecast`r`nAutomated dashboard and query tests" $TEAL
Add-Card $s 340 112 280 270 'Limitations' "Completed trips do not reveal unmet demand`r`nNo driver-supply or customer-response data`r`nLive events are simulated`r`nML uses calendar and borough features only`r`nSQLite targets local demonstration scale" $RED
Add-Card $s 642 112 280 270 'Future scope' "Connect weather and event data`r`nAdd driver-supply signals`r`nCompare LSTM and XGBoost models`r`nUse Kafka for external event streams`r`nDeploy PostgreSQL/PostGIS in the cloud" $AMBER
Add-Footer $s 11 'Future-scope items are proposals and are not implemented in the current project.'

# 12 Summary
$s = New-Slide 12 'Summary' 'NYC Mobility Intelligence'
Add-Text $s '29.7 million public taxi trips become decision-ready mobility analytics through a reproducible batch pipeline.' 100 118 760 48 22 $WHITE $true 2 | Out-Null
Add-Rect $s 170 196 620 2 $TEAL $TEAL | Out-Null
Add-Text $s "The project demonstrates distributed ETL, spatial and temporal aggregation, a trained demand forecast, explainable surge pricing, spike detection and simulated live operations.`r`n`r`nThe dashboard connects each analytical output to an operational question while keeping simulated and historical data separate." 150 228 660 126 16 $MUTED $false 2 | Out-Null
Add-Text $s 'THANK YOU' 290 390 380 42 30 $TEAL $true 2 | Out-Null
Add-Text $s 'Questions and Answers' 330 442 300 26 16 $AMBER $true 2 | Out-Null
Add-Footer $s 12

if (Test-Path -LiteralPath $pptxPath) { Remove-Item -LiteralPath $pptxPath -Force }
$deck.SaveAs($pptxPath, 24)
if (Test-Path -LiteralPath $pdfPath) { Remove-Item -LiteralPath $pdfPath -Force }
$deck.SaveAs($pdfPath, 32)
$deck.Close()
$pp.Quit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($deck) | Out-Null
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($pp) | Out-Null
Write-Output $pptxPath
Write-Output $pdfPath
